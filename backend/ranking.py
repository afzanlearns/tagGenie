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
            (r"(opening|haul|unboxing|collection|display|shelfie)", 18),
            (r"(review|demo|tutorial|howto|guide)", 16),
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
            (r"(market|trends|analysis|investing|valuation|economy)", 18),
            (r"(collectible|investment|collector|limited|edition)", 16),
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
            (r"(opening|haul|unboxing|collection|reveal)", 18),
            (r"(review|demo|tutorial|howto|guide)", 16),
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
    "Pinterest": {
        "base_hashtag": 0.8,
        "base_keyword": 0.6,
        "boost_patterns": [
            (r"(inspiration|ideas|diy|tutorial|guide|howto|step.?by.?step)$", 30),
            (r"^(decor|recipe|craft|style|design|organize|plan)", 25),
            (r"(aesthetic|minimalist|boho|modern|rustic|vintage)", 22),
            (r"(collection|moodboard|vision.?board|wishlist|favorite)", 20),
            (r"(home|garden|wedding|party|seasonal|holiday)", 18),
        ],
        "category_boosts": {
            "Hashtag": 15, "Topic": 12, "Audience": 8, "Keyword": 5,
            "Industry Term": -10, "Brand": 5,
        },
    },
}

# ---------------------------------------------------------------------------
# weights  —  product context is now the strongest signal
# ---------------------------------------------------------------------------

W_PRODUCT = 0.25
W_REL = 0.12
W_TREND = 0.08
W_LOW_COMP = 0.18
W_PLATFORM = 0.30
W_CONF = 0.07

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
# 1b  product relevance  —  match tag against product alone
# ---------------------------------------------------------------------------

def compute_product_relevance(tag: str, product: str) -> float:
    model = _get_sim()
    emb_tag = model.encode([tag], normalize_embeddings=True)
    emb_prod = model.encode([product], normalize_embeddings=True)
    return round(max(0.0, min(100.0, float(np.dot(emb_tag, emb_prod.T)[0][0]) * 100.0)), 1)


def batch_product_relevance(tags: list[str], product: str) -> list[float]:
    model = _get_sim()
    emb_tags = model.encode(tags, normalize_embeddings=True)
    emb_prod = model.encode([product], normalize_embeddings=True)
    sims = np.dot(emb_tags, emb_prod.T).flatten()
    return [round(max(0.0, min(100.0, s * 100.0)), 1) for s in sims]


# ---------------------------------------------------------------------------
# 2  platform fit
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
# 6a  global brand blacklist  (for blue ocean)
# ---------------------------------------------------------------------------

GLOBAL_BRANDS: set[str] = {
    "tesla", "apple", "google", "amazon", "nike", "microsoft", "meta",
    "netflix", "spotify", "youtube", "instagram", "facebook", "twitter",
    "linkedin", "tiktok", "snapchat", "pinterest", "uber", "airbnb",
    "disney", "coca", "pepsi", "mcdonald", "starbucks", "walmart",
    "target", "costco", "samsung", "sony", "panasonic", "lg", "intel",
    "amd", "nvidia", "adobe", "salesforce", "oracle", "ibm", "cisco",
    "dell", "hp", "canon", "nike", "adidas", "puma", "gucci", "prada",
    "chanel", "louisvuitton", "zara", "hm", "ikea", "nintendo", "playstation",
    "xbox", "reddit", "discord", "zoom", "slack", "notion", "figma",
    "stripe", "paypal", "shopify", "wordpress", "github", "gitlab",
}

LOCAL_BRAND_WORDS: set[str] = {
    "tesla", "apple", "google", "amazon", "nike", "microsoft", "meta",
    "netflix", "spotify", "youtube", "uber", "disney", "samsung",
    "nvidia", "adobe", "salesforce", "oracle", "ibm", "intel",
    "paypal", "shopify", "github", "reddit", "discord", "zoom",
}


def _is_global_brand(tag: str) -> bool:
    """Check if tag refers to a globally dominant brand."""
    t = _normalize_tag(tag)
    if t in GLOBAL_BRANDS:
        return True
    words = t.split()
    for w in words:
        if w in LOCAL_BRAND_WORDS:
            return True
    return False


# ---------------------------------------------------------------------------
# 6  duplicate normalisation  (Phase 5: stronger dedup)
# ---------------------------------------------------------------------------

