"""Local embeddings via fastembed (BAAI/bge-small-en-v1.5, 384-d ONNX).

Free, no API key, runs on CPU. The model is downloaded once on first use (~130 MB)
and cached on disk by fastembed. We keep one model instance per process (lru_cache).
"""
from __future__ import annotations

from functools import lru_cache

from . import config


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=config.EMBED_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of documents -> list of 384-float vectors."""
    return [vec.tolist() for vec in _model().embed(texts)]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


@lru_cache(maxsize=1)
def dim() -> int:
    return len(embed_query("dimension probe"))
