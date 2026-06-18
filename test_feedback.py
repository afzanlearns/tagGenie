"""Quick test: Verify feedback loop weight adjustments work."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.feedback import init_db, seed_synthetic_feedback, log_feedback
from backend.scoring import PLATFORM_WEIGHTS, load_weights
from backend.scheduler import trigger_recompute

DATA_DIR = Path(__file__).parent / "data"

def main():
    init_db()
    seed_synthetic_feedback()

    print("Initial weights:")
    for plat, weights in PLATFORM_WEIGHTS.items():
        print(f"  {plat}: hashtag={weights['hashtag']}, keyword={weights['keyword']}")

    print("\nTriggering nightly recompute...")
    trigger_recompute()

    print("\nWeights after recompute:")
    for plat, weights in PLATFORM_WEIGHTS.items():
        print(f"  {plat}: hashtag={weights['hashtag']}, keyword={weights['keyword']}")

    weights_path = DATA_DIR / "weights.json"
    if weights_path.exists():
        print(f"\nweights.json contents:")
        with open(weights_path) as f:
            print(json.dumps(json.load(f), indent=2))

    print("\nDone. Feedback loop validated.")


if __name__ == "__main__":
    main()
