import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from backend.niche_manager import build_jargon_context, get_active_niche

load_dotenv(Path(__file__).parent / ".env")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def expand_topic(topic: str, product: str, niche_id: str = None) -> str:
    if niche_id is None:
        niche_id = get_active_niche()

    client = _get_client()
    jargon = build_jargon_context(niche_id)

    prompt = (
        f"You are an industry expert in the '{niche_id}' domain. "
        f"Expand the following topic with 5-8 related industry terms, jargon, synonyms, "
        f"and adjacent concepts specific to this industry.\n\n"
        f"Industry context — relevant terms and jargon:\n{jargon}\n\n"
        f"Topic: {topic}\nProduct: {product}\n\n"
        f"Return ONLY a natural paragraph of 3-5 sentences that includes the original topic "
        f"and weaves in the expanded terms contextually. Do not use bullet points or lists."
    )
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
            timeout=10.0,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return f"{topic} {product} {niche_id} industry terms trends best practices"


def generate_rationale(
    tag: str, reach_score: float, competition_score: float, final_score: float,
    niche_id: str = None
) -> str:
    if niche_id is None:
        niche_id = get_active_niche()

    client = _get_client()
    prompt = (
        f"Generate ONE sentence explaining why the tag '{tag}' ranks where it does "
        f"in the '{niche_id}' industry context. "
        f"Use ONLY these numbers:\n"
        f"- Reach score: {reach_score:.1f}/100\n"
        f"- Competition score: {competition_score:.1f}/100 (higher = more saturated)\n"
        f"- Final score: {final_score:.1f}/100\n\n"
        f"Ground the sentence in these actual values. Do not invent claims beyond them. "
        f"If reach is high and competition low, say it's an underused term. "
        f"If competition is high, say the space is crowded. Keep it to one sentence."
    )
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=120,
            timeout=10.0,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        if competition_score < 30 and reach_score > 60:
            return f"High reach ({reach_score:.0f}) with low saturation ({competition_score:.0f}) — an underused term in {niche_id} right now."
        elif competition_score > 70:
            return f"Reach of {reach_score:.0f} but high competition ({competition_score:.0f}) — a crowded space in this niche."
        else:
            return f"Balanced reach ({reach_score:.0f}) and competition ({competition_score:.0f}) yielding final score of {final_score:.0f}."


def batch_generate_rationales(
    tags: list[dict], niche_id: str = None
) -> list[str]:
    """Generate rationales for multiple tags in a single LLM call.

    Each dict in `tags` should have keys: tag, reach_score, competition_score, final_score.
    Returns a list of rationale strings in the same order.
    """
    if niche_id is None:
        niche_id = get_active_niche()

    tag_block = "\n".join(
        f"  {i+1}. tag='{t['tag']}' reach={t['reach_score']:.1f} comp={t['competition_score']:.1f} final={t['final_score']:.1f}"
        for i, t in enumerate(tags)
    )

    client = _get_client()
    prompt = (
        f"Given the following {len(tags)} scored tags in the '{niche_id}' industry, "
        f"generate a ONE-SENTENCE rationale for EACH tag explaining why it ranks where it does. "
        f"Numbers: reach=reach/trend score, comp=competition/saturation, final=composite.\n\n"
        f"Rules:\n"
        f"- If reach is high and comp low (blue ocean), say it's an underused opportunity.\n"
        f"- If comp is high, say the space is crowded.\n"
        f"- Ground each rationale in the actual numbers provided.\n"
        f"- Keep each rationale to one sentence.\n"
        f"- Do not add disclaimers like 'based on the numbers'.\n\n"
        f"Tags:\n{tag_block}\n\n"
        f"Return ONLY a numbered list:\n1. [rationale for tag 1]\n2. [rationale for tag 2]\n..."
    )
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=800,
            timeout=15.0,
        )
        raw = resp.choices[0].message.content.strip()
        lines = [l.strip() for l in raw.split("\n") if l.strip()]
        results = []
        for l in lines:
            l = l.lstrip("0123456789. )-")
            if l:
                results.append(l)
        if len(results) >= len(tags):
            return results[:len(tags)]
        return results + [generate_rationale(t["tag"], t["reach_score"], t["competition_score"], t["final_score"], niche_id) for t in tags[len(results):]]
    except Exception:
        return [
            f"Reach: {t['reach_score']:.0f}, Competition: {t['competition_score']:.0f}"
            for t in tags
        ]
