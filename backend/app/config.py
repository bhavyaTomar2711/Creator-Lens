"""Central config — everything reads from .env so nothing is hard-coded."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# fastembed/huggingface_hub warns about symlinks on Windows without Developer Mode — harmless.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

# --- Groq (free tier): Whisper transcription + LLM chat ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")

# --- Local embeddings (free, no key) ---
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")

# --- Qdrant local on-disk mode (no Docker, no key) ---
QDRANT_PATH = str(BACKEND_DIR / os.getenv("QDRANT_PATH", "./qdrant_data"))

# --- Instagram auth (IG blocks anonymous yt-dlp). Pick ONE: ---
# Easiest: point at a browser where you're logged into Instagram (chrome/edge/firefox/brave).
IG_COOKIES_FROM_BROWSER = os.getenv("IG_COOKIES_FROM_BROWSER") or None
# Or: path to an exported cookies.txt (Netscape format).
IG_COOKIES_FILE = os.getenv("IG_COOKIES_FILE") or None

# Working dirs
DATA_DIR = BACKEND_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
DATA_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)
