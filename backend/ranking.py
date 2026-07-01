"""Recommendation ranking engine — Phase 5.

Platform-intelligent, explainable, diversity-aware multi-signal ranking
with score breakdown, quality labels, percentile confidence bands,
and rich bullet-point explanations.
"""

import re

import numpy as np
from sentence_transformers import SentenceTransformer

from backend import embeddings, trends
from backend.niche_manager import get_niche_profile
from backend.models import (
    CandidateTag, GapTag, HighCompetitionTag, HiddenGemTag,
    RejectedCandidateTag, MixSummary, ScoreAnalytics, confidence_band,
)

# ---------------------------------------------------------------------------
def _convert_breakdown(bd: dict) -> dict:
    """Recursively convert numpy types to Python native types."""
    result = {}
    for k, v in bd.items():
        if isinstance(v, dict):
            result[k] = _convert_breakdown(v)
        elif hasattr(v, "item"):
            result[k] = v.item()
        else:
            result[k] = v
    return result


# platform profiles  —  strongly differentiated
# ---------------------------------------------------------------------------

PLATFORM_PROFILES: dict[str, dict] = {
    "Instagram": {
        "base_hashtag": 1.0,
        "base_keyword": 0.05,
        "boost_patterns": [
            (r"(life|vibes|culture|lover|tok|daily|style|gram|aesthetic)$", 30),
            (r"^(coffee|fit|food|travel|fashion|beauty|skincare)", 25),
            (r"(community|discover|explore|engagement|creator)", 22),
            (r"(photography|outfit|makeup|hair|nails|wellness)", 20),
            (r"(ootd|grwm|motd|shelfie|flatlay|inspo)", 28),
        ],
        "category_boosts": {
            "Hashtag": 20, "Audience": 15, "Topic": 10,
            "Industry Term": -20, "Brand": 0, "Keyword": -5,
        },
    },
    "LinkedIn": {
        "base_hashtag": 0.05,
        "base_keyword": 1.0,
        "boost_patterns": [
            (r"(industry|strategy|supply.?chain|leadership|innovation|professional|sector|market|b2b|enterprise)", 30),
            (r"^(thought|expert|insight|analysis|enterprise|framework|whitepaper)", 25),
            (r"(certification|compliance|governance|roi|scalability|infrastructure)", 22),
            (r"(workforce|talent|recruitment|hiring|management|executive)", 20),
            (r"(transformation|digitalization|optimization|automation)", 25),
        ],
        "category_boosts": {
            "Industry Term": 20, "Brand": 12, "Topic": 10,
            "Hashtag": -20, "Audience": 5, "Keyword": 8,
        },
    },
    "TikTok": {
        "base_hashtag": 1.0,
        "base_keyword": 0.05,
        "boost_patterns": [
            (r"(tok|hack|challenge|tutorial|routine|aesthetic|viral)$", 30),
            (r"^(coffeetok|beautytok|fittok|gaming|foodtok|planttok|booktok)", 28),
            (r"(trending|viral|discover|explore|pov|fyp|foryou)", 22),
            (r"(makeup|recipe|diy|transformation|dayinmylife|relatable)", 20),
            (r"(grwm|getready|nightroutine|morningroutine)", 25),
        ],
        "category_boosts": {
            "Hashtag": 20, "Topic": 12, "Audience": 10,
            "Industry Term": -20, "Brand": -5, "Keyword": -10,
        },
    },
    "X": {
        "base_hashtag": 0.3,
        "base_keyword": 0.8,
        "boost_patterns": [
            (r"(news|breaking|update|trending|hot|just.?in|live)$", 25),
            (r"^(report|analysis|opinion|watch|exclusive|alert)", 20),
            (r"(discussion|debate|thread|community|take)", 18),
            (r"(controversy|unpopular|opinion|hot.?take|debate)", 22),
        ],
        "category_boosts": {
            "Topic": 15, "Brand": 10, "Hashtag": 5,
            "Industry Term": 8, "Audience": 0, "Keyword": 5,
        },
    },
}

# ---------------------------------------------------------------------------
# weights  —  platform is now the strongest signal
# ---------------------------------------------------------------------------

