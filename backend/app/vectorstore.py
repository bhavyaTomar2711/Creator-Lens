"""Qdrant vector store — local on-disk mode (no Docker, no server, no key).

One collection holds chunks from every session. Each point is tagged with
{session_id, video_id, chunk_index, start, end, text, platform, creator} so we can:
  - scope retrieval to one comparison        -> filter session_id
  - scope to one video (A or B)              -> filter video_id
  - answer "first N seconds" questions       -> filter start <= N

NOTE: local mode holds a file lock, so only ONE process may open the path at a time
(fine for this app + scripts; production would point at a Qdrant server instead).
"""
from __future__ import annotations

import atexit
import uuid
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)

from . import config, embeddings
from .models import Video

COLLECTION = "creatorlens"
_NS = uuid.UUID("00000000-0000-0000-0000-00000000c0de")  # stable namespace for point ids


@lru_cache(maxsize=1)
def client() -> QdrantClient:
    c = QdrantClient(path=config.QDRANT_PATH)
    atexit.register(c.close)  # close cleanly before shutdown (avoids __del__ teardown error)
    return c


def ensure_collection() -> None:
    c = client()
    if not c.collection_exists(COLLECTION):
        c.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=embeddings.dim(), distance=Distance.COSINE),
        )


def upsert_video(session_id: str, video: Video) -> int:
    """Embed and upsert all of a video's chunks. Idempotent: re-running with the same
    (session, video, chunk) overwrites rather than duplicating (uuid5 point ids)."""
    if not video.chunks:
        return 0
    ensure_collection()
    vectors = embeddings.embed_texts([ch.text for ch in video.chunks])
    points = [
        PointStruct(
            id=str(uuid.uuid5(_NS, f"{session_id}:{video.video_id}:{ch.chunk_index}")),
            vector=vec,
            payload={
                "session_id": session_id,
                "video_id": video.video_id,
                "chunk_index": ch.chunk_index,
                "start": ch.start,
                "end": ch.end,
                "text": ch.text,
                "platform": video.platform,
                "creator": video.creator,
            },
        )
        for ch, vec in zip(video.chunks, vectors)
    ]
    client().upsert(COLLECTION, points=points)
    return len(points)


def search(
    session_id: str,
    query: str,
    video_id: str | None = None,
    top_k: int = 4,
    max_start: float | None = None,
) -> list[dict]:
    """Return top_k chunks (payload + score), scoped to the session (and optionally a
    single video and/or a max start-time for "first N seconds" questions)."""
    must = [FieldCondition(key="session_id", match=MatchValue(value=session_id))]
    if video_id:
        must.append(FieldCondition(key="video_id", match=MatchValue(value=video_id)))
    if max_start is not None:
        must.append(FieldCondition(key="start", range=Range(lte=max_start)))

    res = client().query_points(
        COLLECTION,
        query=embeddings.embed_query(query),
        query_filter=Filter(must=must),
        limit=top_k,
        with_payload=True,
    )
    return [{**p.payload, "score": round(p.score, 4)} for p in res.points]
