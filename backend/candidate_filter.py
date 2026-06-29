import re
import spacy
import numpy as np
from sentence_transformers import SentenceTransformer

_nlp = None
_sim_model = None

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "not",
    "no", "nor", "so", "if", "than", "that", "this", "these", "those",
    "it", "its", "over", "under", "between", "through", "during", "before",
    "after", "above", "below", "about", "into", "more", "some", "such",
    "also", "very", "just", "because", "their", "them", "they", "which",
    "when", "where", "how", "what", "who", "whom", "both", "each", "few",
    "most", "other", "up", "down", "out", "off", "all", "any", "every",
    "our", "your", "his", "her", "my", "me", "we", "us", "our", "get",
    "got", "use", "used", "using", "make", "made", "making", "take",
    "took", "taken", "taking", "need", "needs", "needed", "new", "one",
    "two", "like", "just", "really", "much", "many", "still", "even",
    "way", "things", "thing", "think", "going", "go", "goes", "went",
    "come", "came", "coming", "know", "knows", "known", "see", "seen",
    "say", "said", "says", "find", "finds", "found", "tell", "tells",
    "told", "look", "looks", "looked", "try", "tries", "tried", "ask",
    "asks", "asked", "seem", "seems", "seemed", "want", "wants", "wanted",
    "give", "gives", "gave", "given", "work", "works", "worked",
    "call", "calls", "called", "keep", "keeps", "kept", "let", "lets",
    "begin", "begins", "began", "begun", "show", "shows", "showed",
    "hear", "hears", "heard", "play", "plays", "played", "run", "runs",
    "ran", "move", "moves", "moved", "live", "lives", "lived",
    "believe", "believes", "believed", "hold", "holds", "held",
    "bring", "brings", "brought", "happen", "happens", "happened",
    "write", "writes", "wrote", "written", "provide", "provides",
    "provided", "sit", "sits", "sat", "stand", "stands", "stood",
    "lose", "loses", "lost", "pay", "pays", "paid", "meet", "meets",
    "met", "include", "includes", "included", "continue", "continues",
    "continued", "set", "sets", "setting", "learn", "learns", "learned",
    "change", "changes", "changed", "lead", "leads", "led",
    "increase", "increases", "increased", "decrease", "decreases",
    "decreased", "create", "creates", "created", "help", "helps",
    "helped", "talk", "talks", "talked", "start", "starts", "started",
    "rise", "rises", "rose", "risen", "fall", "falls", "fell", "fallen",
    "affect", "affects", "affected", "grow", "grows", "grew", "grown",
    "drive", "drives", "drove", "driven", "become", "becomes", "became",
    "remain", "remains", "remained", "add", "adds", "added",
    "allow", "allows", "allowed", "expect", "expects", "expected",
    "follow", "follows", "followed", "form", "forms", "formed",
    "produce", "produces", "produced", "turn", "turns", "turned",
    "consider", "considers", "considered", "appear", "appears", "appeared",
    "cause", "causes", "caused", "define", "defines", "defined",
    "develop", "develops", "developed", "reach", "reaches", "reached",
}


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _get_sim_model():
    global _sim_model
    if _sim_model is None:
        _sim_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sim_model


def semantic_confidence(term: str, topic: str, product: str) -> float:
    model = _get_sim_model()
    combined_query = f"{topic} {product}"
    emb_term = model.encode([term])
    emb_query = model.encode([combined_query])
    sim = float(np.dot(emb_term, emb_query.T)[0][0])
    return round(min(100.0, max(0.0, sim * 100.0)), 1)


def is_sentence_fragment(text: str, doc=None) -> bool:
    if doc is None:
        nlp = _get_nlp()
        doc = nlp(text.lower())

    has_noun = any(token.pos_ == "NOUN" for token in doc)
    if not has_noun:
        return True

    if doc[0].pos_ == "VERB" and doc[0].tag_ not in ("VBG", "VBN"):
        return True

    root_verbs = [token for token in doc if token.dep_ == "ROOT" and token.pos_ == "VERB"]
    has_dobj = any(token.dep_ == "dobj" for token in doc)
    if root_verbs and not has_dobj:
        return True

    return False