W_REL = 0.30
W_TREND = 0.12
W_LOW_COMP = 0.13
W_PLATFORM = 0.40
W_CONF = 0.05

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_sim_model: SentenceTransformer | None = None


def _get_sim():
    global _sim_model
    if _sim_model is None:
        _sim_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sim_model


# ---------------------------------------------------------------------------
# 1  semantic relevance
# ---------------------------------------------------------------------------

def compute_semantic_relevance(tag: str, topic: str, product: str) -> float:
    model = _get_sim()
    emb_tag = model.encode([tag], normalize_embeddings=True)
    emb_query = model.encode([f"{topic} {product}"], normalize_embeddings=True)
    return round(max(0.0, min(100.0, float(np.dot(emb_tag, emb_query.T)[0][0]) * 100.0)), 1)


def batch_semantic_relevance(tags: list[str], topic: str, product: str) -> list[float]:
    model = _get_sim()
    emb_tags = model.encode(tags, normalize_embeddings=True)
    emb_query = model.encode([f"{topic} {product}"], normalize_embeddings=True)
    sims = np.dot(emb_tags, emb_query.T).flatten()
    return [round(max(0.0, min(100.0, s * 100.0)), 1) for s in sims]


# ---------------------------------------------------------------------------
# 2  platform fit  (strongest signal)
# ---------------------------------------------------------------------------

EXPECTED_CATEGORIES = {"Product", "Hashtag", "Industry Term", "Audience", "Topic", "Brand", "Keyword"}


def compute_platform_fit(tag: str, tag_type: str, platform: str, category: str = "") -> float:
    profile = PLATFORM_PROFILES.get(platform, PLATFORM_PROFILES["X"])
    base = profile["base_hashtag"] if tag_type == "hashtag" else profile["base_keyword"]

    category_boost = profile.get("category_boosts", {}).get(category, 0) if category else 0

    boost = 0.0
    for pattern, pts in profile.get("boost_patterns", []):
        if re.search(pattern, tag, re.IGNORECASE):
            boost = max(boost, pts)

    return round(max(0.0, min(100.0, (base * 55.0) + boost + category_boost)), 1)


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
        score += 15
    if profile_term_count >= 50:
        score += 10
    if corpus_size >= 20:
        score += 10
    if corpus_size >= 100:
        score += 15
    return round(min(100.0, score), 1)


# ---------------------------------------------------------------------------
# 6  duplicate normalisation  (Phase 5: stronger dedup)
# ---------------------------------------------------------------------------

def _normalize_tag(tag: str) -> str:
    t = re.sub(r"\s+", "", tag).lower()
    t = re.sub(r"[^a-z0-9]", "", t)
    if t.endswith("s") and len(t) > 4:
        t = t[:-1]
    return t


def normalise_tag(term: str) -> str:
    return _normalize_tag(term)


def _is_near_duplicate(a: str, b: str) -> bool:
    """Check if two tags are near-duplicates (e.g. 'smart home' vs 'smart homes')."""
    na = _normalize_tag(a)
    nb = _normalize_tag(b)
    if na == nb:
        return True
    if len(na) > 3 and len(nb) > 3:
        if na.startswith(nb) or nb.startswith(na):
            return True
        if abs(len(na) - len(nb)) <= 2:
            shorter = min(na, nb, key=len)
            longer = max(na, nb, key=len)
            if shorter in longer:
                return True
    return False


def deduplicate(candidates: list[dict]) -> list[dict]:
    result: list[dict] = []
    for c in candidates:
        norm = _normalize_tag(c["tag"])
        is_dup = False
        for existing in result:
            if _is_near_duplicate(c["tag"], existing["tag"]):
                if c.get("semantic_relevance", 0) > existing.get("semantic_relevance", 0):
                    result.remove(existing)
                    result.append(c)
                is_dup = True
                break
        if not is_dup:
            result.append(c)
    return result


# ---------------------------------------------------------------------------
# 7  diversity penalty  (MMR — stronger penalty in Phase 5)
# ---------------------------------------------------------------------------

def apply_diversity(candidates: list[dict], lambda_: float = 0.45, top_k: int = 15) -> list[dict]:
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
# 8  quality indicators
# ---------------------------------------------------------------------------

