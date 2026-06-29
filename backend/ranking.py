"""Recommendation ranking engine.

Replaces the old composite-score approach with a structured multi-signal
ranking that produces meaningful score spread, platform-aware ordering,
duplicate deduplication, semantic diversity, and post-rank explanations.
"""

import re
import numpy as np
from sentence_transformers import SentenceTransformer

from backend import embeddings
from backend import trends
from backend.niche_manager import get_niche_profile, get_active_niche
from backend.models import CandidateTag

# ---------------------------------------------------------------------------
# platform profiles  —  how each platform weights tag types & term patterns
# ---------------------------------------------------------------------------

PlatformProfile = dict

PLATFORM_PROFILES: dict[str, PlatformProfile] = {
    "Instagram": {
        "base_hashtag": 1.0,
        "base_keyword": 0.3,
        "boost_patterns": [
            (r"(life|vibes|culture|lover|tok|daily|style|gram)$", 15),
            (r"^(coffee|fit|food|travel|fashion)", 10),
        ],
    },
    "LinkedIn": {
        "base_hashtag": 0.3,
        "base_keyword": 1.0,
        "boost_patterns": [
            (r"(industry|strategy|supply.?chain|leadership|innovation|professional|sector|market|trend)", 15),
            (r"^(thought|expert|insight|analysis|enterprise)", 10),
        ],
    },
    "TikTok": {
        "base_hashtag": 1.0,
        "base_keyword": 0.4,
        "boost_patterns": [
            (r"(tok|hack|challenge|tutorial|routine|aesthetic|viral)$", 15),
            (r"^(coffeetok|beautytok|fittok|gaming)", 10),
        ],
    },
    "X": {
        "base_hashtag": 0.7,
        "base_keyword": 0.7,
        "boost_patterns": [
            (r"(news|breaking|update|trending|hot)$", 10),
        ],
    },
}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_sim_model: SentenceTransformer | None = None


def _get_sim():
    global _sim_model
    if _sim_model is None:
        _sim_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sim_model


def _normalize_tag(tag: str) -> str:
    """Normalise a tag for deduplication (strip spaces, lowercase)."""
    return re.sub(r"\s+", "", tag).lower()


# ---------------------------------------------------------------------------
# 1  semantic relevance  (40% weight)
# ---------------------------------------------------------------------------

def compute_semantic_relevance(tag: str, topic: str, product: str) -> float:
    model = _get_sim()
    query = f"{topic} {product}"
    emb_tag = model.encode([tag], normalize_embeddings=True)
    emb_query = model.encode([query], normalize_embeddings=True)
    sim = float(np.dot(emb_tag, emb_query.T)[0][0])
    return round(max(0.0, min(100.0, sim * 100.0)), 1)


def batch_semantic_relevance(tags: list[str], topic: str, product: str) -> list[float]:
    model = _get_sim()
    query = f"{topic} {product}"
    emb_tags = model.encode(tags, normalize_embeddings=True)
    emb_query = model.encode([query], normalize_embeddings=True)
    sims = np.dot(emb_tags, emb_query.T).flatten()
    return [round(max(0.0, min(100.0, s * 100.0)), 1) for s in sims]


# ---------------------------------------------------------------------------
# 2  platform fit  (15% weight)
# ---------------------------------------------------------------------------

def compute_platform_fit(tag: str, tag_type: str, platform: str) -> float:
    profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["X"])
    base = profile["base_hashtag"] if tag_type == "hashtag" else profile["base_keyword"]
    boost = 0.0
    for pattern, pts in profile.get("boost_patterns", []):
        if re.search(pattern, tag, re.IGNORECASE):
            boost = max(boost, pts)
    return round(max(0.0, min(100.0, (base * 70.0) + boost)), 1)


# ---------------------------------------------------------------------------
# 3  competition  (15% weight — inverse)
# ---------------------------------------------------------------------------

def compute_low_competition(comp_score: float) -> float:
    return round(max(0.0, 100.0 - comp_score), 1)


# ---------------------------------------------------------------------------
# 4  trend / reach  (25% weight)
# ---------------------------------------------------------------------------

def compute_trend_score(reach_volume: float) -> float:
    return round(max(0.0, min(100.0, reach_volume)), 1)


