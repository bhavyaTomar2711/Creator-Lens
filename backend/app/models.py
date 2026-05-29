"""Data model for a comparison.

Key design decision: engagement rate is computed HERE, in code — never asked of the
LLM. The model reasons about *why* engagement differs; it never invents the *numbers*.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Platform = Literal["youtube", "instagram"]
VideoLabel = Literal["A", "B"]


def engagement_rate(likes: int, comments: int, views: int) -> float:
    """(likes + comments) / views * 100, rounded to 2dp.

    Returns 0.0 when views is 0/unknown to avoid divide-by-zero blowing up ingestion.
    """
    if not views or views <= 0:
        return 0.0
    return round((likes + comments) / views * 100, 2)


class Chunk(BaseModel):
    chunk_index: int
    text: str
    start: float = 0.0  # seconds into the video (enables "first 5s" filtering + seek)
    end: float = 0.0


class Video(BaseModel):
    video_id: VideoLabel              # "A" (YouTube) / "B" (Instagram) — UI + citation label
    url: str
    url_hash: str                     # sha256(url) — dedup / cache key
    platform: Platform

    # metadata (R2)
    creator: Optional[str] = None
    follower_count: Optional[int] = None
    title: Optional[str] = None
    upload_date: Optional[str] = None     # YYYY-MM-DD
    duration_sec: Optional[int] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    hashtags: list[str] = Field(default_factory=list)
    thumbnail: Optional[str] = None

    # derived (R3) — computed, not hallucinated
    engagement_rate: float = 0.0

    # transcript (R2/R4)
    transcript: str = ""
    transcript_source: Literal["captions", "whisper", "manual", "none"] = "none"
    chunks: list[Chunk] = Field(default_factory=list)

    @field_validator("duration_sec", mode="before")
    @classmethod
    def _floor_duration(cls, v):
        # Instagram reports fractional seconds (e.g. 76.72); we store whole seconds.
        return int(v) if isinstance(v, float) else v

    def recompute_engagement(self) -> "Video":
        self.engagement_rate = engagement_rate(self.likes, self.comments, self.views)
        return self
