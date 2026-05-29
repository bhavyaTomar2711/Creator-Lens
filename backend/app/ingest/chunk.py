"""Timestamped chunking.

Merge transcript segments into ~chunk_chars-sized chunks while carrying start/end
timestamps. Timestamps let us (a) answer "first 5 seconds" precisely and (b) seek the
video player to a cited moment.

Two-pass design (refined Day 2):
  1. greedy-group segments up to ~chunk_chars
  2. fold an undersized tail group into the previous one (no 3-word orphan chunks)
  3. prepend the previous group's trailing segment(s) as overlap so context isn't
     severed at a boundary
"""
from __future__ import annotations

from ..models import Chunk
from .transcribe import Segment


def chunk_segments(
    segments: list[Segment],
    chunk_chars: int = 600,
    overlap_segments: int = 1,
    min_tail_chars: int = 240,
) -> list[Chunk]:
    if not segments:
        return []

    # Pass 1 — greedy groups, no overlap yet
    groups: list[list[Segment]] = []
    cur: list[Segment] = []
    cur_len = 0
    for s in segments:
        cur.append(s)
        cur_len += len(s["text"])
        if cur_len >= chunk_chars:
            groups.append(cur)
            cur, cur_len = [], 0
    if cur:
        groups.append(cur)

    # Pass 2 — fold a too-small tail into the previous group
    if len(groups) >= 2 and sum(len(s["text"]) for s in groups[-1]) < min_tail_chars:
        groups[-2].extend(groups.pop())

    # Pass 3 — build chunks, prepending overlap context from the previous group
    chunks: list[Chunk] = []
    for i, g in enumerate(groups):
        segs = (groups[i - 1][-overlap_segments:] + g) if (overlap_segments and i > 0) else g
        chunks.append(
            Chunk(
                chunk_index=i,
                text=" ".join(s["text"] for s in segs).strip(),
                start=round(float(segs[0]["start"]), 2),
                end=round(float(segs[-1]["end"]), 2),
            )
        )
    return chunks
