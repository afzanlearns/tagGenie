from keybert import KeyBERT
import spacy
import json
from pathlib import Path
from backend.llm import expand_topic

_ke_model = None
_nlp = None


def _get_ke():
    global _ke_model
    if _ke_model is None:
        _ke_model = KeyBERT()
    return _ke_model


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def extract_hashtags(text: str, top_n: int = 15) -> list[str]:
    kw_model = _get_ke()
    keywords = kw_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 3),
        stop_words="english",
        top_n=top_n,
        use_mmr=True,
        diversity=0.4,
    )
    tags = []
    seen = set()
    for kw, _ in keywords:
        tag = kw.strip().lower()
        if tag not in seen and len(tag) > 2:
            seen.add(tag)
            tags.append(tag)
    return tags


def extract_candidates(topic: str, product: str) -> list[dict]:
    expanded = expand_topic(topic, product)
    if not expanded or not expanded.strip():
        expanded = f"{topic} {product}"

    raw_keywords = extract_hashtags(expanded, top_n=25)
    if not raw_keywords:
        raw_keywords = [w.strip() for w in f"{topic} {product}".lower().split() if len(w.strip()) > 2]

    nlp = _get_nlp()
    doc = nlp(expanded)

    candidates = []
    seen = set()
    for kw in raw_keywords:
        if kw not in seen:
            seen.add(kw)
            tag_type = "hashtag" if len(kw.split()) <= 2 else "keyword"
            candidates.append({"tag": kw, "type": tag_type})

    for chunk in doc.noun_chunks:
        phrase = chunk.text.strip().lower()
        if len(phrase.split()) >= 2 and phrase not in seen:
            seen.add(phrase)
            candidates.append({"tag": phrase, "type": "keyword"})

    return candidates[:25]
