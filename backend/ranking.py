"""Recommendation ranking engine.

Multi-signal ranking with platform-aware ordering, duplicate deduplication,
semantic diversity, category assignment, blue-ocean / high-competition /
hidden-gem detection, rejected candidate tracking, and rich explanations.
"""

import re

import numpy as np
from sentence_transformers import SentenceTransformer

from backend import embeddings, trends
from backend.niche_manager import get_niche_profile, get_active_niche
from backend.models import (
    CandidateTag,
    GapTag,
    HighCompetitionTag,
    HiddenGemTag,
    RejectedCandidateTag,
    MixSummary,
    ScoreAnalytics,
    confidence_band,
)

# ---------------------------------------------------------------------------
# platform profiles
# ---------------------------------------------------------------------------

PLATFORM_PROFILES: dict[str, dict] = {
    "Instagram": {
        "base_hashtag": 1.0,
        "base_keyword": 0.25,
        "boost_patterns": [
            (r"(life|vibes|culture|lover|tok|daily|style|gram)$", 20),
            (r"^(coffee|fit|food|travel|fashion|beauty)", 15),
            (r"(community|discover|explore|trending)", 12),
        ],
    },
    "LinkedIn": {
        "base_hashtag": 0.25,
        "base_keyword": 1.0,
        "boost_patterns": [
            (r"(industry|strategy|supply.?chain|leadership|innovation|professional|sector|market|trend|b2b)", 20),
            (r"^(thought|expert|insight|analysis|enterprise|enterprise)", 15),
            (r"(certification|compliance|governance|framework)", 12),
        ],
    },
    "TikTok": {
        "base_hashtag": 1.0,
        "base_keyword": 0.35,
        "boost_patterns": [
            (r"(tok|hack|challenge|tutorial|routine|aesthetic|viral)$", 20),
            (r"^(coffeetok|beautytok|fittok|gaming|foodtok)", 15),
            (r"(trending|viral|discover|explore)", 12),
        ],
    },
    "X": {
        "base_hashtag": 0.6,
        "base_keyword": 0.7,
        "boost_patterns": [
            (r"(news|breaking|update|trending|hot|just.?in)$", 15),
            (r"^(report|analysis|opinion|watch)", 10),
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
    return re.sub(r"\s+", "", tag).lower()


# ---------------------------------------------------------------------------
# 1  semantic relevance
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
# 2  platform fit  (higher weight, more aggressive)
# ---------------------------------------------------------------------------

def compute_platform_fit(tag: str, tag_type: str, platform: str, category: str = "") -> float:
    profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["X"])
    base = profile["base_hashtag"] if tag_type == "hashtag" else profile["base_keyword"]

    category_boost = 0.0
    if platform == "LinkedIn":
        if category in ("Industry Term", "Brand", "Topic"):
            category_boost = 10
        elif category == "Hashtag":
            category_boost = -10
    elif platform == "Instagram":
        if category in ("Hashtag", "Audience", "Topic"):
            category_boost = 10
        elif category == "Industry Term":
            category_boost = -10
    elif platform == "TikTok":
        if category in ("Hashtag", "Topic"):
            category_boost = 10
        elif category == "Industry Term":
            category_boost = -10
    elif platform == "X":
        if category in ("Topic", "Brand"):
            category_boost = 8

    boost = 0.0
    for pattern, pts in profile.get("boost_patterns", []):
        if re.search(pattern, tag, re.IGNORECASE):
            boost = max(boost, pts)

    return round(max(0.0, min(100.0, (base * 60.0) + boost + category_boost)), 1)


# ---------------------------------------------------------------------------
# 3  competition
# ---------------------------------------------------------------------------

def compute_low_competition(comp_score: float) -> float:
    return round(max(0.0, 100.0 - comp_score), 1)


# ---------------------------------------------------------------------------
# 4  trend
# ---------------------------------------------------------------------------

def compute_trend_score(reach_volume: float) -> float:
    return round(max(0.0, min(100.0, reach_volume)), 1)


# ---------------------------------------------------------------------------
# 5  profile confidence
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
# 7  diversity penalty  (MMR)
# ---------------------------------------------------------------------------

def apply_diversity(candidates: list[dict], lambda_: float = 0.35, top_k: int = 15) -> list[dict]:
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

        best_idx = int(np.argmax(scores))
        if best_idx in remaining:
            selected.append(best_idx)
            remaining.remove(best_idx)
        else:
            break

    return [candidates[i] for i in selected] + [candidates[i] for i in remaining]


# ---------------------------------------------------------------------------
# 8  explanation generator  (rich natural language)
# ---------------------------------------------------------------------------

def _metric_label(value: float, high: float = 70, low: float = 35) -> str:
    if value >= high:
        return "strong"
    if value >= low:
        return "moderate"
    return "low"


_RELEVANCE_PREFIX = {
    "strong": "Excellent semantic match to the query",
    "moderate": "Good semantic relevance to the query",
    "low": "Limited semantic connection to the query",
}

_TREND_PREFIX = {
    "strong": "Strong momentum and growing interest",
    "moderate": "Moderate trending signals detected",
    "low": "Low trending activity currently",
}

_COMPETITION_PREFIX = {
    "strong": "Very low competition — an underused term with first-mover potential",
    "moderate": "Moderate competition levels",
    "low": "High competition — very saturated space with many creators",
}

_PLATFORM_PREFIX = {
    "strong": "Highly favored for this platform",
    "moderate": "Adequate fit for this platform",
    "low": "Suboptimal for this platform's content style",
}


def generate_explanation(
    tag: str, semantic_relevance: float, trend_score: float,
    competition_score: float, platform_fit: float,
    rank: int, total: int,
) -> str:
    rel = _metric_label(semantic_relevance)
    tr = _metric_label(trend_score)
    comp_label = _metric_label(100 - competition_score)
    plat = _metric_label(platform_fit)

    parts = []
    parts.append(f"#{rank} {tag}.")

    parts.append(f"{_RELEVANCE_PREFIX[rel]} ({semantic_relevance:.0f}/100).")
    parts.append(f"{_TREND_PREFIX[tr]} ({trend_score:.0f}/100).")
    parts.append(f"{_COMPETITION_PREFIX[comp_label]} ({competition_score:.0f}/100).")
    parts.append(f"{_PLATFORM_PREFIX[plat]} ({platform_fit:.0f}/100).")

    if rank == 1:
        parts.append("Top recommendation — highest overall score across all signals.")
    elif rank <= 3:
        parts.append("Top-three pick — strong across relevance, trend, and platform fit.")
    elif rank <= 5:
        parts.append("Strong contender — good balance of signals with room for growth.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# 9  category detection from profile
# ---------------------------------------------------------------------------

def _compute_opportunity_score(rel: float, trend: float, comp: float) -> float:
    return round(rel * trend * (100 - comp) / 10000.0, 1)


# ---------------------------------------------------------------------------
# 10  main ranking entry point
# ---------------------------------------------------------------------------

TOP_K = 15
DISPLAY_K = 10

EXPECTED_CATEGORIES = {"Product", "Hashtag", "Industry Term", "Audience", "Topic", "Brand", "Keyword"}


def rank_candidates(
    candidates: list[dict],
    topic: str,
    product: str,
    platform: str,
    niche_id: str,
    user_id: str | None = None,
) -> tuple[list[CandidateTag], list[GapTag], list[HighCompetitionTag], list[HiddenGemTag], list[RejectedCandidateTag], MixSummary, ScoreAnalytics]:
    """Rank candidates using the multi-signal scoring model.

    Returns (ranked_tags, gap_tags, high_competition_tags, hidden_gems,
             rejected_candidates, mix_summary, analytics).
    """
    tags = [c["tag"] for c in candidates]
    types = [c.get("type", "hashtag" if len(t.split()) <= 2 else "keyword") for c, t in zip(candidates, tags)]
    categories = [c.get("category", "Keyword") for c in candidates]

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
    fit_scores = [compute_platform_fit(t, ty, platform, cat) for t, ty, cat in zip(tags, types, categories)]

    # Updated weights — more platform influence
    W_REL = 0.35
    W_TREND = 0.15
    W_LOW_COMP = 0.15
    W_PLATFORM = 0.30
    W_CONF = 0.05

    profile_conf = compute_profile_confidence(niche_id, user_id)

    enriched: list[dict] = []
    for i in range(len(tags)):
        rel = rel_scores[i]
        tr = trend_scores[i]
        comp = comp_scores[i]
        fit = fit_scores[i]
        low_comp = compute_low_competition(comp)
        opp = _compute_opportunity_score(rel, tr, comp)
        cat = categories[i] if categories[i] in EXPECTED_CATEGORIES else "Keyword"

        final = round(
            rel * W_REL
            + tr * W_TREND
            + low_comp * W_LOW_COMP
            + fit * W_PLATFORM
            + profile_conf * W_CONF,
            1,
        )

        enriched.append({
            "tag": tags[i],
            "type": types[i],
            "category": cat,
            "semantic_relevance": rel,
            "trend_score": tr,
            "competition_score": comp,
            "platform_fit": fit,
            "history_confidence": profile_conf,
            "final_score": final,
            "opportunity_score": opp,
        })

    # 6  deduplicate
    enriched = deduplicate(enriched)

    # 7  initial rank
    enriched.sort(key=lambda x: x["final_score"], reverse=True)

    # 8  diversity penalty on top
    enriched = apply_diversity(enriched, lambda_=0.35, top_k=TOP_K)

    total_evaluated = len(enriched)

    # 9  classify each candidate
    blue_ocean: list[CandidateTag] = []
    high_comp: list[HighCompetitionTag] = []
    hidden_gems: list[HiddenGemTag] = []
    rejected: list[RejectedCandidateTag] = []

    result: list[CandidateTag] = []
    mix_counts: dict[str, int] = {"hashtags": 0, "products": 0, "industry_terms": 0, "audience": 0, "topics": 0, "brands": 0, "keywords": 0}

    for i, c in enumerate(enriched):
        rel = c["semantic_relevance"]
        tr = c["trend_score"]
        comp = c["competition_score"]
        fit = c["platform_fit"]
        opp = c["opportunity_score"]
        final = c["final_score"]
        cat = c["category"]
        tag_type = c["type"]
        tag_name = c["tag"]

        is_bo = opp > 12.0 and comp < 45 and tr > 45
        is_hg = rel > 55 and comp < 35 and tr < 50 and not is_bo
        is_hc = comp > 75

        band = confidence_band(final)

        expl = generate_explanation(tag_name, rel, tr, comp, fit, i + 1, total_evaluated)

        ct = CandidateTag(
            tag=tag_name,
            type=tag_type,
            category=cat,
            semantic_relevance=rel,
            trend_score=tr,
            competition_score=comp,
            platform_fit=fit,
            history_confidence=profile_conf,
            final_score=final,
            explanation=expl,
            confidence_band=band,
            opportunity_score=opp,
            is_blue_ocean=is_bo,
            is_hidden_gem=is_hg,
            is_high_competition=is_hc,
        )

        # Track mix
        if tag_type == "hashtag":
            mix_counts["hashtags"] += 1
        elif cat == "Product":
            mix_counts["products"] += 1
        elif cat == "Industry Term":
            mix_counts["industry_terms"] += 1
        elif cat == "Audience":
            mix_counts["audience"] += 1
        elif cat == "Topic":
            mix_counts["topics"] += 1
        elif cat == "Brand":
            mix_counts["brands"] += 1
        else:
            mix_counts["keywords"] += 1

        result.append(ct)

        if i >= TOP_K:
            if is_hc:
                high_comp.append(HighCompetitionTag(tag=tag_name, type=tag_type, competition_score=comp))
            elif not is_bo and not is_hg and (comp > 60 or rel < 30):
                rejected.append(RejectedCandidateTag(tag=tag_name, type=tag_type, reason=_rejection_reason(rel, tr, comp, fit)))

    # Select top DISPLAY_K for ranked_tags
    ranked_tags = result[:DISPLAY_K]

    # Blue ocean: collect from top results + extra candidates
    all_bo = [ct for ct in result if ct.is_blue_ocean]
    all_bo.sort(key=lambda x: x.opportunity_score, reverse=True)
    gap_tags = [
        GapTag(
            tag=bo.tag,
            type=bo.type,
            semantic_relevance=bo.semantic_relevance,
            trend_score=bo.trend_score,
            competition_score=bo.competition_score,
            opportunity_score=bo.opportunity_score,
            reason=(
                f"High relevance ({bo.semantic_relevance:.0f}) + "
                f"{'strong demand' if bo.trend_score > 60 else 'moderate demand'} "
                f"({bo.trend_score:.0f}) + "
                f"{'very low' if bo.competition_score < 25 else 'low'} saturation "
                f"({bo.competition_score:.0f}) = blue ocean opportunity"
            ),
        )
        for bo in all_bo[:5]
    ]

    # High competition tags: from all evaluated
    high_competition_tags = []
    seen_hc = set()
    for ct in result:
        if ct.is_high_competition and ct.tag not in seen_hc:
            high_competition_tags.append(HighCompetitionTag(
                tag=ct.tag, type=ct.type, competition_score=ct.competition_score,
            ))
            seen_hc.add(ct.tag)
    high_competition_tags.sort(key=lambda x: x.competition_score, reverse=True)

    # Hidden gems
    all_hg = [ct for ct in result if ct.is_hidden_gem]
    all_hg.sort(key=lambda x: x.semantic_relevance, reverse=True)
    hidden_gem_list = [
        HiddenGemTag(
            tag=hg.tag, type=hg.type,
            semantic_relevance=hg.semantic_relevance,
            competition_score=hg.competition_score,
            trend_score=hg.trend_score,
            reason=(
                f"High relevance ({hg.semantic_relevance:.0f}) + "
                f"low competition ({hg.competition_score:.0f}) + "
                f"moderate trend ({hg.trend_score:.0f}) — long-tail opportunity"
            ),
        )
        for hg in all_hg[:5]
    ]

    # Rejected
    rejection_list = rejected[:8]

    # Mix summary
    mix_summary = MixSummary(**mix_counts)

    # Analytics
    if ranked_tags:
        avg_rel = sum(t.semantic_relevance for t in ranked_tags) / len(ranked_tags)
        avg_tr = sum(t.trend_score for t in ranked_tags) / len(ranked_tags)
        avg_comp = sum(t.competition_score for t in ranked_tags) / len(ranked_tags)
        avg_plat = sum(t.platform_fit for t in ranked_tags) / len(ranked_tags)
        avg_final = sum(t.final_score for t in ranked_tags) / len(ranked_tags)
    else:
        avg_rel = avg_tr = avg_comp = avg_plat = avg_final = 0.0

    unique_cats = len(set(t.category for t in ranked_tags if t.category))

    analytics = ScoreAnalytics(
        avg_relevance=round(avg_rel, 1),
        avg_trend=round(avg_tr, 1),
        avg_competition=round(avg_comp, 1),
        avg_platform_fit=round(avg_plat, 1),
        avg_final_score=round(avg_final, 1),
        diversity=round(len(ranked_tags) / max(total_evaluated, 1) * 100, 1) if total_evaluated else 0.0,
        unique_categories=unique_cats,
        blue_ocean_count=len(gap_tags),
        high_competition_count=len(high_competition_tags),
        hidden_gem_count=len(hidden_gem_list),
        total_candidates_evaluated=total_evaluated,
    )

    return ranked_tags, gap_tags, high_competition_tags, hidden_gem_list, rejection_list, mix_summary, analytics


def _rejection_reason(rel: float, trend: float, comp: float, plat: float) -> str:
    reasons = []
    if comp > 75:
        reasons.append("Very high competition")
    if rel < 30:
        reasons.append("Low semantic relevance")
    if plat < 25:
        reasons.append("Weak platform fit")
    if trend < 20:
        reasons.append("Insufficient trend data")
    if not reasons:
        reasons.append("Outranked by stronger candidates")
    return ". ".join(reasons) + "."
