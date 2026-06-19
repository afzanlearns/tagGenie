from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

VALID_PLATFORMS = {"LinkedIn", "Instagram", "X", "TikTok"}


class ScoreRequest(BaseModel):
    topic: str
    product: str
    platform: Literal["LinkedIn", "Instagram", "X", "TikTok"]
    niche: str = "gps-telematics"
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
    niche: str = "gps-telematics"
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
    niche: str = "gps-telematics"


class IngestTopic(BaseModel):
    topic: str
    momentum_score: float


class IngestRequest(BaseModel):
    topics: list[IngestTopic]


class CreateNicheRequest(BaseModel):
    niche_id: str
    display_name: str
    description: str = ""
    sample_posts: list[str]


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
