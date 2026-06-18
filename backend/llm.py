import os
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


def expand_topic(topic: str, product: str) -> str:
    client = _get_client()
    prompt = (
        f"You are a fleet-tech and telematics industry expert. "
        f"Expand the following topic with 5-8 related industry terms, jargon, synonyms, "
        f"and adjacent concepts specific to fleet technology, telematics, dashcams, and logistics.\n\n"
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
        return f"{topic} {product} fleet technology telematics dashcam safety logistics predictive maintenance real-time monitoring"


def generate_rationale(
    tag: str, reach_score: float, competition_score: float, final_score: float
) -> str:
    client = _get_client()
    prompt = (
        f"Generate ONE sentence explaining why the tag '{tag}' ranks where it does. "
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
            return f"High reach ({reach_score:.0f}) with low saturation ({competition_score:.0f}) — an underused term in this niche right now."
        elif competition_score > 70:
            return f"Reach of {reach_score:.0f} but high competition ({competition_score:.0f}) — a crowded space where differentiation is difficult."
        else:
            return f"Balanced reach ({reach_score:.0f}) and competition ({competition_score:.0f}) yielding final score of {final_score:.0f}."
