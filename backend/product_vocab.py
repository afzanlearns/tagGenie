"""Product vocabulary extraction — parses the product string into structured components.

Heuristic-based (no LLM). Extracts product family, model, edition,
variant, manufacturer, aliases, and abbreviations from the raw product name.
"""

import re


def extract_product_vocab(product: str, topic: str = "") -> dict:
    words = product.split()
    lower = product.lower()

    out = {
        "raw": product,
        "lower": lower,
        "words": words,
        "family": "",
        "model": "",
        "edition": "",
        "variant": "",
        "aliases": [],
        "abbrevs": [],
        "all_terms": set(),
    }

    _add(out, product)
    _add(out, lower)

    # Aliases: acronym from words
    if len(words) >= 2:
        acro = "".join(w[0] for w in words if w).lower()
        if 2 <= len(acro) <= 5:
            out["abbrevs"].append(acro)
            _add(out, acro)
            if not out.get("family"):
                out["family"] = words[0]

    # Detect patterns
    _detect_collection_edition(out, product, lower, words)
    _detect_generational(out, lower, words)
    _detect_manufacturer(out, lower, words, topic)
    _detect_known_patterns(out, lower, words)

    # Simple word-level aliases (remove stopwords, add key nouns)
    stopwords = {"the", "a", "an", "of", "for", "in", "and", "with", "to", "&"}
    for w in words:
        wl = w.lower().strip(".,!?;:'\"")
        if wl not in stopwords and len(wl) > 1:
            out["abbrevs"].append(wl)
            out["all_terms"].add(wl)

    if not out.get("family") and words:
        out["family"] = words[0]

    out["aliases"] = list(dict.fromkeys(out["aliases"]))
    out["abbrevs"] = list(dict.fromkeys(out["abbrevs"]))
    return out


def _add(out: dict, term: str):
    t = term.strip().lower()
    if t:
        out["all_terms"].add(t)


def _detect_collection_edition(out: dict, product: str, lower: str, words: list):
    edition_keywords = [
        "booster", "box", "set", "collection", "pack", "edition", "series",
        "volume", "version", "gen", "drop", "release", "bundle", "kit",
        "expansion", "starter", "deluxe", "premium", "limited", "special",
        "booster box", "booster pack", "etb", "elite trainer",
    ]
    for kw in edition_keywords:
        if kw in lower:
            out["edition"] = kw
            # extract phrase containing the edition word
            for phrase_len in (2, 3):
                for i in range(len(words) - phrase_len + 1):
                    phrase = " ".join(words[i:i+phrase_len]).lower()
                    if kw in phrase:
                        out["aliases"].append(phrase)
            break


def _detect_generational(out: dict, lower: str, words: list):
    gen_patterns = [
        (r'\b\d+[a-z]{0,2}\s*(?:pro|max|ultra|plus|mini|air|lite|s|se)?\b', "model"),
        (r'\b(?:series\s+)?\d{1,2}\b', "generation"),
        (r'\b(?:gen\s+)?\d{1,2}\b', "generation"),
        (r'\b(?:scarlet|violet|crimson|teal|indigo|mask|sword|shield|sun|moon|xy|black|white|red|blue|green|gold|silver|ruby|sapphire|diamond|pearl|platinum|heartgold|soulsilver|omega|alpha|x|y)\b', "generation"),
    ]
    for pat, key in gen_patterns:
        m = re.search(pat, lower)
        if m:
            val = m.group(0).strip()
            if val and not out.get(key):
                out[key] = val
                out["aliases"].append(val)


def _detect_manufacturer(out: dict, lower: str, words: list, topic: str = ""):
    known_brands = [
        "apple", "samsung", "google", "microsoft", "sony", "nintendo",
        "nvidia", "amd", "intel", "tesla", "pokemon", "disney", "adobe",
        "lego", "dji", "canon", "nikon", "bose", "dyson", "rolex",
        "gucci", "prada", "nike", "adidas", "loreal", "neutrogena",
        "cerave", "the ordinary", "estee lauder", "clinique",
    ]
    lower_topic = topic.lower()
    for brand in known_brands:
        if brand in lower or brand in lower_topic:
            out["manufacturer"] = brand
            out["aliases"].append(brand)
            break

    # Also try first word as manufacturer if it looks like a company
    if not out.get("manufacturer") and words:
        first = words[0].lower()
        if first[0].isupper() and len(first) > 1:
            pass


def _detect_known_patterns(out: dict, lower: str, words: list):
    if "booster box" in lower or "booster pack" in lower:
        out["aliases"].append("booster")
        out["aliases"].append("sealed")

    if "serum" in lower:
        out["variant"] = "serum"
        out["aliases"].append("vitamin")

    if any(w in lower for w in ["gpu", "graphics", "rtx", "gtx", "rx"]):
        out["variant"] = "gpu"
        out["aliases"].extend(["graphics card", "gpu"])

    if any(w in lower for w in ["iphone", "ipad", "macbook", "airpods", "apple watch"]):
        out["manufacturer"] = "apple"

    if any(w in lower for w in ["galaxy", "samsung"]):
        out["manufacturer"] = "samsung"

    if "model" in lower.lower() or "cybertruck" in lower.lower() or "model y" in lower.lower():
        out["manufacturer"] = "tesla"
        out["variant"] = "ev"
        out["aliases"].extend(["ev", "electric vehicle"])
