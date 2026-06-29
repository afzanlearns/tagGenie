import json
import copy
from pathlib import Path

from backend import extraction
from backend import embeddings
from backend import ranking
from backend.models import CandidateTag, GapTag, ScoreResponse, BaselineTag
from backend.niche_manager import get_active_niche, get_niche_profile

DATA_DIR = Path(__file__).parent.parent / "data"
WEIGHTS_FILE = DATA_DIR / "weights.json"

DEFAULT_WEIGHTS = {
    "LinkedIn": {"hashtag": 0.3, "keyword": 1.0},
    "Instagram": {"hashtag": 1.0, "keyword": 0.4},
    "X": {"hashtag": 0.7, "keyword": 0.6},
    "TikTok": {"hashtag": 0.9, "keyword": 0.5},
}

PLATFORM_WEIGHTS = copy.deepcopy(DEFAULT_WEIGHTS)


def _get_weights_path(user_id: str = None) -> Path:
    if user_id and not user_id.startswith("guest_"):
        user_dir = DATA_DIR / "users" / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / "weights.json"
    return WEIGHTS_FILE


def load_weights(user_id: str = None) -> dict:
    if user_id and user_id.startswith("guest_"):
        from backend.guest_store import get_weights as _guest_weights
        gw = _guest_weights(user_id)
        PLATFORM_WEIGHTS.clear()
        PLATFORM_WEIGHTS.update(gw)
        return PLATFORM_WEIGHTS

    path = _get_weights_path(user_id)
    if path.exists():
        with open(path) as f:
            saved = json.load(f)
        for platform, weights in saved.items():
            if platform in PLATFORM_WEIGHTS:
                PLATFORM_WEIGHTS[platform].update(weights)
    elif WEIGHTS_FILE.exists() and (user_id is None or user_id.startswith("guest_")):
        with open(WEIGHTS_FILE) as f:
            saved = json.load(f)
        for platform, weights in saved.items():
            if platform in PLATFORM_WEIGHTS:
                PLATFORM_WEIGHTS[platform].update(weights)
    return PLATFORM_WEIGHTS


def save_weights(user_id: str = None):
    if user_id and user_id.startswith("guest_"):
        from backend.guest_store import save_weights as _guest_save_weights
        _guest_save_weights(user_id, dict(PLATFORM_WEIGHTS))
        return
    path = _get_weights_path(user_id)
    with open(path, "w") as f:
        json.dump(
            {k: dict(v) for k, v in PLATFORM_WEIGHTS.items()}, f, indent=2
        )


def compute_confidence(fallback_mode: bool = False, niche_id: str = None, user_id: str = None) -> float:
    if niche_id is None:
        niche_id = get_active_niche(user_id)
    return ranking.compute_profile_confidence(niche_id, user_id)


def score_topic(
    topic: str,
    product: str,
    platform: str,
    niche_id: str = None,
    user_id: str = None,
) -> ScoreResponse:
    if niche_id is None:
        niche_id = get_active_niche(user_id)

    load_weights(user_id)
    embeddings.seed_corpus(niche_id, user_id)

    raw_candidates = extraction.extract_candidates(topic, product, niche_id, user_id)
    if not raw_candidates:
        return ScoreResponse(
            topic=topic,
            platform=platform,
            niche=niche_id,
            ranked_tags=[],
            gap_tags=[],
            confidence=0.0,
            fallback_mode=False,
        )

    ranked = ranking.rank_candidates(
        raw_candidates, topic, product, platform, niche_id, user_id,
    )

    top_confidence = ranking.compute_profile_confidence(niche_id, user_id)
    fallback_mode = top_confidence < 50.0

    gaps = ranking.find_gaps(ranked)
    gap_tags = [
        GapTag(**g) for g in gaps
    ]

    ranked_tags = ranked[:10]

    return ScoreResponse(
        topic=topic,
        platform=platform,
        niche=niche_id,
        ranked_tags=ranked_tags,
        gap_tags=gap_tags,
        confidence=top_confidence,
        fallback_mode=fallback_mode,
    )


def semantic_relevance(tag: str, topic: str, product: str = "") -> float:
    """Backward-compatible wrapper: product is optional."""
    return ranking.compute_semantic_relevance(tag, topic, product)


def _get_sim_model():
    """Backward-compatible alias — pre-loads embedding model on startup."""
    from backend.ranking import _get_sim
    return _get_sim()

# backward-compatible aliases for existing tests
from backend.ranking import (  # noqa: F401
    compute_trend_score,
    compute_low_competition,
    compute_platform_fit,
    compute_profile_confidence,
    normalise_tag,
    apply_diversity,
    generate_explanation,
)
