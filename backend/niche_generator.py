"""LLM-powered niche generation: takes sample posts, returns structured industry vocabulary.

The LLM NEVER generates prose or paragraphs.
It ONLY returns structured JSON vocabulary.
"""

import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from backend.candidate_filter import normalize_term, filter_candidates

load_dotenv(Path(__file__).parent / ".env")

_client = None

PROFILE_CATEGORIES = [
    "industry_terms",
    "products",
    "topics",
    "hashtags",
    "brands",
    "audience",
]


def _get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def generate_niche_draft(niche_id: str, display_name: str, sample_posts: list[str]) -> dict:
    """Call Groq LLM to generate a structured industry vocabulary profile.

    Returns a dict with:
    - description: auto-generated description
    - sample_topics: suggested search topics
    - profile: NicheProfile dict with industry_terms, products, topics, hashtags, brands, audience, synonyms
    - corpus: cleaned sample posts
    - _fallback: error message if LLM failed
    """
    client = _get_client()
    posts_text = "\n".join(f"- {p}" for p in sample_posts[:50])
    max_corpus = min(60, len(sample_posts))

    prompt = (
        f"You are an industry terminologist. Given {len(sample_posts)} sample social media posts "
        f"from the '{display_name}' industry (niche_id: '{niche_id}'), extract structured industry vocabulary.\n\n"
        f"CRITICAL: Return ONLY valid JSON. No explanations, no markdown, no code fences, no prose.\n\n"
        f"Sample posts:\n{posts_text}\n\n"
        f"Return a JSON object with these EXACT keys:\n"
        f'1. "description" (string): One-sentence description of this industry.\n'
        f'2. "sample_topics" (array of 5-8 strings): Topic queries someone in this niche would search for.\n'
        f"   Examples: \"Pokemon TCG booster box prices\", \"Rare Pokemon card grading\"\n"
        f'3. "profile" (object) — the structured vocabulary. Contains these keys:\n'
        f'   - "industry_terms" (array of strings): Core industry terminology, jargon, and domain-specific phrases. '
        f"Each term should be a real marketing keyword or industry term, never a sentence fragment.\n"
        f'     Examples: "Trading Cards", "Booster Pack", "PSA Grading", "Pokemon TCG"\n'
        f'   - "products" (array of strings): Products, services, and offerings in this industry.\n'
        f'     Examples: "Booster Box", "Elite Trainer Box", "Pokemon Plush"\n'
        f'   - "topics" (array of strings): Subjects, themes, and discussion topics.\n'
        f'     Examples: "Card Values", "Set Release Dates", "Tournament Strategies"\n'
        f'   - "hashtags" (array of strings): Social media hashtags and short tags (1-3 words, no # symbol).\n'
        f'     Examples: "PokemonCommunity", "TCGCommunity", "CardCollector"\n'
        f'   - "brands" (array of strings): Companies, brands, and entities.\n'
        f'     Examples: "Pokemon Company", "PSA", "Beckett"\n'
        f'   - "audience" (array of strings): Types of people, communities, and stakeholders.\n'
        f'     Examples: "Pokemon Collectors", "TCG Players", "Card Graders"\n'
        f'   - "synonyms" (object): Key terms mapped to their synonyms/alternate phrasings.\n'
        f'     Example: {{"pokemon cards": ["pokemon tcg", "pokemon trading cards", "pokemon collectibles"], '
        f'"card grading": ["psa grading", "card authentication", "grading service"]}}\n\n'
        f"RULES:\n"
        f"- Every term MUST be a real-world industry term, product name, or marketing keyword\n"
        f"- NEVER output sentence fragments like 'popularity certain pokemon' or 'characters affecting scarcity'\n"
        f"- NEVER output phrases that look like extracted from a sentence (e.g. 'rise of', 'how to', 'reasons why')\n"
        f"- Each term should be 1-4 words maximum\n"
        f"- Prioritize terms a marketer would actually use as hashtags or keywords\n"
        f"- industry_terms should have at least 25 entries across all categories combined\n"
        f"- hashtags should NOT include the # symbol\n"
        f'4. "corpus" (array of strings): A deduplicated, cleaned version of the sample posts. '
        f"Output at most {max_corpus} posts.\n\n"
        f"Return ONLY valid JSON. No markdown. No code fences. No explanation."
    )

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000,
            timeout=30.0,
        )
        raw = resp.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if "```" in raw:
                raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()

        result = json.loads(raw)

        profile = result.get("profile", {})
        for cat in PROFILE_CATEGORIES:
            if cat not in profile or not isinstance(profile[cat], list):
                profile[cat] = []
            profile[cat] = [normalize_term(t) for t in profile[cat] if isinstance(t, str)]

        if "synonyms" not in profile or not isinstance(profile["synonyms"], dict):
            profile["synonyms"] = {}

        description = result.get("description", f"Auto-generated niche for {display_name}")
        sample_topics = result.get("sample_topics", [])
        corpus = result.get("corpus", sample_posts[:max_corpus])

        all_terms = []
        for cat in PROFILE_CATEGORIES:
            all_terms.extend(profile[cat])
        for syn_list in profile.get("synonyms", {}).values():
            all_terms.extend(syn_list)

        clean_terms = filter_candidates(all_terms)
        profile["industry_terms"] = [t for t in clean_terms if t in profile.get("industry_terms", []) or True]
        profile["all_terms"] = clean_terms

        return {
            "description": description,
            "sample_topics": sample_topics[:8],
            "profile": profile,
            "corpus": corpus,
        }

    except (json.JSONDecodeError, Exception) as e:
        return {
            "description": f"Auto-generated niche for {display_name}",
            "sample_topics": sample_posts[:5],
            "profile": {
                "industry_terms": [],
                "products": [],
                "topics": [],
                "hashtags": [],
                "brands": [],
                "audience": [],
                "synonyms": {},
                "all_terms": [],
            },
            "corpus": sample_posts[:60],
            "_fallback": str(e),
        }
