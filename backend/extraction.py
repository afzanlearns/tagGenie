"""Candidate extraction using stored niche vocabulary profiles.

No KeyBERT. No LLM prose generation.
Every candidate comes from the niche's structured vocabulary profile,
matched semantically to the user's topic/product query.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from backend.niche_manager import get_niche_profile, get_active_niche
from backend.candidate_filter import filter_candidates, semantic_confidence, normalize_term, is_valid_candidate

_sim_model = None


def _get_sim_model():
    global _sim_model
    if _sim_model is None:
        _sim_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sim_model


def extract_candidates(topic: str, product: str, niche_id: str = None,
                       user_id: str = None) -> list[dict]:
    if niche_id is None:
        niche_id = get_active_niche(user_id)

    profile = get_niche_profile(niche_id, user_id)

    all_vocab = []
    if profile:
        for cat in ["industry_terms", "products", "topics", "hashtags", "brands", "audience"]:
            all_vocab.extend(profile.get(cat, []))

        synonyms = profile.get("synonyms", {})
        for key, syn_list in synonyms.items():
            all_vocab.append(key)
            all_vocab.extend(syn_list)

        all_vocab = list(dict.fromkeys(all_vocab))

    combined_query = f"{topic} {product}"

    if all_vocab and len(all_vocab) >= 3:
        model = _get_sim_model()
        emb_vocab = model.encode(all_vocab)
        emb_query = model.encode([combined_query])
        scores = np.dot(emb_vocab, emb_query.T).flatten()
        top_indices = np.argsort(scores)[::-1][:40]
        threshold = 0.25
        scored_terms = []
        for idx in top_indices:
            if scores[idx] >= threshold:
                term = all_vocab[idx].strip().lower()
                conf = round(float(scores[idx] * 100.0), 1)
                if is_valid_candidate(term, topic, product, min_confidence=30.0):
                    tag_type = "hashtag" if len(term.split()) <= 2 else "keyword"
                    scored_terms.append({"tag": term, "type": tag_type, "confidence": conf})

        if scored_terms:
            scored_terms.sort(key=lambda x: x["confidence"], reverse=True)
            return scored_terms[:25]

    fallback_terms = _generate_fallback_terms(topic, product)
    filtered = filter_candidates(fallback_terms, topic, product, min_confidence=25.0)
    return [
        {"tag": t, "type": "hashtag" if len(t.split()) <= 2 else "keyword", "confidence": 50.0}
        for t in filtered[:15]
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