def _normalize_tag(tag: str) -> str:
    t = tag.strip().lstrip("#").lower()
    t = re.sub(r"\s+", "", t)
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
    prod_rel = c.get("product_relevance", 0)
    tr = c["trend_score"]
    comp = c["competition_score"]
    fit = c["platform_fit"]
    tag = c.get("tag", "")
    bonus = c.get("product_bonus", 0)

    if prod_rel >= 70 and bonus > 0:
        labels.append("Product Match")
    elif prod_rel >= 55:
        labels.append("Product Related")

    if rel >= 80:
        labels.append("Excellent Match")
    elif rel >= 60:
        labels.append("Strong Match")

    if tr >= 70:
        labels.append("Trending")
    elif tr >= 55:
        labels.append("Rising")
    elif tr >= 40 and comp <= 35:
        labels.append("Emerging")

    if comp <= 20:
        labels.append("Low Competition")
    elif comp <= 35:
        labels.append("Moderate Competition")

    if fit >= 80:
        labels.append("Platform Favorite")
    elif fit >= 60:
        labels.append("Platform Friendly")

    if c.get("is_blue_ocean"):
        labels.append("Blue Ocean")
    if c.get("is_hidden_gem"):
        labels.append("Hidden Gem")

    if c.get("category") == "Industry Term":
        if platform == "LinkedIn":
            labels.append("Professional Term")
        else:
            labels.append("Technical")
    elif c.get("category") == "Brand":
        labels.append("Brand Label")
    elif c.get("category") == "Hashtag" and platform in ("Instagram", "TikTok"):
        labels.append("Creator Friendly")

    if rel > 50 and comp < 35 and 30 <= tr <= 65:
        labels.append("Long Tail")

    if rel > 55 and comp < 40 and tr < 30:
        labels.append("Evergreen")

    if "Low Competition" in labels and "Moderate Competition" in labels:
        labels.remove("Moderate Competition")
    if "Blue Ocean" in labels and "Hidden Gem" in labels:
        labels.remove("Hidden Gem")

    return labels[:3]


# ---------------------------------------------------------------------------
# 9  explanation generator  (analyst language, multiple templates)
# ---------------------------------------------------------------------------

_SEMANTIC_DESC = {
    80: "This term has excellent semantic alignment with your niche profile",
    60: "Good semantic match — relevant to your core topic and product offering",
    40: "Moderate thematic connection to your niche; not a direct match but adjacent",
    0: "Limited semantic relevance — may resonate more in adjacent niches",
}

_TREND_DESC = {
    70: "Demand signals are strong with consistent search volume and growing interest",
    55: "Moderate-to-rising trend momentum detected across recent data",
    40: "Steady but not explosive — reliable performer rather than breakout candidate",
    0: "Low trending activity currently; minimal organic discovery potential",
}

_COMP_DESC = {
    75: "Competition is remarkably low — this space is underserved by existing content",
    55: "Competition is manageable — there is room to establish authority without fighting for saturation",
    35: "Moderate competition — content exists but the field is not fully crowded",
    0: "Heavily saturated — many content pieces already competing for the same terms",
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
    "Pinterest": {
        80: "Naturally aligned with Pinterest's visual discovery and inspiration-driven ecosystem",
        60: "Performs well within Pinterest's collection and idea-sharing format",
        40: "Moderate fit for Pinterest's aesthetic-focused platform",
        0: "Suboptimal — this tag type underperforms on Pinterest's visual discovery model",
    },
}


def _band_desc(band: str) -> str:
    return {
        "Elite": "Elite — top percentile ranking confidence",
        "Excellent": "Excellent — very strong ranking confidence",
        "Very Strong": "Very Strong — high ranking confidence",
        "Strong": "Strong — solid ranking confidence",
        "Moderate": "Moderate — adequate ranking confidence",
        "Fair": "Fair — moderate ranking confidence",
        "Weak": "Weak — lower ranking confidence",
    }.get(band, "Standard ranking confidence")


