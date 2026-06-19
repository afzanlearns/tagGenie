"""Nightly weight recompute using Thompson Sampling.

Thompson Sampling models each platform/tag-type weight as a Beta distribution.
Alpha/beta parameters are updated based on whether engagement outperformed or
underperformed the platform's rolling average. The live weight is sampled from
the distribution — more data = more confident = more concentrated samples.

The old ±10% heuristic is preserved as `_heuristic_recompute` for comparison.
"""

import json
import random
import math
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from backend import feedback
from backend import scoring

DATA_DIR = Path(__file__).parent.parent / "data"
BETA_FILE = DATA_DIR / "beta_params.json"

_scheduler = None

# Default Beta parameters: Beta(alpha=2, beta=2) is uniform-ish on [0,1]
# We scale the sampled value to [0.1, 2.0] range.
_DEFAULT_ALPHA = 2.0
_DEFAULT_BETA = 2.0

# Platform tag-type combos tracked for Beta distributions
PLATFORM_TAG_TYPES = [
    ("LinkedIn", "hashtag"),
    ("LinkedIn", "keyword"),
    ("Instagram", "hashtag"),
    ("Instagram", "keyword"),
    ("X", "hashtag"),
    ("X", "keyword"),
    ("TikTok", "hashtag"),
    ("TikTok", "keyword"),
]


def _load_beta_params() -> dict:
    """Load Beta distribution parameters from disk."""
    if BETA_FILE.exists():
        with open(BETA_FILE) as f:
            return json.load(f)
    return {}


def _save_beta_params(params: dict):
    """Save Beta distribution parameters to disk."""
    with open(BETA_FILE, "w") as f:
        json.dump(params, f, indent=2)


def _get_beta_key(platform: str, tag_type: str) -> str:
    return f"{platform}:{tag_type}"


def _get_beta(key: str, beta_params: dict) -> tuple:
    """Get (alpha, beta) for a key, defaulting if not present."""
    entry = beta_params.get(key, {"alpha": _DEFAULT_ALPHA, "beta": _DEFAULT_BETA})
    return entry["alpha"], entry["beta"]


def _sample_from_beta(alpha: float, beta: float) -> float:
    """Sample from a Beta distribution using random.betavariate."""
    try:
        return random.betavariate(alpha, beta)
    except (ValueError, ZeroDivisionError):
        return 0.5  # Fallback to midpoint


def _thompson_recompute():
    """Nightly job using Thompson Sampling for principled weight learning.

    For each platform/tag-type combination:
    1. Get tag engagement data from the feedback DB
    2. For each tag, compare its normalized engagement to the platform average
    3. If the tag outperformed, reward it (alpha++). If underperformed, penalize (beta++)
    4. Sample from the updated Beta distribution to set the live weight
    5. Scale the [0,1] sample to [0.1, 2.0] range
    """
    beta_params = _load_beta_params()

    for platform in ["LinkedIn", "Instagram", "X", "TikTok"]:
        stats = feedback.get_platform_stats(platform)
        if stats["post_count"] == 0:
            continue

        avg_eng = stats["avg_engagement"]

        # Track updates per tag-type for this platform
        type_updates = {"hashtag": {"alpha": 0, "beta": 0}, "keyword": {"alpha": 0, "beta": 0}}

        for tag, data in stats["tag_engagement"].items():
            tag_avg = data["engagement"] / max(1, data["count"])
            delta = tag_avg / max(1, avg_eng)

            # Determine if this is a hashtag or keyword by length heuristic
            tag_type = "hashtag" if len(tag.split()) <= 2 else "keyword"

            if delta > 1.1:
                type_updates[tag_type]["alpha"] += data["count"]
            elif delta < 0.9:
                type_updates[tag_type]["beta"] += data["count"]
            else:
                # Near average: slight positive reinforcement
                type_updates[tag_type]["alpha"] += max(1, data["count"] // 2)

        # Update Beta distributions and sample new weights
        for tag_type in ["hashtag", "keyword"]:
            key = _get_beta_key(platform, tag_type)
            old_alpha, old_beta = _get_beta(key, beta_params)

            new_alpha = old_alpha + max(0, type_updates[tag_type]["alpha"])
            new_beta = old_beta + max(0, type_updates[tag_type]["beta"])

            beta_params[key] = {"alpha": new_alpha, "beta": new_beta}

            # Sample from the posterior distribution
            sampled = _sample_from_beta(new_alpha, new_beta)

            # Scale from [0, 1] to [0.1, 2.0]
            scaled_weight = round(0.1 + sampled * 1.9, 2)

            # Update the running weights
            old = scoring.PLATFORM_WEIGHTS[platform][tag_type]
            # Blend old and new for smoothness (70% new, 30% old)
            blended = round(old * 0.3 + scaled_weight * 0.7, 2)
            blended = max(0.1, min(2.0, blended))
            scoring.PLATFORM_WEIGHTS[platform][tag_type] = blended

    _save_beta_params(beta_params)
    scoring.save_weights()


def _heuristic_recompute():
    """Original ±10% heuristic — kept for side-by-side comparison.

    This is the Phase 2 approach: flat ±10% adjustment with no uncertainty
    modeling. It's preserved here for A/B comparison but not called by default.
    """
    for platform in ["LinkedIn", "Instagram", "X", "TikTok"]:
        stats = feedback.get_platform_stats(platform)
        if stats["post_count"] == 0:
            continue

        avg_eng = stats["avg_engagement"]
        for tag, data in stats["tag_engagement"].items():
            tag_avg = data["engagement"] / max(1, data["count"])
            delta = tag_avg / max(1, avg_eng)

            if delta > 1.2:
                factor = 1.1
            elif delta < 0.8:
                factor = 0.9
            else:
                continue

            for wtype in ["hashtag", "keyword"]:
                old = scoring.PLATFORM_WEIGHTS[platform][wtype]
                new = round(max(0.1, min(2.0, old * factor)), 2)
                scoring.PLATFORM_WEIGHTS[platform][wtype] = new

    scoring.save_weights()


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_thompson_recompute, "cron", hour=2, minute=0)
    _scheduler.start()


def shutdown_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None


def trigger_recompute():
    _thompson_recompute()


def get_beta_summary() -> dict:
    """Return current Beta distribution parameters for inspection."""
    return _load_beta_params()
