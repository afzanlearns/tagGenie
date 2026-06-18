"""Phase 2 CLI validation: Test the extraction + scoring engine
against 5 sample fleet-tech topics before building the UI."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.scoring import score_topic
from backend.feedback import init_db, seed_synthetic_feedback

TEST_TOPICS = [
    {
        "topic": "AI dashcams for fleet safety",
        "product": "Vignan Dashcam AI",
        "platform": "LinkedIn",
    },
    {
        "topic": "real-time GPS telematics for last-mile delivery",
        "product": "AjnaView GPS Suite",
        "platform": "Instagram",
    },
    {
        "topic": "predictive maintenance for commercial fleets",
        "product": "FleetPredict Pro",
        "platform": "X",
    },
    {
        "topic": "driver behavior monitoring with computer vision",
        "product": "DashCam Vision AI",
        "platform": "TikTok",
    },
    {
        "topic": "fleet electrification and sustainability",
        "product": "GreenFleet EV",
        "platform": "LinkedIn",
    },
]


def main():
    init_db()
    seed_synthetic_feedback()

    for i, test in enumerate(TEST_TOPICS, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}: {test['topic']}")
        print(f"  Product: {test['product']}")
        print(f"  Platform: {test['platform']}")
        print(f"{'='*70}")

        result = score_topic(**test)

        print(f"\nConfidence: {result.confidence:.0f}%")
        print(f"Fallback Mode: {result.fallback_mode}")
        print(f"Gap Tags (Blue Ocean): {len(result.gap_tags)}")
        if result.gap_tags:
            for gt in result.gap_tags:
                print(f"  -> {gt.tag} (reach={gt.reach_score:.0f}, comp={gt.competition_score:.0f}): {gt.reason}")

        print(f"\nRanked Tags:")
        for rank, rt in enumerate(result.ranked_tags, 1):
            print(f"  {rank:2d}. [{rt.type:>8s}] {rt.tag:<35s} "
                  f"final={rt.final_score:6.1f} reach={rt.reach_score:5.1f} "
                  f"comp={rt.competition_score:5.1f}")
            if rt.rationale:
                print(f"       {rt.rationale}")

    print("\n\nDone. All 5 topics scored and ranked.")


if __name__ == "__main__":
    main()