def generate_explanation(
    tag: str, semantic_relevance: float, trend_score: float,
    competition_score: float, platform_fit: float,
    rank: int, total: int, platform: str, category: str,
    band: str, opp_score: float, quality_labels: list[str],
) -> str:
    import random as _r
    _r.seed(hash(tag) % (2**31))

    def _desc(mapping: dict, value: float) -> str:
        for threshold, desc in sorted(mapping.items(), reverse=True):
            if value >= threshold:
                return desc
        return list(mapping.values())[-1]

    rel_desc = _desc(_SEMANTIC_DESC, semantic_relevance)
    trend_desc = _desc(_TREND_DESC, trend_score)
    comp_score_val = competition_score
    comp_desc = _desc(_COMP_DESC, 100 - comp_score_val) if comp_score_val < 40 else _desc(_COMP_DESC, comp_score_val)
    plat_map = _PLATFORM_DESC.get(platform, _PLATFORM_DESC["X"])
    plat_desc = _desc(plat_map, platform_fit)

    # Analyst templates
    if rank <= 3:
        templates = [
            f"{rel_desc}. {trend_desc.lower()}. {comp_desc.lower()} This combination makes it a {"strong top-tier" if rank==1 else "solid high-ranking"} recommendation for {platform}.",
            f"{tag}: {rel_desc.lower()}. On {platform}, {plat_desc.lower()}. With {_desc(_COMP_DESC, 100-comp_score_val).lower()}, this term stands out from alternatives.",
            f"This {"industry term" if category=="Industry Term" else "keyword" if category=="Keyword" else "tag"} {"matches your niche exceptionally well" if semantic_relevance>70 else "is relevant to your niche"}. The trend profile suggests {trend_desc.lower()} and the competitive landscape is {comp_desc.lower()}.",
        ]
    elif rank <= 6:
        templates = [
            f"{rel_desc}. {trend_desc}. Competition analysis: {comp_desc}. On {platform}, {plat_desc}.",
            f"{tag} combines {f"strong relevance ({semantic_relevance:.0f})" if semantic_relevance>60 else f"adequate relevance ({semantic_relevance:.0f})"} with {f"healthy demand signals ({trend_score:.0f})" if trend_score>50 else f"stable demand ({trend_score:.0f})"} and {f"low saturation ({comp_score_val:.0f})" if comp_score_val<40 else f"moderate saturation ({comp_score_val:.0f})"}.",
        ]
    else:
        templates = [
            f"{rel_desc}. {trend_desc}. {comp_desc}.",
            f"{tag}: relevance {semantic_relevance:.0f}, demand {trend_score:.0f}, saturation {comp_score_val:.0f}. Platform fit for {platform}: {platform_fit:.0f}.",
        ]

    parts = [templates[_r.randint(0, len(templates)-1)]]

    if category:
        joiners = ["Sits in the", "Categorized under", "Belongs to the"]
        parts.append(f"{_r.choice(joiners)} {category} segment." if _r.random()>0.3 else f"Fits into the {category} category.")

    if quality_labels:
        parts.append(f"Quality signals: {', '.join(quality_labels)}.")

    if opp_score > 12:
        phrases = [
            f"Opportunity score {opp_score:.0f} — early-mover advantage in an emerging space.",
            f"With an opportunity score of {opp_score:.0f}, this term represents attractive first-mover potential.",
            f"Scored {opp_score:.0f} on opportunity — positioning ahead of the curve.",
        ]
        parts.append(_r.choice(phrases))

    avg = (semantic_relevance + trend_score + platform_fit + (100 - comp_score_val)) / 4
    if avg > 60:
        closing = [
            "A well-rounded recommendation with balanced signals across all dimensions.",
            "Strong multi-signal candidate — performs well on relevance, demand, and platform fit.",
            "Solid all-around performer with no significant weak points in the scoring profile.",
        ]
        if _r.random() > 0.5:
            parts.append(_r.choice(closing))

    return " ".join(parts)


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

    # 1  batch semantic relevance (topic + product combined)
    rel_scores = batch_semantic_relevance(tags, topic, product)

    # 1b  product relevance (product alone — higher if tag matches specific product)
    prod_rel_scores = batch_product_relevance(tags, product)

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

    # Extract product vocab for confidence bonus
    from backend.product_vocab import extract_product_vocab
    pv = extract_product_vocab(product, topic)
    product_terms = pv.get("all_terms", set())
    if not isinstance(product_terms, set):
        product_terms = set(product_terms)

    # 5  assemble enriched candidates with score breakdown
    enriched: list[dict] = []
    for i in range(len(tags)):
        rel = rel_scores[i]
        prod_rel = prod_rel_scores[i]
        tr = trend_scores[i]
        comp = comp_scores[i]
        fit = fit_scores[i]
        low_comp = compute_low_competition(comp)
        cat = categories[i] if categories[i] in EXPECTED_CATEGORIES else "Keyword"
        opp = round(rel * tr * (100 - comp) / 10000.0, 1)

        # Product confidence bonus: only when tag strongly matches the product
        product_bonus = 0
        tag_lower = tags[i].lower()
        tag_words = set(tag_lower.split())
        if prod_rel >= 65:
            product_bonus = 8
        elif prod_rel >= 50:
            product_bonus = 5
        elif (product_terms & tag_words) and prod_rel >= 35:
            product_bonus = 4
        elif any(a in tag_lower for a in pv.get("aliases", [])) and prod_rel >= 40:
            product_bonus = 3

        prod_contrib = round(prod_rel * W_PRODUCT, 1)
        sem_contrib = round(rel * W_REL, 1)
        trend_contrib = round(tr * W_TREND, 1)
        comp_contrib = round(low_comp * W_LOW_COMP, 1)
        plat_contrib = round(fit * W_PLATFORM, 1)
        conf_contrib = round(profile_conf * W_CONF, 1)

        final = round(prod_contrib + sem_contrib + trend_contrib + comp_contrib + plat_contrib + conf_contrib + product_bonus, 1)

        score_breakdown = {
            "product_contribution": prod_contrib,
            "semantic_contribution": sem_contrib,
            "trend_contribution": trend_contrib,
            "competition_contribution": comp_contrib,
            "platform_contribution": plat_contrib,
            "confidence_contribution": conf_contrib,
            "product_bonus": product_bonus,
            "weights": {
                "product": W_PRODUCT,
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
            "product_relevance": prod_rel,
            "trend_score": tr,
            "competition_score": comp,
            "platform_fit": fit,
            "product_bonus": product_bonus,
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

        # Product-aware enhancements
        tag_words_set = set(tag_name.lower().split())
        is_product_specific = bool(product_terms & tag_words_set) or any(a in tag_name.lower() for a in pv.get("aliases", []))
        prod_rel = c.get("product_relevance", 0)

        # Blue ocean: niche opportunities with first-mover potential
        is_global = _is_global_brand(tag_name)
        is_long_tail = len(tag_name.split()) >= 3
        is_tech_term = cat == "Industry Term" and any(w in tag_name.lower() for w in ["tech", "ai", "ml", "data", "cloud", "api", "saas", "system", "platform", "solution", "software", "digital", "automation", "analytics"])

        # Blue ocean: product-specific terms with low comp get priority; generic niche words need higher opp
        if is_product_specific:
            is_bo = opp > 6.0 and comp < 50
        elif is_long_tail and opp > 8.0 and comp < 40:
            is_bo = True
        elif is_tech_term and opp > 8.0 and comp < 45:
            is_bo = True
        else:
            is_bo = opp > 12.0 and comp < 40 and tr > 40 and not is_global

        is_hg = rel > 55 and comp < 35 and tr < 50 and not is_bo and not is_global and (is_product_specific or is_long_tail)
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

    # --- lightweight category diversity swap: avoid >3 of the same category in top 10
    if len(result) >= 6:
        cat_counts: dict[str, int] = {}
        for t in result[:DISPLAY_K]:
            cat = t.category or "Keyword"
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        for idx in range(min(DISPLAY_K, len(result))):
            cur_cat = result[idx].category or "Keyword"
            if cat_counts.get(cur_cat, 0) >= 3:
                for swap_idx in range(idx + 1, len(result)):
                    swap_cat = result[swap_idx].category or "Keyword"
                    if cat_counts.get(swap_cat, 0) is not None and cat_counts.get(swap_cat, 0) <= 1:
                        if swap_idx < DISPLAY_K:
                            result[idx], result[swap_idx] = result[swap_idx], result[idx]
                            cat_counts[cur_cat] = cat_counts.get(cur_cat, 0) - 1
                            cat_counts[swap_cat] = cat_counts.get(swap_cat, 0) + 1
                        break

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
        reasons.append("Very high competition makes it difficult to gain visibility")
    if rel < 30:
        reasons.append("Limited semantic relevance to the chosen niche")
    if plat < 25:
        reasons.append("Weak alignment with platform content dynamics")
    if trend < 20:
        reasons.append("Insufficient trend momentum to generate organic reach")
    if not reasons:
        reasons.append("Outranked by stronger candidates in the final evaluation")
    return " ".join(reasons) + ""


def _blue_ocean_reason(bo: CandidateTag) -> str:
    rel_label = "Excellent relevance" if bo.semantic_relevance > 70 else "Strong topical relevance"
    demand_label = "rising demand" if bo.trend_score > 65 else "consistent demand"
    sat_label = "minimal saturation" if bo.competition_score < 25 else "low saturation"
    return (
        f"{rel_label} ({bo.semantic_relevance:.0f}) + "
        f"{demand_label} ({bo.trend_score:.0f}) + "
        f"{sat_label} ({bo.competition_score:.0f}) = "
        f"blue ocean opportunity with first-mover potential"
    )


def _hidden_gem_reason(hg: CandidateTag) -> str:
    return (
        f"Strong topical relevance ({hg.semantic_relevance:.0f}) paired with "
        f"low competitive pressure ({hg.competition_score:.0f}) and "
        f"{'moderate' if hg.trend_score < 50 else 'growing'} trend activity ({hg.trend_score:.0f}) "
        f"— a long-tail opportunity with favorable positioning for future growth"
    )



