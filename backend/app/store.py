"""Persistence: url-hash dedup cache + per-session metadata store.

- CACHE: a fully-ingested Video keyed by sha256(url). The expensive work (download +
  Whisper + API enrichment) happens ONCE per URL, ever. This is the core scale lever —
  creators re-analyze the same / popular videos constantly, so most ingests are cache hits.

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


# --- url-hash cache ---
def cache_get(url_hash: str) -> Video | None:
    p = CACHE_DIR / f"{url_hash}.json"
    if p.exists():
        return Video.model_validate_json(p.read_text(encoding="utf-8"))
    return None


def cache_put(video: Video) -> None:
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
    (SESSION_DIR / f"{session_id}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_session(session_id: str) -> dict | None:
    p = SESSION_DIR / f"{session_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
