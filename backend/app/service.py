"""Ingest service: ties the pipeline, cache, vector store, and session store together.

ingest_pair() is what the /ingest endpoint calls.
"""
from __future__ import annotations

import uuid

from . import store, vectorstore
from .ingest.common import url_hash
from .ingest.pipeline import ingest
from .models import Video, VideoLabel


def _ingest_one(url: str, label: VideoLabel, overrides: dict | None = None) -> Video:
    """Cache-aware single-video ingest. Overrides bypass the cache (manual data is
    session-specific and shouldn't poison the shared cache)."""
    if not overrides:
        cached = store.cache_get(url_hash(url))
        if cached is not None:
            cached.video_id = label  # same URL may be A in one session, B in another
            return cached

    video = ingest(url, label, overrides)

    # only cache a clean, successful ingest (no overrides, real transcript)
    if not overrides and video.transcript_source not in ("none", "manual"):
        store.cache_put(video)
    return video


def ingest_pair(
    youtube_url: str,
    instagram_url: str,
    overrides_a: dict | None = None,
    overrides_b: dict | None = None,
) -> dict:
    session_id = uuid.uuid4().hex

    video_a = _ingest_one(youtube_url, "A", overrides_a)
    video_b = _ingest_one(instagram_url, "B", overrides_b)

    chunks_a = vectorstore.upsert_video(session_id, video_a)
    chunks_b = vectorstore.upsert_video(session_id, video_b)

    store.save_session(session_id, video_a, video_b)

    return {
        "session_id": session_id,
        "video_a": video_a,
        "video_b": video_b,
        "chunks_indexed": {"A": chunks_a, "B": chunks_b},
    }
