"""Niche management: load, list, create, and switch between industry niches."""

import json
import random
from pathlib import Path
from typing import Optional

NICHES_DIR = Path(__file__).parent.parent / "niches"

_active_niche_id = "gps-telematics"


def get_available_niches() -> list[dict]:
    """Discover all configured niches from the niches/ directory."""
    if not NICHES_DIR.exists():
        return [_get_default_niche_config()]

    niches = []
    for d in sorted(NICHES_DIR.iterdir()):
        config_file = d / "config.json"
        if d.is_dir() and config_file.exists():
            with open(config_file) as f:
                cfg = json.load(f)
            niches.append(cfg)
    return niches if niches else [_get_default_niche_config()]


def _get_default_niche_config() -> dict:
    return {
        "niche_id": "gps-telematics",
        "display_name": "GPS & Telematics",
        "description": "Fleet telematics and logistics industry",
        "default_platforms": ["LinkedIn", "Instagram", "X", "TikTok"],
        "sample_topics": ["fleet GPS tracking", "telematics dashboards"],
        "created_at": "2026-01-01T00:00:00Z",
    }


def get_niche_config(niche_id: str) -> Optional[dict]:
    """Get the config for a specific niche by ID."""
    for n in get_available_niches():
        if n["niche_id"] == niche_id:
            return n
    return None


def get_jargon(niche_id: str) -> dict:
    """Load the jargon expansion file for a niche."""
    path = NICHES_DIR / niche_id / "jargon_expansion.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"industry_terms": {}, "abbreviations": {}, "trending_concepts": []}


def get_seed_corpus(niche_id: str) -> list[str]:
    """Load the seed corpus for a niche."""
    path = NICHES_DIR / niche_id / "seed_corpus.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def get_active_niche() -> str:
    """Get the currently active niche ID."""
    return _active_niche_id


def set_active_niche(niche_id: str) -> bool:
    """Switch the active niche. Returns True if successful."""
    global _active_niche_id
    if get_niche_config(niche_id) is not None:
        _active_niche_id = niche_id
        return True
    return False


def build_jargon_context(niche_id: str) -> str:
    """Build a formatted string of industry terms from the jargon file."""
    jargon = get_jargon(niche_id)
    parts = []

    for category, terms in jargon.get("industry_terms", {}).items():
        prefix = category.replace("_", " ").title()
        parts.append(f"{prefix}: {', '.join(terms)}")

    abbrevs = jargon.get("abbreviations", {})
    if abbrevs:
        abbrev_strs = [f"{k} ({v})" for k, v in abbrevs.items()]
        parts.append(f"Abbreviations: {', '.join(abbrev_strs)}")

    trending = jargon.get("trending_concepts", [])
    if trending:
        parts.append(f"Trending concepts: {', '.join(trending)}")

    return "\n".join(parts)


def save_niche_draft(
    niche_id: str,
    display_name: str,
    description: str,
    sample_posts: list[str],
    corpus: list[str],
    jargon: dict,
    sample_topics: list[str],
) -> dict:
    """Save a user-reviewed niche draft to disk.
    
    This is the second step of the two-step creation flow:
    1. generate_niche_draft() — LLM produces draft config
    2. User reviews/edits in UI
    3. save_niche_draft() — writes final files to disk
    """
    niche_dir = NICHES_DIR / niche_id
    niche_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "niche_id": niche_id,
        "display_name": display_name,
        "description": description,
        "default_platforms": ["LinkedIn", "Instagram", "X", "TikTok"],
        "sample_topics": sample_topics[:5],
        "created_at": "2026-06-19T00:00:00Z",
    }
    with open(niche_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    with open(niche_dir / "seed_corpus.json", "w") as f:
        json.dump(corpus[:100], f, indent=2)

    with open(niche_dir / "jargon_expansion.json", "w") as f:
        json.dump(jargon, f, indent=2)

    return config


def create_custom_niche(
    niche_id: str,
    display_name: str,
    description: str,
    sample_posts: list[str],
) -> dict:
    """Create a new niche from user-supplied sample posts.
    
    Takes 20+ sample posts, generates:
    - config.json
    - seed_corpus.json (the posts themselves)
    - A starter jargon_expansion.json by heuristics (auto-generated terms)
    """
    niche_dir = NICHES_DIR / niche_id
    niche_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "niche_id": niche_id,
        "display_name": display_name,
        "description": description,
        "default_platforms": ["LinkedIn", "Instagram", "X", "TikTok"],
        "sample_topics": [
            p for p in _extract_sample_topics(sample_posts)
        ][:5],
        "created_at": "2026-06-19T00:00:00Z",
    }
    with open(niche_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    corpus = sample_posts[:100]
    with open(niche_dir / "seed_corpus.json", "w") as f:
        json.dump(corpus, f, indent=2)

    jargon = _auto_generate_jargon(niche_id, sample_posts)
    with open(niche_dir / "jargon_expansion.json", "w") as f:
        json.dump(jargon, f, indent=2)

    return config


def _extract_sample_topics(posts: list[str]) -> list[str]:
    """Extract topic-like phrases from the first few words of posts."""
    topics = set()
    for p in posts:
        words = p.split()[:5]
        if len(words) >= 3:
            topics.add(" ".join(words[:3]).lower().rstrip(",.!?"))
    return list(topics)


def _auto_generate_jargon(niche_id: str, posts: list[str]) -> dict:
    """Auto-generate a starter jargon file from sample posts using heuristics.
    
    Extracts frequent bigrams, domain-specific terms, and abbreviations.
    The user will review and edit this before saving.
    """
    import re
    from collections import Counter

    words = []
    bigrams = []
    for post in posts:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", post.lower())
        tokens = cleaned.split()
        words.extend(tokens)
        for i in range(len(tokens) - 1):
            bigrams.append(f"{tokens[i]} {tokens[i+1]}")

    word_freq = Counter(words)
    bigram_freq = Counter(bigrams)

    common_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "as", "is", "was", "are",
        "were", "be", "been", "being", "have", "has", "had", "do",
        "does", "did", "will", "would", "could", "should", "may",
        "might", "shall", "can", "not", "no", "nor", "so", "if",
        "than", "that", "this", "these", "those", "it", "its",
        "over", "under", "between", "through", "during", "before",
        "after", "above", "below", "about", "into", "more", "some",
        "such", "than", "also", "very", "just", "because", "their",
        "them", "they", "which", "when", "where", "how", "what",
        "who", "whom", "both", "each", "few", "most", "other",
    }

    domain_words = [
        w for w, c in word_freq.most_common(200)
        if len(w) > 3 and w not in common_words
    ][:30]

    domain_phrases = [
        bg for bg, c in bigram_freq.most_common(100)
        if c > 1
    ][:20]

    abbrevs = []
    for w in domain_words:
        if w == w.upper() and 2 <= len(w) <= 5:
            abbrevs.append(w)

    adjacents = [
        t for t, c in bigram_freq.most_common(80)
        if c > 2
    ][:10]

    return {
        "niche": niche_id,
        "industry_terms": {
            "auto_detected_terms": domain_words,
            "common_phrases": domain_phrases,
            "adjacent_concepts": adjacents,
        },
        "abbreviations": {a: a for a in abbrevs},
        "adjacent_industries": [],
        "trending_concepts": domain_phrases[:5],
    }
