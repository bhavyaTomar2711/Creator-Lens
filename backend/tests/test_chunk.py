"""Chunking tests — verify orphan-tail merging and timestamp carry-through.
Run: python -m tests.test_chunk
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingest.chunk import chunk_segments  # noqa: E402


def _seg(start, end, text):
    return {"start": start, "end": end, "text": text}


def test_empty():
    assert chunk_segments([]) == []


def test_single_segment_one_chunk():
    chunks = chunk_segments([_seg(0, 5, "hello world")])
    assert len(chunks) == 1
    assert chunks[0].start == 0 and chunks[0].end == 5


def test_tiny_tail_is_merged():
    # 3 big segments + 1 tiny tail -> tail must fold into previous, not become its own chunk
    segs = [_seg(i, i + 1, "x" * 300) for i in range(3)] + [_seg(3, 4, "tiny")]
    chunks = chunk_segments(segs, chunk_chars=600, min_tail_chars=240)
    assert all(len(c.text) >= 200 for c in chunks), "no orphan tail chunk allowed"


def test_timestamps_span_segments():
    segs = [_seg(0, 10, "a" * 400), _seg(10, 20, "b" * 400)]
    chunks = chunk_segments(segs, chunk_chars=300)
    assert chunks[0].start == 0
    assert chunks[-1].end == 20


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
