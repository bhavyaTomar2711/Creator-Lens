"""Instagram Reel ingestion — the hard one (no public API).

Metadata via yt-dlp; transcript via download -> ffmpeg audio -> Whisper.
Handles rate-limits/login with optional cookies, and degrades to manual override
upstream so a blocked reel never kills the demo.
"""
from __future__ import annotations

import re

from .. import config
from . import ig_api
from .common import extract_hashtags, ffmpeg_location
from .transcribe import Segment, transcribe

_SHORTCODE = re.compile(r"/(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)")


def shortcode_from_url(url: str) -> str | None:
    m = _SHORTCODE.search(url)
    return m.group(1) if m else None


def _ydl_opts(extra: dict | None = None) -> dict:
    opts: dict = {"quiet": True, "no_warnings": True}
    # IG requires auth. Prefer browser cookies (zero manual export); else cookies.txt.
    if config.IG_COOKIES_FROM_BROWSER:
        opts["cookiesfrombrowser"] = (config.IG_COOKIES_FROM_BROWSER,)
    elif config.IG_COOKIES_FILE:
        opts["cookiefile"] = config.IG_COOKIES_FILE
    ff = ffmpeg_location()
    if ff:
        opts["ffmpeg_location"] = ff
    if extra:
        opts.update(extra)
    return opts


def fetch_metadata(url: str) -> dict:
    from yt_dlp import YoutubeDL

    with YoutubeDL(_ydl_opts({"skip_download": True})) as ydl:
        info = ydl.extract_info(url, download=False)

    upload = info.get("upload_date")  # YYYYMMDD
    desc = info.get("description") or info.get("title")
    meta = {
        "creator": info.get("uploader") or info.get("channel") or info.get("uploader_id"),
        "follower_count": info.get("channel_follower_count"),
        "title": info.get("title"),
        "upload_date": f"{upload[:4]}-{upload[4:6]}-{upload[6:]}" if upload else None,
        "duration_sec": info.get("duration"),
        "views": info.get("view_count") or info.get("play_count") or 0,
        "likes": info.get("like_count") or 0,
        "comments": info.get("comment_count") or 0,
        "hashtags": extract_hashtags(desc),
        "thumbnail": info.get("thumbnail"),
    }

    # yt-dlp can't see IG views/followers — enrich from the authenticated web API.
    shortcode = shortcode_from_url(url)
    if shortcode and (not meta["views"] or not meta["follower_count"]):
        extra = ig_api.enrich(shortcode)
        if not meta["views"] and extra.get("views"):
            meta["views"] = extra["views"]
        if not meta["follower_count"] and extra.get("follower_count"):
            meta["follower_count"] = extra["follower_count"]
        if extra.get("creator"):
            meta["creator"] = extra["creator"]
    return meta


def fetch_transcript(url: str, url_hash: str) -> tuple[str, list[Segment]]:
    audio_path = _download_audio(url, url_hash)
    return transcribe(audio_path)


def _download_audio(url: str, url_hash: str) -> str:
    """Download best audio and extract to mp3 in AUDIO_DIR. Returns the file path."""
    from yt_dlp import YoutubeDL

    out_base = str(config.AUDIO_DIR / url_hash)
    opts = _ydl_opts(
        {
            "format": "bestaudio/best",
            "outtmpl": out_base + ".%(ext)s",
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}
            ],
        }
    )
    with YoutubeDL(opts) as ydl:
        ydl.download([url])
    return out_base + ".mp3"
