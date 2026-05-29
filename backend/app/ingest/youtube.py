"""YouTube ingestion: metadata via yt-dlp, transcript via free captions (no Whisper cost)."""
from __future__ import annotations

import re

from .common import extract_hashtags
from .transcribe import Segment

_VID = re.compile(r"(?:v=|/shorts/|youtu\.be/|/embed/)([A-Za-z0-9_-]{11})")


def video_id_from_url(url: str) -> str | None:
    m = _VID.search(url)
    return m.group(1) if m else None


def fetch_metadata(url: str) -> dict:
    """Pull metadata with yt-dlp (no download)."""
    from yt_dlp import YoutubeDL

    with YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    upload = info.get("upload_date")  # YYYYMMDD
    return {
        "creator": info.get("uploader") or info.get("channel"),
        "follower_count": info.get("channel_follower_count"),
        "title": info.get("title"),
        "upload_date": f"{upload[:4]}-{upload[4:6]}-{upload[6:]}" if upload else None,
        "duration_sec": info.get("duration"),
        "views": info.get("view_count") or 0,
        "likes": info.get("like_count") or 0,
        "comments": info.get("comment_count") or 0,
        "hashtags": extract_hashtags(info.get("description")),
        "thumbnail": info.get("thumbnail"),
    }


def fetch_transcript(url: str) -> tuple[str, list[Segment]]:
    """Free captions via youtube-transcript-api. Returns ("", []) if none available
    (caller then falls back to yt-dlp audio -> Whisper)."""
    vid = video_id_from_url(url)
    if not vid:
        return "", []

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        # Support both the 0.6.x classmethod API and the 1.x instance API.
        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            raw = YouTubeTranscriptApi.get_transcript(vid)
            entries = [{"text": r["text"], "start": r["start"], "dur": r["duration"]} for r in raw]
        else:
            fetched = YouTubeTranscriptApi().fetch(vid)
            entries = [{"text": s.text, "start": s.start, "dur": s.duration} for s in fetched]
    except Exception as e:  # noqa: BLE001
        print(f"[youtube] no captions ({e}); will fall back to Whisper")
        return "", []

    segments = [
        {"start": e["start"], "end": e["start"] + e["dur"], "text": e["text"].strip()}
        for e in entries
        if e["text"].strip()
    ]
    text = " ".join(s["text"] for s in segments).strip()
    return text, segments
