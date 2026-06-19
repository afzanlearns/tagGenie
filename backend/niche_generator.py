"""LLM-powered niche generation: takes sample posts, returns draft corpus + jargon for user review."""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv(Path(__file__).parent / ".env")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def generate_niche_draft(niche_id: str, display_name: str, sample_posts: list[str]) -> dict:
    """Call Groq LLM to generate a draft niche config from sample posts.

    Returns a dict with:
    - seed_corpus: deduplicated, summarized list of posts
    - jargon: structured industry terms, abbreviations, trending concepts
    - sample_topics: suggested topic queries for this niche
    - description: auto-generated description
    """
    client = _get_client()

    posts_text = "\n".join(f"- {p}" for p in sample_posts[:50])

    max_corpus = min(60, len(sample_posts))

    prompt = (
        f"You are an industry analyst. Given {len(sample_posts)} sample social media posts "
        f"from the '{display_name}' industry (niche_id: '{niche_id}'), generate a structured "
        f"niche configuration. Return ONLY valid JSON, no markdown formatting.\n\n"
        f"Sample posts:\n{posts_text}\n\n"
        f"Return JSON with these exact keys:\n"
        f'1. "description" (string): A one-sentence description of this industry niche.\n'
        f'2. "sample_topics" (array of 5 strings): Topic queries someone in this niche would search for.\n'
        f'3. "jargon" (object): Industry-specific terminology organized as:\n'
        f'   - "industry_terms" (object with categories as keys, each category is an array of terms): '
        f'Categorize terms into groups like "products", "services", "stakeholders", "pain_points", "metrics". '
        f'Extract at least 20 total terms across categories.\n'
        f'   - "abbreviations" (object): Common industry abbreviations as key-value pairs (e.g., "API": "Application Programming Interface").\n'
        f'   - "adjacent_industries" (array of strings): Related industries.\n'
        f'   - "trending_concepts" (array of strings): Current trending topics in this space.\n'
        f'4. "corpus" (array of strings): A deduplicated, cleaned version of the sample posts. '
        f'Remove near-duplicates (keep the best version), fix typos, ensure each post is a complete sentence. '
        f"Output at most {max_corpus} posts. Keep the original meaning and specificity.\n\n"
        f"Return ONLY the JSON object. No explanation, no markdown."
    )

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=4000,
            timeout=30.0,
        )
        raw = resp.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if "```" in raw:
                raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()

        result = json.loads(raw)

        # Validate structure
        if "jargon" not in result:
            result["jargon"] = {"industry_terms": {}, "abbreviations": {}, "adjacent_industries": [], "trending_concepts": []}
        if "corpus" not in result or not isinstance(result["corpus"], list):
            result["corpus"] = sample_posts[:60]
        if "description" not in result:
            result["description"] = f"Auto-generated niche for {display_name}"
        if "sample_topics" not in result:
            result["sample_topics"] = sample_posts[:5]

        return result

    except (json.JSONDecodeError, Exception) as e:
        # Fallback to heuristic generation
        from backend.niche_manager import _auto_generate_jargon
        jargon = _auto_generate_jargon(niche_id, sample_posts)
        return {
            "description": f"Auto-generated niche for {display_name}",
            "sample_topics": sample_posts[:5],
            "jargon": jargon,
            "corpus": sample_posts[:60],
            "_fallback": str(e),
        }
