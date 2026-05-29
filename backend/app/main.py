"""FastAPI app. Day 1: health + /ingest (metadata + transcript). Vector store & the
LangGraph chat endpoint land on Day 2/3."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import service
from .models import Video

app = FastAPI(title="CreatorLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    youtube_url: str
    instagram_url: str
    # optional manual overrides for fields a blocked reel can't supply (e.g. follower_count)
    overrides_a: dict | None = None
    overrides_b: dict | None = None


class IngestResponse(BaseModel):
    session_id: str
    video_a: Video
    video_b: Video
    chunks_indexed: dict


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
def ingest_pair(req: IngestRequest):
    """Ingest both videos, embed + index their chunks, and open a chat session."""
    result = service.ingest_pair(
        req.youtube_url, req.instagram_url, req.overrides_a, req.overrides_b
    )
    return IngestResponse(**result)
