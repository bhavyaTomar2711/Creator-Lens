"""Day-1 exit criteria: ingest a real YouTube URL (A) and a real Instagram Reel (B)
end-to-end into the Video data model, and print the result.

Usage:
    python -m scripts.smoke_ingest <youtube_url> <instagram_reel_url>

Inputs are hard-coded-able (the brief allows hard-coded inputs); outputs are 100% dynamic.
"""
import sys
from pathlib import Path

# Windows consoles default to cp1252 and choke on emoji/♪ in transcripts.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingest.pipeline import ingest  # noqa: E402

# Sensible defaults so it runs with no args; override on the CLI.
DEFAULT_YT = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
DEFAULT_IG = "https://www.instagram.com/reel/C8XYZexample/"


def show(v):
    print("=" * 70)
    print(f"[{v.video_id}] {v.platform.upper()}  {v.url}")
    print(f"  creator        : {v.creator}  (followers: {v.follower_count})")
    print(f"  title          : {v.title}")
    print(f"  uploaded       : {v.upload_date}   duration: {v.duration_sec}s")
    print(f"  views/likes/cmt: {v.views} / {v.likes} / {v.comments}")
    print(f"  ENGAGEMENT     : {v.engagement_rate}%   <-- computed in code")
    print(f"  hashtags       : {v.hashtags}")
    print(f"  transcript     : {v.transcript_source}, {len(v.transcript)} chars, {len(v.chunks)} chunks")
    if v.chunks:
        c = v.chunks[0]
        print(f"  first chunk    : [{c.start:.1f}-{c.end:.1f}s] {c.text[:120]}...")


def main():
    yt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_YT
    ig = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_IG
    print(f"Ingesting A (YouTube): {yt}\nIngesting B (Instagram): {ig}\n")
    show(ingest(yt, "A"))
    show(ingest(ig, "B"))


if __name__ == "__main__":
    main()
