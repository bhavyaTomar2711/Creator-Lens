"""Shared ingestion helpers: platform detection, hashing, hashtag extraction, ffmpeg."""
from __future__ import annotations

import hashlib
import re

from ..models import Platform

_YT = re.compile(r"(youtube\.com|youtu\.be)", re.I)
_IG = re.compile(r"instagram\.com", re.I)
_HASHTAG = re.compile(r"#(\w+)")


def detect_platform(url: str) -> Platform:
    if _IG.search(url):
        return "instagram"
    if _YT.search(url):
        return "youtube"
    raise ValueError(f"Unsupported URL (need YouTube or Instagram): {url}")


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode()).hexdigest()


def extract_hashtags(text: str | None) -> list[str]:
    if not text:
        return []
    # dedupe, preserve order
    seen, out = set(), []
    for tag in _HASHTAG.findall(text):
        low = tag.lower()
        if low not in seen:
            seen.add(low)
            out.append("#" + tag)
    return out


def ffmpeg_location() -> str | None:
    """Prefer system ffmpeg; fall back to the pip-bundled imageio-ffmpeg binary."""
    import shutil

    if shutil.which("ffmpeg"):
        return None  # on PATH; yt-dlp will find it
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None