def _quality_labels(c: dict, platform: str) -> list[str]:
    labels = []
    rel = c["semantic_relevance"]
    tr = c["trend_score"]
    comp = c["competition_score"]
    fit = c["platform_fit"]
    final = c["final_score"]

    if rel >= 80:
        labels.append("Excellent Match")
    elif rel >= 60:
        labels.append("Strong Match")

    if tr >= 70:
        labels.append("Trending")
    elif tr >= 50:
        labels.append("Rising")

    if comp <= 25:
        labels.append("Low Competition")
    elif comp <= 40:
        labels.append("Moderate Competition")

    if fit >= 80:
        labels.append("Platform Favorite")
    elif fit >= 60:
        labels.append("Platform Friendly")

    if c.get("is_blue_ocean"):
        labels.append("Blue Ocean")
    if c.get("is_hidden_gem"):
        labels.append("Hidden Gem")

    if c.get("category") == "Industry Term" and platform == "LinkedIn":
        labels.append("Professional Term")
    if c.get("category") == "Hashtag" and platform in ("Instagram", "TikTok"):
        labels.append("Creator Friendly")

    if c["opportunity_score"] > 20 and comp < 35:
        labels.append("Emerging")

    return labels[:4]


# ---------------------------------------------------------------------------
# 9  explanation generator  (rich bullet-point)
# ---------------------------------------------------------------------------

_SEMANTIC_DESC = {
    80: "Excellent semantic match with your niche profile",
    60: "Good semantic alignment with the query",
    40: "Moderate semantic connection to the topic",
    0: "Limited semantic relevance",
}

_TREND_DESC = {
    70: "Frequently searched within your selected platform",
    50: "Growing interest detected in recent data",
    30: "Moderate trending signals present",
    0: "Lower trending activity currently",
}

_COMP_DESC = {
    75: "Competition is considerably lower than similar alternatives",
    50: "Competition levels are manageable",
    30: "Moderate competition from existing content",
    0: "High competition — very saturated space",
}

_PLATFORM_DESC = {
    "LinkedIn": {
        80: "Strong platform compatibility because LinkedIn rewards professional and industry-focused terminology",
        60: "Good alignment with LinkedIn's professional content ecosystem",
        40: "Moderate fit for LinkedIn's content format",
        0: "Suboptimal — this tag type underperforms on LinkedIn",
    },
    "Instagram": {
        80: "Ideal for Instagram's visual discovery and hashtag-driven ecosystem",
        60: "Performs well within Instagram's content discovery patterns",
        40: "Average performance on Instagram's platform",
        0: "Not optimized for Instagram's hashtag-heavy model",
    },
    "TikTok": {
        80: "Naturally aligned with TikTok's trend-driven, creator-friendly environment",
        60: "Relevant within TikTok's content discovery algorithm",
        40: "Moderate TikTok compatibility",
        0: "Less suited to TikTok's viral content patterns",
    },
    "X": {
        80: "Well-suited for X's real-time conversation and news-oriented format",
        60: "Relevant within X's discussion and trending ecosystem",
        40: "Average fit for X's platform dynamics",
        0: "Not ideal for X's concise, timely content model",
    },
}


def _band_desc(band: str) -> str:
    return {
        "Elite": "Elite — top percentile ranking confidence",
        "Excellent": "Excellent — very strong ranking confidence",
        "Very Strong": "Very Strong — high ranking confidence",
        "Strong": "Strong — solid ranking confidence",
        "Moderate": "Moderate — adequate ranking confidence",
        "Weak": "Weak — lower ranking confidence",
    }.get(band, "Standard ranking confidence")