# ---------------------------------------------------------------------------
# 5  confidence / profile quality  (5% weight)
# ---------------------------------------------------------------------------

def compute_profile_confidence(niche_id: str, user_id: str | None = None) -> float:
    profile = get_niche_profile(niche_id, user_id)
    all_terms = []
    for cat in ("industry_terms", "products", "topics", "hashtags", "brands", "audience"):
        all_terms.extend(profile.get(cat, []))
    profile_term_count = len(all_terms)

    corpus_size = embeddings.get_corpus_size(niche_id, user_id)
    score = 50.0
    if profile_term_count >= 20:
        score += 20
    if profile_term_count >= 50:
        score += 10
    if corpus_size >= 20:
        score += 10
    if corpus_size >= 100:
        score += 10
    return round(min(100.0, score), 1)


# ---------------------------------------------------------------------------
# 6  duplicate normalisation
# ---------------------------------------------------------------------------

_DUPLICATE_GROUPS: list[tuple[re.Pattern, callable]] = []


def _build_duplicate_groups():
    if _DUPLICATE_GROUPS:
        return
    space_variants = re.compile(r"^(.+?)\s+(.+)$")
    _DUPLICATE_GROUPS.append((space_variants, lambda m: f"{m.group(1)}{m.group(2)}"))


def normalise_tag(term: str) -> str:
    return _normalize_tag(term)


def deduplicate(candidates: list[dict]) -> list[dict]:
    seen_norm: dict[str, dict] = {}
    for c in candidates:
        norm = normalise_tag(c["tag"])
        if norm in seen_norm:
            existing = seen_norm[norm]
            if c.get("semantic_relevance", 0) > existing.get("semantic_relevance", 0):
                seen_norm[norm] = c
        else:
            seen_norm[norm] = c
    return list(seen_norm.values())


# ---------------------------------------------------------------------------
# 7  diversity penalty  (Maximal Marginal Relevance)
# ---------------------------------------------------------------------------

def apply_diversity(candidates: list[dict], lambda_: float = 0.4, top_k: int = 10) -> list[dict]:
    if len(candidates) <= 1:
        return candidates

    model = _get_sim()
    tags = [c["tag"] for c in candidates]
    emb = model.encode(tags, normalize_embeddings=True)

    selected: list[int] = []
    remaining = list(range(len(candidates)))

    while len(selected) < min(top_k, len(candidates)):
        if not selected:
            best = int(np.argmax([c.get("final_score", 0) for c in candidates]))
            selected.append(best)
            remaining.remove(best)
            continue

        selected_embs = emb[selected]
        scores = np.array([c.get("final_score", 0) for c in candidates])
        for i in remaining:
            sim_to_selected = float(np.max(np.dot(emb[i], selected_embs.T)))
            scores[i] = scores[i] - lambda_ * sim_to_selected * 100.0

        best = int(np.argmax(scores))
        if best in remaining:
            selected.append(best)
            remaining.remove(best)
        else:
            break

    return [candidates[i] for i in selected] + [candidates[i] for i in remaining]


# ---------------------------------------------------------------------------
# 8  explanation generator
# ---------------------------------------------------------------------------

def _metric_label(value: float, high_threshold: float = 70,
                   low_threshold: float = 35) -> str:
    if value >= high_threshold:
        return "strong"
    if value >= low_threshold:
        return "moderate"
    return "low"


def generate_explanation(tag: str, semantic_relevance: float, trend_score: float,
                         competition_score: float, platform_fit: float,
                         rank: int, total: int) -> str:
    rel_label = _metric_label(semantic_relevance)
    trend_label = _metric_label(trend_score)
    comp_label = _metric_label(100 - competition_score)
    plat_label = _metric_label(platform_fit)

    parts = []
    if rel_label != "low":
        parts.append(f"{rel_label} semantic relevance ({semantic_relevance:.0f}/100)")
    if trend_label != "low":
        parts.append(f"{trend_label} trend momentum ({trend_score:.0f}/100)")
    else:
        parts.append(f"limited trend data ({trend_score:.0f}/100)")
    if comp_label == "strong":
        parts.append("low competition — an underused term")
    elif comp_label == "low":
        parts.append(f"high competition ({competition_score:.0f}/100)")
    else:
        parts.append(f"moderate competition ({competition_score:.0f}/100)")
    if plat_label == "strong":
        parts.append(f"excellent platform fit ({platform_fit:.0f}/100)")
    elif plat_label == "moderate":
        parts.append(f"moderate platform fit ({platform_fit:.0f}/100)")

    return f"#{rank} {tag}: {', '.join(parts)}."


