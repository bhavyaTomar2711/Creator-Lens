"""Timestamped chunking.

Merge transcript segments into ~chunk_chars-sized chunks while carrying start/end
timestamps. Timestamps let us (a) answer "first 5 seconds" precisely and (b) seek the
video player to a cited moment. (Tuned further on Day 2.)
"""
from __future__ import annotations

from ..models import Chunk
from .transcribe import Segment


def chunk_segments(segments: list[Segment], chunk_chars: int = 500, overlap: int = 1) -> list[Chunk]:
    """Greedy merge of segments up to ~chunk_chars. `overlap` = #segments to repeat
    between chunks to preserve cross-boundary context."""
    if not segments:
        return []

    chunks: list[Chunk] = []
    buf: list[Segment] = []
    buf_len = 0
    idx = 0

    def flush(b: list[Segment]) -> None:
        nonlocal idx
        if not b:
            return
        chunks.append(
            Chunk(
                chunk_index=idx,
                text=" ".join(s["text"] for s in b).strip(),
                start=round(float(b[0]["start"]), 2),
                end=round(float(b[-1]["end"]), 2),
            )
        )
        idx += 1

    for seg in segments:
        buf.append(seg)
        buf_len += len(seg["text"])
        if buf_len >= chunk_chars:
            flush(buf)
            buf = buf[-overlap:] if overlap else []
            buf_len = sum(len(s["text"]) for s in buf)

    flush(buf)
    return chunks
