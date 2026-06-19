from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import CountVectorizer
import spacy
import json
from pathlib import Path
from backend.niche_manager import get_seed_corpus, get_active_niche

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _extract_raw_terms(text: str) -> list[str]:
    nlp = _get_nlp()
    doc = nlp(text.lower())
    tokens = set()
    for token in doc:
        if not token.is_stop and not token.is_punct and token.is_alpha and len(token.text) > 2:
            tokens.add(token.text)
    for chunk in doc.noun_chunks:
        phrase = chunk.text.strip()
        if len(phrase.split()) >= 2:
            tokens.add(phrase)
    return list(tokens)


def score_baseline(topic: str, product: str, niche_id: str = None) -> list[dict]:
    if niche_id is None:
        niche_id = get_active_niche()

    combined = f"{topic} {product}"
    terms = _extract_raw_terms(combined)
    if not terms:
        return []

    corpus = get_seed_corpus(niche_id)

    all_docs = corpus + [combined]
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),
        stop_words="english",
        max_features=500,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(all_docs)
    feature_names = vectorizer.get_feature_names_out()
    combined_vec = tfidf_matrix[-1].toarray()[0]

    results = []
    for term in terms:
        matches = [i for i, feat in enumerate(feature_names) if feat == term or feat.replace(" ", "") == term.replace(" ", "")]
        if matches:
            score = float(round(min(100.0, float(combined_vec[matches[0]]) * 100.0), 1))
        else:
            score = 0.0

        tag_type = "hashtag" if len(term.split()) <= 2 else "keyword"
        results.append({"tag": term, "type": tag_type, "score": score})

    if not results:
        for term in terms:
            tag_type = "hashtag" if len(term.split()) <= 2 else "keyword"
            results.append({"tag": term, "type": tag_type, "score": 0.0})

    count_vec = CountVectorizer(ngram_range=(1, 3), stop_words="english", max_features=500)
    count_matrix = count_vec.fit_transform([combined])
    count_features = count_vec.get_feature_names_out()
    count_vec_arr = count_matrix.toarray()[0]

    for idx, feat in enumerate(count_features):
        if feat in terms:
            continue
        tag_type = "hashtag" if len(feat.split()) <= 2 else "keyword"
        tf = float(count_vec_arr[idx])
        score = float(round(min(100.0, (tf / max(1, float(count_vec_arr.max()))) * 60.0), 1))
        results.append({"tag": feat, "type": tag_type, "score": score})

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:10]