# ---------------------------------------------------------------------------
# 9  main ranking entry point
# ---------------------------------------------------------------------------

def rank_candidates(
    candidates: list[dict],
    topic: str,
    product: str,
    platform: str,
    niche_id: str,
    user_id: str | None = None,
) -> list[CandidateTag]:
    """Rank candidates using the multi-signal scoring model.

    Returns a list of CandidateTag objects ordered by final score descending.
    """
    tags = [c["tag"] for c in candidates]
    types = [c.get("type", "hashtag" if len(t.split()) <= 2 else "keyword") for c, t in zip(candidates, tags)]

    # 1  batch semantic relevance
    rel_scores = batch_semantic_relevance(tags, topic, product)

    # 2  trend + competition per candidate
    trend_scores: list[float] = []
    comp_scores: list[float] = []
    for tag in tags:
        td = trends.get_trend_volume(tag)
        trend_scores.append(compute_trend_score(td["volume"]))
        comp = embeddings.compute_competition_score(tag, niche_id, user_id)
        comp_scores.append(comp)

    # 3  platform fit
    fit_scores = [compute_platform_fit(t, ty, platform) for t, ty in zip(tags, types)]

    # 4  profile confidence (same for all — computed once)
    profile_conf = compute_profile_confidence(niche_id, user_id)

    # 5  assemble rows
    enriched: list[dict] = []
    for i in range(len(tags)):
        rel = rel_scores[i]
        tr = trend_scores[i]
        comp = comp_scores[i]
        fit = fit_scores[i]
        low_comp = compute_low_competition(comp)

        final = round(
            rel * 0.40
            + tr * 0.25
            + low_comp * 0.15
            + fit * 0.15
            + profile_conf * 0.05,
            1,
        )

        enriched.append({
            "tag": tags[i],
            "type": types[i],
            "semantic_relevance": rel,
            "trend_score": tr,
            "competition_score": comp,
            "platform_fit": fit,
            "history_confidence": profile_conf,
            "final_score": final,
        })

    # 6  deduplicate
    enriched = deduplicate(enriched)

    # 7  initial rank by final score
    enriched.sort(key=lambda x: x["final_score"], reverse=True)

    # 8  diversity penalty on top
    enriched = apply_diversity(enriched, lambda_=0.4, top_k=10)

    # 9  generate explanations for top
    result: list[CandidateTag] = []
    for i, c in enumerate(enriched[:25]):
        expl = generate_explanation(
            c["tag"], c["semantic_relevance"], c["trend_score"],
            c["competition_score"], c["platform_fit"], i + 1, len(enriched),
        )
        result.append(CandidateTag(
            tag=c["tag"],
            type=c["type"],
            semantic_relevance=c["semantic_relevance"],
            trend_score=c["trend_score"],
            competition_score=c["competition_score"],
            platform_fit=c["platform_fit"],
            history_confidence=c["history_confidence"],
            final_score=c["final_score"],
            explanation=expl,
        ))

    return result


# ---------------------------------------------------------------------------
# 10  gap / blue ocean detection
# ---------------------------------------------------------------------------

def find_gaps(ranked: list[CandidateTag]) -> list[dict]:
    """Detect blue-ocean opportunities from the ranked candidate list."""
    gaps: list[dict] = []
    for c in ranked:
        opportunity = c.semantic_relevance * c.trend_score * (100 - c.competition_score) / 10000.0
        if opportunity > 15.0 and c.competition_score < 40 and c.trend_score > 50:
            gaps.append({
                "tag": c.tag,
                "type": c.type,
                "semantic_relevance": c.semantic_relevance,
                "trend_score": c.trend_score,
                "competition_score": c.competition_score,
                "reason": (
                    f"High relevance ({c.semantic_relevance:.0f}) + strong demand "
                    f"({c.trend_score:.0f}) + low saturation ({c.competition_score:.0f}) "
                    f"= blue ocean opportunity"
                ),
            })
    return gaps