def generate_explanation(
    tag: str, semantic_relevance: float, trend_score: float,
    competition_score: float, platform_fit: float,
    rank: int, total: int, platform: str, category: str,
    band: str, opp_score: float, quality_labels: list[str],
) -> str:
    parts = []

    def _desc(mapping: dict, value: float) -> str:
        for threshold, desc in sorted(mapping.items(), reverse=True):
            if value >= threshold:
                return desc
        return list(mapping.values())[-1]

    parts.append(f"Recommendation #{rank}: {tag}")

    rel_desc = _desc(_SEMANTIC_DESC, semantic_relevance)
    parts.append(f"• {rel_desc} ({semantic_relevance:.0f}/100).")

    trend_desc = _desc(_TREND_DESC, trend_score)
    parts.append(f"• {trend_desc} ({trend_score:.0f}/100).")

    comp_desc = _desc(_COMP_DESC, competition_score)
    comp_inv = _desc(_COMP_DESC, 100 - competition_score)
    if competition_score < 40:
        parts.append(f"• {comp_desc} ({competition_score:.0f}/100).")
    else:
        parts.append(f"• {comp_inv} ({competition_score:.0f}/100).")

    plat_map = _PLATFORM_DESC.get(platform, _PLATFORM_DESC["X"])
    plat_desc = _desc(plat_map, platform_fit)
    parts.append(f"• {plat_desc} ({platform_fit:.0f}/100).")

    if category:
        parts.append(f"• Categorized as {category} — aligns with the '{category}' segment of your niche profile.")

    band_label = _band_desc(band)
    parts.append(f"• Confidence: {band} — {band_label}.")

    if quality_labels:
        parts.append(f"• Indicators: {', '.join(quality_labels)}.")

    if opp_score > 15:
        parts.append(f"• Opportunity score {opp_score:.0f} — qualifies as a blue ocean opportunity with first-mover potential.")

    if rank <= 3:
        parts.append(f"• Recommended alongside complementary terms for broader content reach.")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 10  main ranking entry point
# ---------------------------------------------------------------------------

TOP_K = 15
DISPLAY_K = 10


