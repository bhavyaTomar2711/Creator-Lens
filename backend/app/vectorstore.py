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
    PayloadSchemaType,
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
    if config.USE_CLOUD:
        c = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)
    else:
        c = QdrantClient(path=config.QDRANT_PATH)
    atexit.register(c.close)  # close cleanly before shutdown (avoids __del__ teardown error)
    return c


# Fields we filter on. Qdrant Cloud (unlike local mode) REQUIRES a payload index per
# filtered field, so we create them explicitly and idempotently.
_INDEXED_FIELDS = {
    "session_id": PayloadSchemaType.KEYWORD,
    "video_id": PayloadSchemaType.KEYWORD,
    "start": PayloadSchemaType.FLOAT,
}


def ensure_collection() -> None:
    c = client()
    if not c.collection_exists(COLLECTION):
        c.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=embeddings.dim(), distance=Distance.COSINE),
        )
    for field, schema in _INDEXED_FIELDS.items():
        try:
            c.create_payload_index(COLLECTION, field_name=field, field_schema=schema)
        except Exception:
            pass  # already exists


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


# --- Tiny key-value store on Qdrant (used for sessions/cache in cloud mode) ---
# These collections are never vector-searched; we only get/put by id. The 1-d vector
# is a placeholder Qdrant requires per point.
_KV_VEC = [1.0]


def _kv_id(key: str) -> str:
    return str(uuid.uuid5(_NS, key))


def kv_put(collection: str, key: str, payload: dict) -> None:
    c = client()
    if not c.collection_exists(collection):
        c.create_collection(collection, vectors_config=VectorParams(size=1, distance=Distance.DOT))
    c.upsert(collection, points=[PointStruct(id=_kv_id(key), vector=_KV_VEC, payload=payload)])


def kv_get(collection: str, key: str) -> dict | None:
    c = client()
    if not c.collection_exists(collection):
        return None
    pts = c.retrieve(collection, ids=[_kv_id(key)], with_payload=True)
    return pts[0].payload if pts else None
