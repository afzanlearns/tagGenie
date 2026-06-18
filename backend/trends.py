import json
import numpy as np
from pathlib import Path
from pytrends.request import TrendReq

DATA_DIR = Path(__file__).parent.parent / "data"
_pytrends = None
_fallback_data = None


def _get_pytrends():
    global _pytrends
    if _pytrends is None:
        _pytrends = TrendReq(hl="en-US", tz=360, retries=2, backoff_factor=0.5)
    return _pytrends


def _load_fallback():
    global _fallback_data
    if _fallback_data is None:
        fp = DATA_DIR / "sample_topics.json"
        if fp.exists():
            with open(fp) as f:
                _fallback_data = json.load(f)
    return _fallback_data or []


def get_trend_volume(keyword: str) -> dict:
    try:
        pytrends = _get_pytrends()
        pytrends.build_payload([keyword], timeframe="today 3-m", geo="US")
        interest = pytrends.interest_over_time()
        if interest is not None and not interest.empty:
            vals = interest[keyword].values
            avg = float(np.mean(vals[vals > 0])) if np.any(vals > 0) else 0.0
            normalized = min(100.0, avg * 1.25)
            return {"volume": round(normalized, 1), "fallback_mode": False}
    except Exception:
        pass

    return _get_static_fallback(keyword)


def _get_static_fallback(keyword: str) -> dict:
    fallback = _load_fallback()
    kw_lower = keyword.lower()
    for entry in fallback:
        if entry["topic"].lower() in kw_lower or kw_lower in entry["topic"].lower():
            return {"volume": float(entry["momentum"]), "fallback_mode": True}
    return {"volume": round(np.random.uniform(30, 70), 1), "fallback_mode": True}


def normalize_score(raw: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    return round(max(min_val, min(max_val, raw)), 1)
