"""Day-3 exit criteria: run the 5 brief questions through the LangGraph agent,
confirm grounded answers + citations, and test memory with a follow-up.

Usage: python -m scripts.smoke_chat
"""
import asyncio
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import agent, service  # noqa: E402

YT = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
IG = "https://www.instagram.com/reel/DYPR-_7vXXU/"

QUESTIONS = [
    "Why did Video A get more engagement than Video B?",
    "What's the engagement rate of each?",
    "Compare the hooks in the first 5 seconds.",
    "Who's the creator of Video B and what's their follower count?",
    "Suggest improvements for B based on what worked in A.",
    "And how many followers does video A have?",  # memory: refers back, no context repeated
]


async def main():
    res = service.ingest_pair(YT, IG)
    sid = res["session_id"]
    print(f"session: {sid}\n")

    g = agent.graph()
    history: list[dict] = []
    for q in QUESTIONS:
        out = await g.ainvoke({"session_id": sid, "query": q, "history": history})
        ans = out["answer"]
        cites = sorted({f"{s['video_id']}·{s['chunk_index']}" for s in out["sources"]})
        print("=" * 70)
        print(f"Q: {q}")
        print(f"A: {ans}")
        print(f"   sources: {cites}")
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": ans}]


if __name__ == "__main__":
    asyncio.run(main())
