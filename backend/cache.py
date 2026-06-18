import time
import hashlib
import json

_cache = {}


def cache_key(topic: str, platform: str) -> str:
    raw = json.dumps({"topic": topic.strip().lower(), "platform": platform})
    return hashlib.sha256(raw.encode()).hexdigest()


def get(key: str):
    entry = _cache.get(key)
    if entry is None:
        return None
    if time.time() - entry["ts"] > 600:
        del _cache[key]
        return None
    return entry["data"]


def set(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}


def clear():
    _cache.clear()


def size() -> int:
    now = time.time()
    expired = [k for k, v in _cache.items() if now - v["ts"] > 600]
    for k in expired:
        del _cache[k]
    return len(_cache)
