from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class ScoreRequest(BaseModel):
    topic: str
    product: str
    platform: Literal["LinkedIn", "Instagram", "X", "TikTok"]
    include_baseline: bool = False


class CandidateTag(BaseModel):
    tag: str
    type: Literal["hashtag", "keyword"]
    reach_score: float
    competition_score: float
    final_score: float
    confidence: float
    rationale: str = ""


class GapTag(BaseModel):
    tag: str
    type: Literal["hashtag", "keyword"]
    reach_score: float
    competition_score: float
    reason: str


class BaselineTag(BaseModel):
    tag: str
    type: Literal["hashtag", "keyword"]
    score: float


class ScoreResponse(BaseModel):
    topic: str
    platform: str
    ranked_tags: list[CandidateTag]
    gap_tags: list[GapTag]
    baseline_tags: list[BaselineTag] = []
    confidence: float
    fallback_mode: bool
    timings: dict = {}


class EngagementMetrics(BaseModel):
    likes: int
    shares: int
    comments: int


class FeedbackRequest(BaseModel):
    post_id: str
    platform: Literal["LinkedIn", "Instagram", "X", "TikTok"]
    tags_used: list[str]
    engagement: EngagementMetrics


class IngestTopic(BaseModel):
    topic: str
    momentum_score: float


class IngestRequest(BaseModel):
    topics: list[IngestTopic]
