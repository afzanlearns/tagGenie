"""Cross-niche ranking divergence check.
Scores the same topic through all 3 niches and compares the results side-by-side.

Usage:
    python -m evaluation.niche_divergence_check
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.scoring import score_topic
from backend.niche_manager import get_available_niches
from backend.embeddings import seed_corpus


def main():
    topics = [
        "AI-powered customer analytics",
        "real-time data dashboards",
        "mobile app user engagement",
    ]

    niches = [n["niche_id"] for n in get_available_niches()]
    product = "TagGenie Pro"
    platform = "LinkedIn"

    for topic in topics:
        print(f"\n{'='*80}")
        print(f"TOPIC: \"{topic}\"  |  Platform: {platform}")
        print(f"{'='*80}")

        all_results = {}
        for niche_id in niches:
            seed_corpus(niche_id)
            result = score_topic(topic, product, platform, niche_id)
            all_results[niche_id] = result

        print(f"{'Tag':30s}", end="")
        for n in niches:
            print(f"{n:>22s}", end="")
        print()

        print(f"{'-'*30}", end="")
        for _ in niches:
            print(f"{'-'*22}", end="")
        print()

        all_tag_map = {}
        for n in niches:
            for t in all_results[n].ranked_tags:
                all_tag_map.setdefault(t.tag, {})[n] = t.final_score

        rank = 1
        for tag, scores in sorted(all_tag_map.items(),
                                  key=lambda x: max(x[1].values()), reverse=True)[:15]:
            print(f"{tag:30s}", end="")
            for n in niches:
                s = scores.get(n, None)
                if s is not None:
                    print(f"{s:>22.1f}", end="")
                else:
                    print(f"{'—':>22}", end="")
            print(f"  (rank ~{rank})")
            rank += 1

        for niche_id in niches:
            r = all_results[niche_id]
            gap_tags = [g.tag for g in r.gap_tags]
            print(f"\n  [{niche_id}] Blue ocean gaps ({len(gap_tags)}): {', '.join(gap_tags[:5])}")
            print(f"  [{niche_id}] Top tag: {r.ranked_tags[0].tag} ({r.ranked_tags[0].final_score:.1f})")
            print(f"  [{niche_id}] Confidence: {r.confidence}% | Fallback: {r.fallback_mode}")


if __name__ == "__main__":
    main()
