import json
import time
from copy import deepcopy

_GUEST_NICHES: dict[str, list[dict]] = {}
_GUEST_FEEDBACK: dict[str, list[dict]] = {}
_GUEST_WEIGHTS: dict[str, dict] = {}
_GUEST_BETA_PARAMS: dict[str, dict] = {}
_GUEST_ACTIVE_NICHE: dict[str, str] = {}

DEFAULT_NICHES_CACHE = None


def _get_default_niches():
    global DEFAULT_NICHES_CACHE
    if DEFAULT_NICHES_CACHE is not None:
        return DEFAULT_NICHES_CACHE
    from backend.niche_manager import get_available_niches as _get_global_niches
    DEFAULT_NICHES_CACHE = _get_global_niches()
    return DEFAULT_NICHES_CACHE


def guest_id(session: str) -> str:
    return f"guest_{session}"


def init_guest_session(session: str) -> str:
    gid = guest_id(session)
    _GUEST_NICHES[gid] = deepcopy(_get_default_niches())
    _GUEST_WEIGHTS[gid] = {
        "LinkedIn": {"hashtag": 0.3, "keyword": 1.0},
        "Instagram": {"hashtag": 1.0, "keyword": 0.4},
        "X": {"hashtag": 0.7, "keyword": 0.6},
        "TikTok": {"hashtag": 0.9, "keyword": 0.5},
    }
    _GUEST_BETA_PARAMS[gid] = {}
    _GUEST_FEEDBACK[gid] = []
    _GUEST_ACTIVE_NICHE[gid] = "gps-telematics"
    return gid


def cleanup_guest_session(session: str):
    gid = guest_id(session)
    _GUEST_NICHES.pop(gid, None)
    _GUEST_FEEDBACK.pop(gid, None)
    _GUEST_WEIGHTS.pop(gid, None)
    _GUEST_BETA_PARAMS.pop(gid, None)
    _GUEST_ACTIVE_NICHE.pop(gid, None)


def is_guest(gid: str) -> bool:
    return gid.startswith("guest_")


def get_available_niches(gid: str) -> list[dict]:
    return _GUEST_NICHES.get(gid, deepcopy(_get_default_niches()))


def get_niche_config(gid: str, niche_id: str):
    for n in get_available_niches(gid):
        if n["niche_id"] == niche_id:
            return n
    return None


def set_active_niche(gid: str, niche_id: str) -> bool:
    if get_niche_config(gid, niche_id) is not None:
        _GUEST_ACTIVE_NICHE[gid] = niche_id
        return True
    return False


def get_active_niche(gid: str) -> str:
    return _GUEST_ACTIVE_NICHE.get(gid, "gps-telematics")


def add_custom_niche(gid: str, config: dict, corpus: list[str] = None,
                     jargon: dict = None, profile: dict = None):
    niches = _GUEST_NICHES.setdefault(gid, deepcopy(_get_default_niches()))
    if corpus is not None:
        config["_corpus"] = corpus
    if jargon is not None:
        config["_jargon"] = jargon
    if profile is not None:
        config["_profile"] = profile
    niches.append(config)


def get_niche_profile(gid: str, niche_id: str) -> dict:
    for n in get_available_niches(gid):
        if n["niche_id"] == niche_id and "_profile" in n:
            return n["_profile"]
    return {
        "industry_terms": [], "products": [], "topics": [],
        "hashtags": [], "brands": [], "audience": [],
        "synonyms": {}, "all_terms": [],
    }


def get_niche_data(gid: str, niche_id: str):
    for n in get_available_niches(gid):
        if n["niche_id"] == niche_id:
            return n
    return None


def get_seed_corpus(gid: str, niche_id: str) -> list[str]:
    data = get_niche_data(gid, niche_id)
    if data and data.get("_corpus"):
        return data["_corpus"]
    from backend.niche_manager import get_seed_corpus as _get_global_corpus
    return _get_global_corpus(niche_id)


def get_jargon(gid: str, niche_id: str) -> dict:
    data = get_niche_data(gid, niche_id)
    if data and data.get("_jargon"):
        return data["_jargon"]
    from backend.niche_manager import get_jargon as _get_global_jargon
    return _get_global_jargon(niche_id)


def get_weights(gid: str) -> dict:
    return _GUEST_WEIGHTS.get(gid, {
        "LinkedIn": {"hashtag": 0.3, "keyword": 1.0},
        "Instagram": {"hashtag": 1.0, "keyword": 0.4},
        "X": {"hashtag": 0.7, "keyword": 0.6},
        "TikTok": {"hashtag": 0.9, "keyword": 0.5},
    })


def save_weights(gid: str, weights: dict):
    _GUEST_WEIGHTS[gid] = weights


def get_beta_params(gid: str) -> dict:
    return _GUEST_BETA_PARAMS.get(gid, {})


def save_beta_params(gid: str, params: dict):
    _GUEST_BETA_PARAMS[gid] = params


def log_feedback(gid: str, record: dict):
    _GUEST_FEEDBACK.setdefault(gid, []).append(record)


def get_feedback(gid: str) -> list[dict]:
    return _GUEST_FEEDBACK.get(gid, [])
