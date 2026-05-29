"""FastAPI app. Day 1: health + /ingest (metadata + transcript). Vector store & the
LangGraph chat endpoint land on Day 2/3."""
from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import agent, config, service, store
from .models import Video

app = FastAPI(title="CreatorLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,  # localhost in dev; deployed frontend URL in prod
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    youtube_url: str
    instagram_url: str
    # optional manual overrides for fields a blocked reel can't supply (e.g. follower_count)
    overrides_a: dict | None = None
    overrides_b: dict | None = None


class IngestResponse(BaseModel):
    session_id: str
    video_a: Video
    video_b: Video
    chunks_indexed: dict


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
def ingest_pair(req: IngestRequest):
    """Ingest both videos, embed + index their chunks, and open a chat session."""
    result = service.ingest_pair(
        req.youtube_url, req.instagram_url, req.overrides_a, req.overrides_b
    )
    return IngestResponse(**result)


@app.get("/session/{session_id}")
def get_session(session_id: str):
    """Fetch a session's two video records (for the side-by-side cards)."""
    s = store.load_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    return s


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/chat")
async def chat(req: ChatRequest):
    """Stream a grounded, cited answer over SSE; persists conversation memory (R6)."""
    history = store.load_history(req.session_id)

    async def event_gen():
        sources: list = []
        answer = ""
        async for kind, data in agent.astream_chat(req.session_id, req.message, history):
            if kind == "sources":
                sources = data
                yield {"event": "sources", "data": json.dumps(data)}
            elif kind == "token":
                yield {"event": "token", "data": data}
            elif kind == "done":
                answer = data
                yield {"event": "done", "data": json.dumps({"answer": answer, "sources": sources})}
        # persist memory after the turn completes
        store.save_history(
            req.session_id,
            history + [
                {"role": "user", "content": req.message},
                {"role": "assistant", "content": answer},
            ],
        )

    return EventSourceResponse(event_gen())
