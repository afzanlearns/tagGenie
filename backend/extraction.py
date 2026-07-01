"""Candidate extraction using stored niche vocabulary profiles.

No KeyBERT. No LLM prose generation.
Every candidate comes from the niche's structured vocabulary profile,
matched semantically to the user's topic/product query.

Product-aware: generates additional candidates from the product vocabulary
and blends them with niche-based candidates.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from backend.niche_manager import get_niche_profile, get_active_niche
from backend.candidate_filter import filter_candidates, semantic_confidence, normalize_term, is_valid_candidate
from backend.product_vocab import extract_product_vocab

_sim_model = None


def _get_sim_model():
    global _sim_model
    if _sim_model is None:
        _sim_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sim_model


def _product_candidates(product: str, topic: str) -> list[dict]:
    """Generate candidate tags directly from the product vocabulary."""
    pv = extract_product_vocab(product, topic)
    seen = set()
    candidates = []

    # Common product-content phrase patterns
    suffixes = [" ideas", " inspiration", " guide", " tutorial", " review", " comparison",
                " tips", " tricks", " hacks", " setup", " unboxing", " collection",
                " community", " lovers", " fans", " for sale", " near me"]
    prefixes = ["best ", "top ", "affordable ", "luxury ", "vintage ", "new ",
                "how to ", "why ", "what is "]

    def add(term, cat="Keyword"):
        t = term.strip().lower()
        if t and len(t) > 2 and t not in seen:
            seen.add(t)
            tag_type = "hashtag" if len(t.split()) <= 2 else "keyword"
            candidates.append({"tag": t, "type": tag_type, "category": cat, "confidence": 60.0})

    # Core product terms (avoid single-letter or very short abbreviations)
    for term in pv.get("all_terms", set()):
        if len(term) >= 2:
            add(term)
    for alias in pv.get("aliases", []):
        if len(alias) >= 2:
            add(alias)

    raw_words = set(w.lower().strip(".,!?;:'\"") for w in product.split()
                     if len(w) > 2 and w.lower() not in {"the", "a", "an", "of", "for", "in", "and", "with", "to", "&"})
    for w in raw_words:
        add(w)

    # Product-content phrases (e.g. "booster opening", "pull rates")
    pv_lower = product.lower()
    product_content_pairs = _get_product_content_phrases(pv_lower, pv)
    for phrase in product_content_pairs[:10]:
        add(phrase, "Topic")

    edition = pv.get("edition", "")
    if edition:
        add(f"{edition} opening", "Topic")
        add(f"{edition} review", "Topic")
        add(f"{edition} collection", "Topic")
        if edition in ("booster", "booster box", "pack"):
            add("pull rates", "Topic")
            add("pack opening", "Topic")

    model = pv.get("model", "")
    if model and len(model) > 1:
        add(f"{model} review", "Topic")
        add(f"{model} vs", "Topic")

    # Prefix/suffix with non-abbreviated product words (len >= 4)
    meaningful = set()
    for w in raw_words:
        if len(w) >= 4:
            meaningful.add(w)
    meaningful.add(product.lower().strip())
    for m in list(meaningful)[:2]:
        add(m)
        for suf in suffixes[:5]:
            add(f"{m}{suf}")
        for pref in prefixes[:4]:
            add(f"{pref}{m}")

    return candidates


def _get_product_content_phrases(pv_lower: str, pv: dict) -> list[str]:
    """Generate phrases that combine product terms with content/community words."""
    phrases = []
    combos = [
        (["opening", "unboxing", "review", "haul", "collection"], "Topic"),
        (["community", "fans", "lovers", "enthusiasts"], "Audience"),
        (["price", "cost", "value", "deal", "sale"], "Topic"),
        (["vs", "versus", "comparison", "alternative", "best"], "Topic"),
        (["setup", "display", "storage", "organization"], "Topic"),
        (["rare", "limited", "special", "exclusive", "custom"], "Topic"),
    ]

    family = pv.get("family", "").lower()
    base_terms = set()
    for t in pv.get("all_terms", set()):
        base_terms.add(t)
    for w in pv_lower.split():
        if len(w) > 2:
            base_terms.add(w)

    for base in base_terms:
        for words, cat in combos:
            for w in words:
                phrases.append(f"{base} {w}")

    # Model/edition specific
    model = pv.get("model", "")
    edition = pv.get("edition", "")
    if model and edition:
        phrases.append(f"{model} {edition}")
    return list(dict.fromkeys(phrases))


def extract_candidates(topic: str, product: str, niche_id: str = None,
                       user_id: str = None) -> list[dict]:
    if niche_id is None:
        niche_id = get_active_niche(user_id)

    profile = get_niche_profile(niche_id, user_id)

    all_vocab = []
    term_to_category: dict[str, str] = {}
    if profile:
        category_map = {
            "industry_terms": "Industry Term",
            "products": "Product",
            "topics": "Topic",
            "hashtags": "Hashtag",
            "brands": "Brand",
            "audience": "Audience",
        }
        for cat_key, display_cat in category_map.items():
            terms = profile.get(cat_key, [])
            for t in terms:
                t_lower = t.strip().lower()
                all_vocab.append(t_lower)
                term_to_category[t_lower] = display_cat

        synonyms = profile.get("synonyms", {})
        for key, syn_list in synonyms.items():
            k = key.strip().lower()
            all_vocab.append(k)
            if k not in term_to_category:
                term_to_category[k] = "Topic"
            for syn in syn_list:
                s = syn.strip().lower()
                all_vocab.append(s)
                if s not in term_to_category:
                    term_to_category[s] = "Topic"

        all_vocab = list(dict.fromkeys(all_vocab))

    combined_query = f"{topic} {product}"

    niche_candidates: list[dict] = []

    if all_vocab and len(all_vocab) >= 3:
        model = _get_sim_model()
        emb_vocab = model.encode(all_vocab)
        emb_query = model.encode([combined_query])
        scores = np.dot(emb_vocab, emb_query.T).flatten()
        top_indices = np.argsort(scores)[::-1][:50]
        threshold = 0.20
        for idx in top_indices:
            if scores[idx] >= threshold:
                term = all_vocab[idx].strip().lower()
                conf = round(float(scores[idx] * 100.0), 1)
                if is_valid_candidate(term, topic, product, min_confidence=25.0):
                    tag_type = "hashtag" if len(term.split()) <= 2 else "keyword"
                    category = term_to_category.get(term, "Keyword")
                    niche_candidates.append({"tag": term, "type": tag_type, "category": category, "confidence": conf})

    # Product-aware candidates
    product_cands = _product_candidates(product, topic)

    # Merge: niche candidates first, then product-specific candidates (de-duped)
    seen_tags = set()
    merged = []
    for c in niche_candidates + product_cands:
        norm = c["tag"]
        if norm not in seen_tags:
            seen_tags.add(norm)
            merged.append(c)

    if merged:
        merged.sort(key=lambda x: x["confidence"], reverse=True)
        return merged[:40]

    fallback_terms = _generate_fallback_terms(topic, product)
    filtered = filter_candidates(fallback_terms, topic, product, min_confidence=25.0)
    return [
        {"tag": t, "type": "hashtag" if len(t.split()) <= 2 else "keyword", "category": "Keyword", "confidence": 50.0}
        for t in filtered[:20]
    ]


def _generate_fallback_terms(topic: str, product: str) -> list[str]:
    terms = []
    words = f"{topic} {product}".lower().split()
    for i in range(len(words)):
        for j in range(i + 1, min(i + 4, len(words) + 1)):
            phrase = " ".join(words[i:j])
            if len(phrase) > 2:
                terms.append(phrase)
    return terms
