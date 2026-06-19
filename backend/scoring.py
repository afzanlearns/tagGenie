import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from backend import extraction
from backend import embeddings
from backend import trends
from backend import llm
from backend.models import CandidateTag, GapTag, ScoreResponse
from backend.niche_manager import get_active_niche

DATA_DIR = Path(__file__).parent.parent / "data"
WEIGHTS_FILE = DATA_DIR / "weights.json"

PLATFORM_WEIGHTS = {
    "LinkedIn": {"hashtag": 0.3, "keyword": 1.0},
    "Instagram": {"hashtag": 1.0, "keyword": 0.4},
    "X": {"hashtag": 0.7, "keyword": 0.6},
    "TikTok": {"hashtag": 0.9, "keyword": 0.5},
}

_similarity_model = None


def _get_sim_model():
    global _similarity_model
    if _similarity_model is None:
        _similarity_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _similarity_model


def load_weights() -> dict:
    if WEIGHTS_FILE.exists():
        with open(WEIGHTS_FILE) as f:
            saved = json.load(f)
        for platform, weights in saved.items():
            if platform in PLATFORM_WEIGHTS:
                PLATFORM_WEIGHTS[platform].update(weights)
    return PLATFORM_WEIGHTS


def save_weights():
    with open(WEIGHTS_FILE, "w") as f:
        json.dump(
            {k: dict(v) for k, v in PLATFORM_WEIGHTS.items()}, f, indent=2
        )


def compute_confidence(fallback_mode: bool, niche_id: str = None) -> float:
    if niche_id is None:
        niche_id = get_active_niche()
    confidence = 100.0
    if fallback_mode:
        confidence -= 30
    if embeddings.get_corpus_size(niche_id) < 20:
        confidence -= 10
    return confidence


def semantic_relevance(tag: str, topic: str) -> float:
    model = _get_sim_model()
    emb_tag = model.encode([tag])
    emb_topic = model.encode([topic])
    sim = np.dot(emb_tag, emb_topic.T)[0][0]
    return round(min(100.0, max(0.0, sim * 100.0)), 1)


def score_topic(topic: str, product: str, platform: str, niche_id: str = None) -> ScoreResponse:
    if niche_id is None:
        niche_id = get_active_niche()

    embeddings.seed_corpus(niche_id)

    candidates = extraction.extract_candidates(topic, product, niche_id)
    pw = PLATFORM_WEIGHTS.get(platform, {"hashtag": 0.5, "keyword": 0.5})

    global_fallback = False
    ranked = []
    gap = []

    for c in candidates:
        tag = c["tag"]
        tag_type = c["type"]

        trend_data = trends.get_trend_volume(tag)
        trend_volume = trend_data["volume"]
        if trend_data["fallback_mode"]:
            global_fallback = True

        rel = semantic_relevance(tag, topic)
        reach_score = round((trend_volume * 0.6) + (rel * 0.4), 1)

        comp_score = embeddings.compute_competition_score(tag, niche_id)

        confidence = compute_confidence(trend_data["fallback_mode"], niche_id)
        composite = (
            (reach_score * 0.5)
            + ((100 - comp_score) * 0.3)
            + (confidence * 0.2)
        )
        type_weight = pw.get(tag_type, 0.5)
        final_score = round(composite * type_weight, 1)

        ranked.append(
            {"tag": tag, "type": tag_type, "reach_score": reach_score,
             "competition_score": comp_score, "final_score": final_score,
             "confidence": confidence, "rationale": ""}
        )

        if reach_score > 60 and comp_score < 30:
            reason = f"High reach ({reach_score:.0f}) + low saturation ({comp_score:.0f}) — blue ocean opportunity"
            gap.append(GapTag(tag=tag, type=tag_type, reach_score=reach_score,
                              competition_score=comp_score, reason=reason))

    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    top_confidence = compute_confidence(global_fallback, niche_id)

    top_10 = ranked[:10]
    for item in top_10:
        item["rationale"] = llm.generate_rationale(
            item["tag"], item["reach_score"],
            item["competition_score"], item["final_score"],
            niche_id
        )

    ranked_tags = [
        CandidateTag(**item) for item in ranked[:10]
    ]

    gap.sort(key=lambda x: x.reach_score, reverse=True)

    return ScoreResponse(
        topic=topic,
        platform=platform,
        niche=niche_id,
        ranked_tags=ranked_tags,
        gap_tags=gap,
        confidence=top_confidence,
        fallback_mode=global_fallback,
    )