def starts_with_verb(text: str) -> bool:
    nlp = _get_nlp()
    doc = nlp(text.lower().strip())
    if not doc:
        return False
    return doc[0].pos_ == "VERB"


def contains_stopwords_only(text: str) -> bool:
    words = text.lower().split()
    non_stop = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return len(non_stop) == 0


def has_punctuation(text: str) -> bool:
    return bool(re.search(r'[^\w\s-]', text))


FRAGMENT_INDICATORS = {"why", "how", "what", "when", "where", "which", "who", "whom"}
ARTICLES = {"the", "a", "an"}
KNOWN_ACRONYMS = {"psa", "api", "ai", "ml", "saas", "tcg", "rpg", "mmo", "rpa",
                  "iot", "ui", "ux", "seo", "ppc", "crm", "erp", "hr", "pr",
                  "b2b", "b2c", "d2c", "kpi", "roi", "cta", "vpn", "dns",
                  "ssl", "html", "css", "js", "sql", "nosql", "aws", "gcp"}
PREPOSITIONS = {"of", "in", "on", "at", "to", "for", "with", "by", "from", "about", "into", "through", "during", "before", "after", "above", "below", "between", "under", "over", "without", "against", "within", "along", "among"}


def is_valid_candidate(term: str, topic: str = "", product: str = "",
                       min_confidence: float = 35.0) -> bool:
    term = term.strip()
    if not term or len(term) < 3:
        return False

    word_count = len(term.split())
    if word_count > 4:
        return False

    if contains_stopwords_only(term):
        return False

    if has_punctuation(term):
        return False

    nlp = _get_nlp()
    doc = nlp(term.lower())

    words = [token.text for token in doc]
    pos_tags = [token.pos_ for token in doc]
    tag_codes = [token.tag_ for token in doc]
    deps = [token.dep_ for token in doc]

    if any(w in FRAGMENT_INDICATORS for w in words):
        return False

    if words[0] in ARTICLES:
        return False

    if len(words) >= 3 and words[1] == "of":
        generic_nouns = {"rise", "fall", "use", "need", "way", "role", "impact", "effect",
                         "future", "growth", "decline", "change", "increase", "decrease",
                         "state", "type", "kind", "form", "part", "set", "lack", "absence"}
        if words[0] in generic_nouns:
            return False

    if len(words) >= 2 and words[-1] in PREPOSITIONS:
        return False

    if len(words) == 3 and pos_tags == ["NOUN", "VERB", "NOUN"] and tag_codes[1] == "VBG":
        return False

    if len(words) >= 2 and pos_tags[-1] == "ADJ" and pos_tags[0] == "VERB":
        return False

    has_finite_verb = any(t in ("VBP", "VBZ", "VBD") for t in tag_codes)
    if has_finite_verb and len(words) >= 2:
        return False

    if pos_tags[0] == "VERB" and tag_codes[0] not in ("VBG", "VBN"):
        return False

    if pos_tags[0] == "AUX" and len(words) >= 1:
        if not (len(words) >= 2 and tag_codes[-1] in ("VBG", "VBN")):
            return False

    has_noun = any(token.pos_ in ("NOUN", "PROPN") for token in doc)
    has_acronym = any(w.lower() in KNOWN_ACRONYMS for w in words)
    if not has_noun and not has_acronym:
        return False

    if topic or product:
        conf = semantic_confidence(term, topic, product)
        if conf < min_confidence:
            return False

    return True


def filter_candidates(candidates: list[str], topic: str = "", product: str = "",
                      min_confidence: float = 35.0) -> list[str]:
    seen = set()
    result = []
    for term in candidates:
        cleaned = term.strip().lower()
        if cleaned in seen:
            continue
        if is_valid_candidate(cleaned, topic, product, min_confidence):
            seen.add(cleaned)
            result.append(cleaned)
    return result


def normalize_term(term: str) -> str:
    term = term.strip()
    term = re.sub(r'\s+', ' ', term)
    words = term.split()
    if len(words) >= 2:
        return " ".join(w.capitalize() if i == 0 or not w.isupper() else w
                       for i, w in enumerate(words))
    return term.capitalize()
