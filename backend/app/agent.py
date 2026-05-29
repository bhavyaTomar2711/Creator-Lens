"""LangGraph RAG agent.

Graph:  prepare -> generate
  prepare  : loads the two videos' STRUCTURED metadata (engagement, followers, ...) as
             verified facts, and retrieves transcript chunks from BOTH videos (with a
             "first N seconds" time filter when the question is about hooks/openings).
  generate : a Groq LLM answers grounded ONLY in that context, citing chunks.

Memory (R6) is persisted in the store (survives restarts / multiple replicas), not in an
in-process checkpointer. Streaming (R6) is done with graph.astream_events at the endpoint.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from . import config, store, vectorstore

# No \b wrappers: must still match "hooks" and "first 5 seconds".
_HOOK_RE = re.compile(r"(hook|first\s+\d+\s*sec|first\s+five|opening|intro|beginning)", re.I)
_SEC_RE = re.compile(r"first\s+(\d+)\s*sec", re.I)

SYSTEM_PROMPT = """You are CreatorLens, an analytics assistant that helps a creator compare two short-form videos:
  - Video A (YouTube) and Video B (Instagram).

Rules:
- Use ONLY the CONTEXT below. Never invent numbers, names, or facts.
- For any statistic (engagement rate, views, likes, comments, follower count, duration), use the
  METADATA block exactly as given. Engagement rate is already computed as (likes+comments)/views*100.
- When you reference something SAID in a video, cite the source chunk inline like [A · chunk 0]
  or [B · chunk 1]. Only cite chunks present in the context.
- Be concise, concrete, and actionable for a creator. When asked to compare, compare A vs B directly.
- For "hook" / "opening" / "first N seconds" questions: the hook is the BEGINNING of the earliest
  retrieved chunk (lowest start time) for each video. Quote its opening words and compare them.
  Do NOT claim the opening is missing just because a chunk's time range extends beyond N seconds.
- If the context lacks the answer, say so plainly rather than guessing."""


class ChatState(TypedDict, total=False):
    session_id: str
    query: str
    history: list[dict]
    context: str
    sources: list[dict]
    answer: str


@lru_cache(maxsize=1)
def _llm():
    from langchain_groq import ChatGroq

    return ChatGroq(model=config.GROQ_LLM_MODEL, api_key=config.GROQ_API_KEY, temperature=0.3)


def _fmt_meta(v: dict, label: str) -> str:
    tags = " ".join(v.get("hashtags") or []) or "—"
    return (
        f"=== VIDEO {label} ({v.get('platform','?').upper()}) METADATA ===\n"
        f"creator: {v.get('creator')} | followers: {v.get('follower_count')}\n"
        f"title: {v.get('title')}\n"
        f"views: {v.get('views')} | likes: {v.get('likes')} | comments: {v.get('comments')}\n"
        f"engagement_rate: {v.get('engagement_rate')}%\n"
        f"duration: {v.get('duration_sec')}s | uploaded: {v.get('upload_date')}\n"
        f"hashtags: {tags}\n"
    )


def build_context(session_id: str, query: str) -> tuple[str, list[dict]]:
    """Return (context_string, sources) for a query within a session."""
    session = store.load_session(session_id)
    if not session:
        return "(no session data found)", []

    a, b = session["video_a"], session["video_b"]

    # "first N seconds" / hook questions -> restrict retrieval to the opening
    max_start = None
    if _HOOK_RE.search(query):
        m = _SEC_RE.search(query)
        max_start = float(m.group(1)) if m else 5.0

    # retrieve from BOTH videos so comparisons always see both sides
    chunks = vectorstore.search(session_id, query, video_id="A", top_k=4, max_start=max_start)
    chunks += vectorstore.search(session_id, query, video_id="B", top_k=4, max_start=max_start)

    lines = [_fmt_meta(a, "A"), _fmt_meta(b, "B"), "=== RETRIEVED TRANSCRIPT CHUNKS ==="]
    sources = []
    if not chunks:
        lines.append("(no transcript chunks matched)")
    for c in chunks:
        cite = f"[{c['video_id']} · chunk {c['chunk_index']} · {c['start']:.1f}-{c['end']:.1f}s]"
        lines.append(f"{cite} {c['text']}")
        sources.append(
            {
                "video_id": c["video_id"],
                "chunk_index": c["chunk_index"],
                "start": c["start"],
                "end": c["end"],
                "text": c["text"][:200],
                "score": c.get("score"),
            }
        )
    return "\n".join(lines), sources


def _to_lc_messages(state: ChatState) -> list:
    msgs = [SystemMessage(content=f"{SYSTEM_PROMPT}\n\nCONTEXT:\n{state['context']}")]
    for m in state.get("history", []):
        msgs.append(HumanMessage(m["content"]) if m["role"] == "user" else AIMessage(m["content"]))
    msgs.append(HumanMessage(state["query"]))
    return msgs


# --- graph nodes ---
def _prepare(state: ChatState) -> dict:
    context, sources = build_context(state["session_id"], state["query"])
    return {"context": context, "sources": sources}


async def _generate(state: ChatState) -> dict:
    resp = await _llm().ainvoke(_to_lc_messages(state))
    return {"answer": resp.content}


@lru_cache(maxsize=1)
def graph():
    g = StateGraph(ChatState)
    g.add_node("prepare", _prepare)
    g.add_node("generate", _generate)
    g.add_edge(START, "prepare")
    g.add_edge("prepare", "generate")
    g.add_edge("generate", END)
    return g.compile()


async def astream_chat(session_id: str, query: str, history: list[dict]):
    """Stream the agent. Yields ('sources', list) once prepare finishes, then ('token', str)
    per LLM token, then ('done', full_answer). Driven by LangGraph's event stream."""
    state: ChatState = {"session_id": session_id, "query": query, "history": history}
    answer_parts: list[str] = []

    async for ev in graph().astream_events(state, version="v2"):
        kind = ev["event"]
        if kind == "on_chain_end" and ev.get("name") == "prepare":
            yield ("sources", (ev["data"].get("output") or {}).get("sources", []))
        elif kind == "on_chat_model_stream":
            token = getattr(ev["data"]["chunk"], "content", "") or ""
            if token:
                answer_parts.append(token)
                yield ("token", token)

    yield ("done", "".join(answer_parts))
