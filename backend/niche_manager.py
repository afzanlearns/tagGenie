"""Niche management: load, list, create, and switch between industry niches."""

import json
import random
import sqlite3
from pathlib import Path
from typing import Optional

NICHES_DIR = Path(__file__).parent.parent / "niches"
DATA_DIR = Path(__file__).parent.parent / "data"

_active_niche_id = "gps-telematics"


def _get_user_niches_db() -> Path:
    return DATA_DIR / "user_niches.db"


def _init_user_niches_db():
    db = _get_user_niches_db()
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_niches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            niche_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            description TEXT DEFAULT '',
            config TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, niche_id)
        )
    """)
    conn.commit()
    conn.close()


def get_available_niches(user_id: str = None) -> list[dict]:
    """Discover all configured niches.

    Global niches from the niches/ directory are always included.
    If user_id is provided, also includes user-created custom niches.
    Guest users delegate to in-memory guest store.
    """
    if user_id and user_id.startswith("guest_"):
        from backend.guest_store import get_available_niches as _guest_list
        return _guest_list(user_id)

    _init_user_niches_db()

    global_niches = _get_global_niches()

    if user_id is None:
        return global_niches

    conn = sqlite3.connect(str(_get_user_niches_db()))
    rows = conn.execute(
        "SELECT config FROM user_niches WHERE user_id = ? ORDER BY created_at",
        (user_id,),
    ).fetchall()
    conn.close()

    user_niches = [json.loads(r[0]) for r in rows]
    return global_niches + user_niches


def _get_global_niches() -> list[dict]:
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


def get_niche_config(niche_id: str, user_id: str = None) -> Optional[dict]:
    """Get the config for a specific niche by ID."""
    if user_id and user_id.startswith("guest_"):
        from backend.guest_store import get_niche_config as _guest_get_config
        return _guest_get_config(user_id, niche_id)
    for n in get_available_niches(user_id):
        if n["niche_id"] == niche_id:
            return n
    return None


def get_jargon(niche_id: str, user_id: str = None) -> dict:
    """Load the jargon expansion file for a niche.

    Checks user-specific niche data first, then falls back to global files.
    """
    if user_id and user_id.startswith("guest_"):
        from backend.guest_store import get_jargon as _guest_get_jargon
        return _guest_get_jargon(user_id, niche_id)

    if user_id:
        data = _get_user_niche_data(user_id, niche_id)
        if data and data.get("jargon"):
            return json.loads(data["jargon"]) if isinstance(data["jargon"], str) else data["jargon"]

    path = NICHES_DIR / niche_id / "jargon_expansion.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"industry_terms": {}, "abbreviations": {}, "trending_concepts": []}


def get_seed_corpus(niche_id: str, user_id: str = None) -> list[str]:
    """Load the seed corpus for a niche.

    Checks user-specific niche data first, then falls back to global files.
    """
    if user_id and user_id.startswith("guest_"):
        from backend.guest_store import get_seed_corpus as _guest_get_corpus
        return _guest_get_corpus(user_id, niche_id)
    if user_id:
        data = _get_user_niche_data(user_id, niche_id)
        if data and data.get("corpus"):
            return json.loads(data["corpus"]) if isinstance(data["corpus"], str) else data["corpus"]

    path = NICHES_DIR / niche_id / "seed_corpus.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def get_niche_profile(niche_id: str, user_id: str = None) -> dict:
    """Load the structured industry vocabulary profile for a niche.

    Returns a dict with keys: industry_terms, products, topics, hashtags,
    brands, audience, synonyms.
    Falls back to empty profile if none exists.
    """
    if user_id and user_id.startswith("guest_"):
        from backend.guest_store import get_niche_profile as _guest_profile
        return _guest_profile(user_id, niche_id)

    config = get_niche_config(niche_id, user_id)
    if config and "_profile" in config:
        return config["_profile"]

    path = NICHES_DIR / niche_id / "profile.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)

    return {
        "industry_terms": [],
        "products": [],
        "topics": [],
        "hashtags": [],
        "brands": [],
        "audience": [],
        "synonyms": {},
        "all_terms": [],
    }


def _get_user_niche_data(user_id: str, niche_id: str):
    """Fetch a user's custom niche data (corpus, jargon) from the DB."""
    conn = sqlite3.connect(str(_get_user_niches_db()))
    row = conn.execute(
        "SELECT config FROM user_niches WHERE user_id = ? AND niche_id = ?",
        (user_id, niche_id),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    config = json.loads(row[0])
    return {
        "corpus": config.get("_corpus", "[]"),
        "jargon": config.get("_jargon", "{}"),
    }


def get_active_niche(user_id: str = None) -> str:
    """Get the active niche for a user.

    Guest users: retrieved from in-memory guest store.
    Authenticated users: retrieved from user_niches DB.
    Falls back to the global active niche if no user-specific preference.
    """
    if user_id and user_id.startswith("guest_"):
        from backend.guest_store import get_active_niche as _guest_get_active
        return _guest_get_active(user_id)
    if user_id:
        stored = _get_user_active_niche(user_id)
        if stored:
            return stored
    return _active_niche_id


def _get_user_active_niche(user_id: str):
    """Get the stored active niche for an authenticated user."""
    try:
        conn = sqlite3.connect(str(_get_user_niches_db()))
        row = conn.execute(
            "SELECT niche_id FROM user_niches WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        conn.close()
        if row:
            return row[0]
    except Exception:
        pass
    return None


def set_active_niche(niche_id: str, user_id: str = None) -> bool:
    """Switch the active niche. Returns True if successful.

    Guest users: stored in-memory.
    Authenticated users: stored in user_niches DB.
    Also updates the global active niche for the current session.
    """
    global _active_niche_id
    if not get_niche_config(niche_id, user_id):
        return False
    _active_niche_id = niche_id
    if user_id and user_id.startswith("guest_"):
        from backend.guest_store import set_active_niche as _guest_set_active
        return _guest_set_active(user_id, niche_id)
    return True


def build_jargon_context(niche_id: str, user_id: str = None) -> str:
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
    user_id: str = None,
    profile: dict = None,
) -> dict:
    """Save a user-reviewed niche draft for a specific user.

    Authenticated users: stored in user_niches DB (per-user).
    Guest users: stored in-memory via guest_store.
    The profile contains the structured industry vocabulary.
    """
    if profile is None:
        profile = {
            "industry_terms": [], "products": [], "topics": [],
            "hashtags": [], "brands": [], "audience": [],
            "synonyms": {}, "all_terms": [],
        }

    config = {
        "niche_id": niche_id,
        "display_name": display_name,
        "description": description,
        "default_platforms": ["LinkedIn", "Instagram", "X", "TikTok"],
        "sample_topics": sample_topics[:5],
        "created_at": "2026-06-19T00:00:00Z",
        "_corpus": corpus[:100],
        "_jargon": jargon,
        "_profile": profile,
    }

    if user_id and user_id.startswith("guest_"):
        from backend.guest_store import add_custom_niche
        add_custom_niche(user_id, config, corpus=corpus[:100], jargon=jargon, profile=profile)
        return config

    _init_user_niches_db()
    conn = sqlite3.connect(str(_get_user_niches_db()))
    conn.execute(
        "INSERT OR REPLACE INTO user_niches (user_id, niche_id, display_name, description, config) VALUES (?, ?, ?, ?, ?)",
        (user_id, niche_id, display_name, description, json.dumps(config)),
    )
    conn.commit()
    conn.close()
    return config


def create_custom_niche(
    niche_id: str,
    display_name: str,
    description: str,
    sample_posts: list[str],
    user_id: str = None,
    profile: dict = None,
) -> dict:
    """Create a new niche from user-supplied sample posts.

    Authenticated users: persisted to user_niches DB.
    Guest users: stored in-memory.
    The profile contains structured industry vocabulary.
    """
    corpus = sample_posts[:100]
    jargon = _auto_generate_jargon(niche_id, sample_posts)
    if profile is None:
        profile = {
            "industry_terms": [], "products": [], "topics": [],
            "hashtags": [], "brands": [], "audience": [],
            "synonyms": {}, "all_terms": [],
        }

    config = {
        "niche_id": niche_id,
        "display_name": display_name,
        "description": description,
        "default_platforms": ["LinkedIn", "Instagram", "X", "TikTok"],
        "sample_topics": [
            p for p in _extract_sample_topics(sample_posts)
        ][:5],
        "created_at": "2026-06-19T00:00:00Z",
        "_corpus": corpus,
        "_jargon": jargon,
        "_profile": profile,
    }

    if user_id and user_id.startswith("guest_"):
        from backend.guest_store import add_custom_niche
        add_custom_niche(user_id, config, corpus=corpus, jargon=jargon, profile=profile)
        return config

    _init_user_niches_db()
    conn = sqlite3.connect(str(_get_user_niches_db()))
    conn.execute(
        "INSERT OR REPLACE INTO user_niches (user_id, niche_id, display_name, description, config) VALUES (?, ?, ?, ?, ?)",
        (user_id, niche_id, display_name, description, json.dumps(config)),
    )
    conn.commit()
    conn.close()
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