def rank_candidates(
    candidates: list[dict],
    topic: str,
    product: str,
    platform: str,
    niche_id: str,
    user_id: str | None = None,
) -> tuple[list[CandidateTag], list[GapTag], list[HighCompetitionTag], list[HiddenGemTag], list[RejectedCandidateTag], MixSummary, ScoreAnalytics]:
    tags = [c["tag"] for c in candidates]
    types = [c.get("type", "hashtag" if len(t.split()) <= 2 else "keyword") for c, t in zip(candidates, tags)]
    categories = [c.get("category", "Keyword") for c in candidates]

    # 1  batch semantic relevance
    rel_scores = batch_semantic_relevance(tags, topic, product)

    # 2  trend + competition
    trend_scores: list[float] = []
    comp_scores: list[float] = []
    for tag in tags:
        td = trends.get_trend_volume(tag)
        trend_scores.append(compute_trend_score(td["volume"]))
        comp = embeddings.compute_competition_score(tag, niche_id, user_id)
        comp_scores.append(comp)

    # 3  platform fit
    fit_scores = [compute_platform_fit(t, ty, platform, cat) for t, ty, cat in zip(tags, types, categories)]

    profile_conf = compute_profile_confidence(niche_id, user_id)

    # 5  assemble enriched candidates with score breakdown
    enriched: list[dict] = []
    for i in range(len(tags)):
        rel = rel_scores[i]
        tr = trend_scores[i]
        comp = comp_scores[i]
        fit = fit_scores[i]
        low_comp = compute_low_competition(comp)
        cat = categories[i] if categories[i] in EXPECTED_CATEGORIES else "Keyword"
        opp = round(rel * tr * (100 - comp) / 10000.0, 1)

        sem_contrib = round(rel * W_REL, 1)
        trend_contrib = round(tr * W_TREND, 1)
        comp_contrib = round(low_comp * W_LOW_COMP, 1)
        plat_contrib = round(fit * W_PLATFORM, 1)
        conf_contrib = round(profile_conf * W_CONF, 1)

        final = round(sem_contrib + trend_contrib + comp_contrib + plat_contrib + conf_contrib, 1)

        score_breakdown = {
            "semantic_contribution": sem_contrib,
            "trend_contribution": trend_contrib,
            "competition_contribution": comp_contrib,
            "platform_contribution": plat_contrib,
            "confidence_contribution": conf_contrib,
            "weights": {
                "semantic": W_REL,
                "trend": W_TREND,
                "low_competition": W_LOW_COMP,
                "platform_fit": W_PLATFORM,
                "confidence": W_CONF,
            },
        }

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
            "score_breakdown": score_breakdown,
        })

    # 6  deduplicate (stronger)
    enriched = deduplicate(enriched)

    # 7  initial rank
    enriched.sort(key=lambda x: x["final_score"], reverse=True)

    # 8  diversity penalty
    enriched = apply_diversity(enriched, lambda_=0.45, top_k=TOP_K)

    total_evaluated = len(enriched)

    # 9  classify, build quality labels, generate explanations
    blue_ocean_list: list[CandidateTag] = []
    high_comp_list: list[HighCompetitionTag] = []
    hidden_gems_list: list[HiddenGemTag] = []
    rejected_list: list[RejectedCandidateTag] = []

    result: list[CandidateTag] = []
    mix_counts: dict[str, int] = {
        "hashtags": 0, "products": 0, "industry_terms": 0,
        "audience": 0, "topics": 0, "brands": 0, "keywords": 0,
    }

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

        c["is_blue_ocean"] = is_bo
        c["is_hidden_gem"] = is_hg
        c["is_high_competition"] = is_hc

        band = confidence_band(final)
        qlabels = _quality_labels(c, platform)
        c["quality_labels"] = qlabels

        expl = generate_explanation(
            tag_name, rel, tr, comp, fit,
            i + 1, total_evaluated, platform, cat, band, opp, qlabels,
        )

        ct = CandidateTag(
            tag=tag_name,
            type=tag_type,
            category=cat,
            semantic_relevance=float(rel),
            trend_score=float(tr),
            competition_score=float(comp),
            platform_fit=float(fit),
            history_confidence=float(profile_conf),
            final_score=float(final),
            explanation=expl,
            confidence_band=band,
            opportunity_score=float(opp) if opp is not None else None,
            is_blue_ocean=is_bo,
            is_hidden_gem=is_hg,
            is_high_competition=is_hc,
            score_breakdown=_convert_breakdown(c.get("score_breakdown", {})),
            quality_labels=qlabels,
        )

        # mix
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
                high_comp_list.append(HighCompetitionTag(tag=tag_name, type=tag_type, competition_score=comp))
            elif not is_bo and not is_hg and (comp > 60 or rel < 30):
                rejected_list.append(RejectedCandidateTag(tag=tag_name, type=tag_type, reason=_rejection_reason(rel, tr, comp, fit)))

    ranked_tags = result[:DISPLAY_K]

    # Blue ocean
    all_bo = [ct for ct in result if ct.is_blue_ocean]
    all_bo.sort(key=lambda x: x.opportunity_score, reverse=True)
    gap_tags = [
        GapTag(
            tag=bo.tag, type=bo.type,
            semantic_relevance=bo.semantic_relevance,
            trend_score=bo.trend_score,
            competition_score=bo.competition_score,
            opportunity_score=bo.opportunity_score,
            reason=_blue_ocean_reason(bo),
        )
        for bo in all_bo[:5]
    ]

    # High competition
    seen_hc: set[str] = set()
    high_competition_tags = [
        HighCompetitionTag(tag=ct.tag, type=ct.type, competition_score=ct.competition_score)
        for ct in result if ct.is_high_competition and ct.tag not in seen_hc and not seen_hc.add(ct.tag)
    ]
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
            reason=_hidden_gem_reason(hg),
        )
        for hg in all_hg[:5]
    ]

    # Rejected (sample)
    rejection_list = rejected_list[:8]

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


# ---------------------------------------------------------------------------
# helpers for reasons
# ---------------------------------------------------------------------------

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


def _blue_ocean_reason(bo: CandidateTag) -> str:
    parts = []
    if bo.semantic_relevance > 70:
        parts.append("High relevance")
    else:
        parts.append("Good relevance")
    if bo.trend_score > 65:
        parts.append("strong demand")
    else:
        parts.append("moderate demand")
    if bo.competition_score < 25:
        parts.append("very low saturation")
    else:
        parts.append("low saturation")
    return f"{', '.join(parts)} ({bo.semantic_relevance:.0f}/{bo.trend_score:.0f}/{bo.competition_score:.0f}) = blue ocean opportunity with first-mover potential"


def _hidden_gem_reason(hg: CandidateTag) -> str:
    return (
        f"High relevance ({hg.semantic_relevance:.0f}) + "
        f"low competition ({hg.competition_score:.0f}) + "
        f"moderate trend ({hg.trend_score:.0f}) — "
        f"long-tail opportunity with high future potential"
    )



