"""Persistence: url-hash dedup cache + per-session metadata store.

Two interchangeable backends, chosen by config.STORAGE_BACKEND:
  - "local"  : JSON files under data/ (dev convenience, zero setup)
  - "qdrant" : stored as payloads in Qdrant (cloud) -> NO local disk in production

- CACHE: a fully-ingested Video keyed by sha256(url). The expensive work (download +
  Whisper + API enrichment) happens ONCE per URL, ever. Core scale lever — and it also
  makes the deployed demo reliable (videos pre-ingested locally are served from cloud cache,
  so no risky live Instagram fetch from a datacenter IP).

- SESSIONS: the two Video records for a comparison, keyed by session_id. The chat reads
  engagement/follower numbers from HERE (structured facts), not from vector search.
"""
from __future__ import annotations

import json

from . import config
from .models import Video

CACHE_DIR = config.DATA_DIR / "cache"
SESSION_DIR = config.DATA_DIR / "sessions"
CACHE_DIR.mkdir(exist_ok=True)
SESSION_DIR.mkdir(exist_ok=True)

_USE_QDRANT = config.STORAGE_BACKEND == "qdrant"
_CACHE_COLL = "ingest_cache"
_SESSION_COLL = "sessions"
_CHAT_COLL = "chat_history"

CHAT_DIR = config.DATA_DIR / "chat"
CHAT_DIR.mkdir(exist_ok=True)


# --- url-hash cache ---
def cache_get(url_hash: str) -> Video | None:
    if _USE_QDRANT:
        from . import vectorstore

        payload = vectorstore.kv_get(_CACHE_COLL, url_hash)
        return Video.model_validate(payload["video"]) if payload else None

    p = CACHE_DIR / f"{url_hash}.json"
    return Video.model_validate_json(p.read_text(encoding="utf-8")) if p.exists() else None


def cache_put(video: Video) -> None:
    if _USE_QDRANT:
        from . import vectorstore

        vectorstore.kv_put(_CACHE_COLL, video.url_hash, {"video": video.model_dump()})
        return

    (CACHE_DIR / f"{video.url_hash}.json").write_text(
        video.model_dump_json(indent=2), encoding="utf-8"
    )


# --- session store ---
def save_session(session_id: str, video_a: Video, video_b: Video) -> None:
    payload = {
        "session_id": session_id,
        "video_a": video_a.model_dump(),
        "video_b": video_b.model_dump(),
    }
    if _USE_QDRANT:
        from . import vectorstore

        vectorstore.kv_put(_SESSION_COLL, session_id, payload)
        return

    (SESSION_DIR / f"{session_id}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_session(session_id: str) -> dict | None:
    if _USE_QDRANT:
        from . import vectorstore

        return vectorstore.kv_get(_SESSION_COLL, session_id)

    p = SESSION_DIR / f"{session_id}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# --- conversation memory (R6) ---
# Persisted (not in-process), so memory survives restarts and works across replicas —
# unlike LangGraph's in-memory checkpointer. Each item: {"role": "user"|"assistant", "content": str}.
def load_history(session_id: str) -> list[dict]:
    if _USE_QDRANT:
        from . import vectorstore

        payload = vectorstore.kv_get(_CHAT_COLL, session_id)
        return payload["messages"] if payload else []

    p = CHAT_DIR / f"{session_id}.json"
    return json.loads(p.read_text(encoding="utf-8"))["messages"] if p.exists() else []


def save_history(session_id: str, messages: list[dict]) -> None:
    if _USE_QDRANT:
        from . import vectorstore

        vectorstore.kv_put(_CHAT_COLL, session_id, {"messages": messages})
        return

    (CHAT_DIR / f"{session_id}.json").write_text(
        json.dumps({"messages": messages}, ensure_ascii=False), encoding="utf-8"
    )
