from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

VALID_PLATFORMS = {"LinkedIn", "Instagram", "X", "TikTok", "Pinterest"}

CATEGORIES = [
    "Product", "Hashtag", "Industry Term", "Audience", "Topic", "Brand", "Keyword"
]

CONFIDENCE_BANDS = [
    (90, 100, "Elite"),
    (80, 89, "Excellent"),
    (70, 79, "Very Strong"),
    (60, 69, "Strong"),
    (50, 59, "Moderate"),
    (40, 49, "Fair"),
    (0, 39, "Weak"),
]

def confidence_band(score: float) -> str:
    for lo, hi, label in CONFIDENCE_BANDS:
        if lo <= score <= hi:
            return label
    return "Weak"


class ScoreRequest(BaseModel):
    topic: str
    product: str
    platform: Literal["LinkedIn", "Instagram", "X", "TikTok", "Pinterest"]
    niche: str = "gps-telematics"
    include_baseline: bool = False


class CandidateTag(BaseModel):
    tag: str
    type: Literal["hashtag", "keyword"]
    semantic_relevance: float = 0.0
    trend_score: float = 0.0
    competition_score: float = 0.0
    platform_fit: float = 0.0
    history_confidence: float = 0.0
    final_score: float = 0.0
    explanation: str = ""
    category: str = ""
    confidence_band: str = "Weak"
    opportunity_score: float = 0.0
    is_blue_ocean: bool = False
    is_hidden_gem: bool = False
    is_high_competition: bool = False
    score_breakdown: dict = {}
    quality_labels: list[str] = []


class GapTag(BaseModel):
    tag: str
    type: Literal["hashtag", "keyword"]
    semantic_relevance: float = 0.0
    trend_score: float = 0.0
    competition_score: float = 0.0
    opportunity_score: float = 0.0
    reason: str


class HighCompetitionTag(BaseModel):
    tag: str
    type: Literal["hashtag", "keyword"]
    competition_score: float
    reason: str = "Very saturated."


class HiddenGemTag(BaseModel):
    tag: str
    type: Literal["hashtag", "keyword"]
    semantic_relevance: float = 0.0
    competition_score: float = 0.0
    trend_score: float = 0.0
    reason: str


class RejectedCandidateTag(BaseModel):
    tag: str
    type: Literal["hashtag", "keyword"]
    reason: str


class BaselineTag(BaseModel):
    tag: str
    type: Literal["hashtag", "keyword"]
    score: float
    semantic_relevance: float = 0.0


class MixSummary(BaseModel):
    hashtags: int = 0
    products: int = 0
    industry_terms: int = 0
    audience: int = 0
    topics: int = 0
    brands: int = 0
    keywords: int = 0


class ScoreAnalytics(BaseModel):
    avg_relevance: float = 0.0
    avg_trend: float = 0.0
    avg_competition: float = 0.0
    avg_platform_fit: float = 0.0
    avg_final_score: float = 0.0
    diversity: float = 0.0
    unique_categories: int = 0
    blue_ocean_count: int = 0
    high_competition_count: int = 0
    hidden_gem_count: int = 0
    total_candidates_evaluated: int = 0


class ScoreResponse(BaseModel):
    topic: str
    platform: str
    niche: str = "gps-telematics"
    ranked_tags: list[CandidateTag]
    gap_tags: list[GapTag]
    high_competition_tags: list[HighCompetitionTag] = []
    hidden_gems: list[HiddenGemTag] = []
    rejected_candidates: list[RejectedCandidateTag] = []
    baseline_tags: list[BaselineTag] = []
    mix_summary: MixSummary = MixSummary()
    analytics: ScoreAnalytics = ScoreAnalytics()
    confidence: float
    fallback_mode: bool
    timings: dict = {}


class EngagementMetrics(BaseModel):
    likes: int
    shares: int
    comments: int


class FeedbackRequest(BaseModel):
    post_id: str
    platform: Literal["LinkedIn", "Instagram", "X", "TikTok", "Pinterest"]
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


class GenerateDraftRequest(BaseModel):
    niche_id: str
    display_name: str
    sample_posts: list[str]


class SaveNicheDraftRequest(BaseModel):
    niche_id: str
    display_name: str
    description: str
    sample_posts: list[str]
    corpus: list[str]
    jargon: dict
    sample_topics: list[str]
    profile: Optional[dict] = None


class NicheProfile(BaseModel):
    industry_terms: list[str] = []
    products: list[str] = []
    topics: list[str] = []
    hashtags: list[str] = []
    brands: list[str] = []
    audience: list[str] = []
    synonyms: dict[str, list[str]] = {}


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


class SaveHistoryRequest(BaseModel):
    topic: str
    product: str
    platform: str
    niche: str
    ranked_tags: list[CandidateTag]
    gap_tags: list[GapTag]
    high_competition_tags: list[HighCompetitionTag] = []
    hidden_gems: list[HiddenGemTag] = []
    analytics: ScoreAnalytics = ScoreAnalytics()
    mix_summary: MixSummary = MixSummary()
    confidence: float = 0.0
    fallback_mode: bool = False


class SavedSetRequest(BaseModel):
    name: str
    topic: str
    product: str
    platform: str
    niche: str
    ranked_tags: list[CandidateTag]
    gap_tags: list[GapTag]
    analytics: ScoreAnalytics = ScoreAnalytics()
    mix_summary: MixSummary = MixSummary()
    confidence: float = 0.0


class UserSettingsRequest(BaseModel):
    preferred_platform: Optional[str] = None
    default_niche: Optional[str] = None
    default_export_format: Optional[str] = None
    theme: Optional[str] = None
    sort_preference: Optional[str] = None
