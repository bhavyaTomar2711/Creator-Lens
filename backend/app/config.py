"""Central config — everything reads from env so nothing is hard-coded.

Runs in two modes, switched purely by env (same code, no branches in business logic):
  - LOCAL  (dev): Qdrant on-disk, cache/sessions as JSON files. Zero setup.
  - CLOUD  (deploy): Qdrant Cloud holds vectors AND cache/sessions. Zero local disk.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

from dotenv import load_dotenv

# fastembed/huggingface_hub warns about symlinks on Windows without Developer Mode — harmless.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

# Working dirs (ephemeral in cloud; persistent locally)
DATA_DIR = BACKEND_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
DATA_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

# --- Groq (free tier): Whisper transcription + LLM chat ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")

# --- Local embeddings (free, no key) ---
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")

# --- Qdrant: cloud if URL is set, else local on-disk ---
QDRANT_URL = os.getenv("QDRANT_URL") or None
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
QDRANT_PATH = str(BACKEND_DIR / os.getenv("QDRANT_PATH", "./qdrant_data"))
USE_CLOUD = bool(QDRANT_URL)

# Where cache/sessions live. Defaults to qdrant when cloud is configured (no local disk).
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "qdrant" if USE_CLOUD else "local")

# --- CORS: comma-separated allowed origins (the deployed frontend) ---
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

# --- Instagram auth (IG blocks anonymous yt-dlp). Resolved in priority order: ---
IG_COOKIES_FROM_BROWSER = os.getenv("IG_COOKIES_FROM_BROWSER") or None
IG_COOKIES_FILE = os.getenv("IG_COOKIES_FILE") or None

# In cloud, ship cookies as a base64 env secret; materialize to an ephemeral file at boot.
_cookies_b64 = os.getenv("IG_COOKIES_B64")
if _cookies_b64 and not IG_COOKIES_FILE:
    _path = DATA_DIR / "cookies.txt"
    _path.write_bytes(base64.b64decode(_cookies_b64))
    IG_COOKIES_FILE = str(_path)
