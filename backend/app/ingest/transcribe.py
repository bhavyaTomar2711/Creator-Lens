"""Whisper transcription.

Primary: Groq Whisper (free tier, fast) — returns word/segment timestamps so transcript
chunks stay aligned to the video (needed for the "first 5 seconds hook" question + seek).
Fallback: faster-whisper (fully offline, $0, no key) if Groq is unavailable.

Returns (full_text, segments) where segments = [{"start", "end", "text"}, ...].
"""
from __future__ import annotations

from .. import config

Segment = dict  # {"start": float, "end": float, "text": str}


def transcribe(audio_path: str) -> tuple[str, list[Segment]]:
    if config.GROQ_API_KEY:
        try:
            return _groq(audio_path)
        except Exception as e:  # noqa: BLE001 — degrade gracefully to offline
            print(f"[transcribe] Groq failed ({e}); trying faster-whisper offline...")
    return _faster_whisper(audio_path)


def _groq(audio_path: str) -> tuple[str, list[Segment]]:
    from groq import Groq

    client = Groq(api_key=config.GROQ_API_KEY)
    with open(audio_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            file=(audio_path, f.read()),
            model=config.GROQ_WHISPER_MODEL,
            response_format="verbose_json",  # gives timestamped segments
        )
    text = (resp.text or "").strip()
    segments = [
        {"start": float(s["start"]), "end": float(s["end"]), "text": s["text"].strip()}
        for s in (getattr(resp, "segments", None) or [])
    ]
    return text, segments


def _faster_whisper(audio_path: str) -> tuple[str, list[Segment]]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError(
            "No Groq key and faster-whisper not installed. "
            "Add GROQ_API_KEY to .env, or `pip install faster-whisper`."
        ) from e

    model = WhisperModel("base", device="cpu", compute_type="int8")
    seg_iter, _ = model.transcribe(audio_path)
    segments = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in seg_iter]
    text = " ".join(s["text"] for s in segments).strip()
    return text, segments
