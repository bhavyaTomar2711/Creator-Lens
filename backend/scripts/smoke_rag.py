"""Day-2 exit criteria: ingest -> embed -> index in Qdrant -> filtered retrieval,
and prove the url-hash cache makes a re-ingest instant.

Usage:
    python -m scripts.smoke_rag <youtube_url> <instagram_reel_url>
"""
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import service, vectorstore  # noqa: E402

YT = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
IG = sys.argv[2] if len(sys.argv) > 2 else "https://www.instagram.com/reel/DYPR-_7vXXU/"


def hr(title):
    print("\n" + "=" * 70 + f"\n{title}\n" + "=" * 70)


def main():
    hr("1) INGEST + EMBED + INDEX")
    t0 = time.perf_counter()
    res = service.ingest_pair(YT, IG)
    sid = res["session_id"]
    print(f"session_id   : {sid}")
    print(f"indexed      : A={res['chunks_indexed']['A']} chunks, B={res['chunks_indexed']['B']} chunks")
    print(f"A engagement : {res['video_a'].engagement_rate}%  | B engagement: {res['video_b'].engagement_rate}%")
    print(f"took         : {time.perf_counter() - t0:.1f}s (first run: downloads + Whisper)")

    hr("2) RETRIEVAL (filtered by session + video, with citations)")
    queries = [
        ("hook / opening line", "what is the opening hook of the video", None, None),
        ("first 5 seconds of A", "opening", "A", 5.0),
        ("topic of B", "what is this video about", "B", None),
    ]
    for label, q, vid, max_start in queries:
        print(f"\n  Q: {label}  (video={vid or 'both'}, max_start={max_start})")
        for r in vectorstore.search(sid, q, video_id=vid, top_k=2, max_start=max_start):
            cite = f"[{r['video_id']} · chunk {r['chunk_index']} · {r['start']:.1f}-{r['end']:.1f}s]"
            print(f"    {r['score']:.3f} {cite} {r['text'][:80]}...")

    hr("3) CACHE TEST (re-ingest same URLs -> should be near-instant)")
    t1 = time.perf_counter()
    service.ingest_pair(YT, IG)
    print(f"re-ingest took: {time.perf_counter() - t1:.1f}s (cache hit: no download/Whisper)")


if __name__ == "__main__":
    main()
