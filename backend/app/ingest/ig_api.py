"""Instagram private web-API enrichment.

yt-dlp gives us likes/comments/creator but NOT view_count or follower_count for reels.
Those are required (R2) and view_count drives engagement rate (R3). Since we're already
authenticated (cookies), we fetch the gaps directly from Instagram's web API:

  - media info  -> play_count / view_count   (via shortcode -> media_id)
  - web profile -> follower_count            (via username)

All best-effort: any failure returns {} and the pipeline falls back to manual override.
"""
from __future__ import annotations

import http.cookiejar
import json
import urllib.request

from .. import config

_APP_ID = "936619743392459"  # Instagram web app id (public, used by instagram.com itself)
_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def shortcode_to_media_id(shortcode: str) -> int:
    """Instagram shortcodes are base64 of the numeric media id."""
    mid = 0
    for ch in shortcode:
        mid = mid * 64 + _ALPHABET.index(ch)
    return mid


def _opener() -> urllib.request.OpenerDirector | None:
    if not config.IG_COOKIES_FILE:
        return None
    cj = http.cookiejar.MozillaCookieJar(config.IG_COOKIES_FILE)
    try:
        cj.load(ignore_discard=True, ignore_expires=True)
    except Exception:
        return None
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def _get_json(opener, url: str) -> dict | None:
    req = urllib.request.Request(
        url,
        headers={"X-IG-App-ID": _APP_ID, "User-Agent": _UA, "Referer": "https://www.instagram.com/"},
    )
    try:
        return json.loads(opener.open(req, timeout=30).read())
    except Exception:
        return None


def enrich(shortcode: str) -> dict:
    """Return {views, follower_count, creator?} for the fields the API exposes."""
    opener = _opener()
    if opener is None:
        return {}

    out: dict = {}

    # 1) media info -> views + (authoritative) like/comment counts + owner username
    media_id = shortcode_to_media_id(shortcode)
    info = _get_json(opener, f"https://i.instagram.com/api/v1/media/{media_id}/info/")
    username = None
    if info and info.get("items"):
        item = info["items"][0]
        views = item.get("play_count") or item.get("view_count") or item.get("ig_play_count")
        if views:
            out["views"] = int(views)
        username = (item.get("user") or {}).get("username")

    # 2) web profile -> follower_count
    if username:
        prof = _get_json(
            opener, f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
        )
        try:
            user = prof["data"]["user"]
            out["follower_count"] = int(user["edge_followed_by"]["count"])
            out["creator"] = user.get("full_name") or username
        except Exception:
            pass

    return out
