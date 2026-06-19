"""Evaluation harness: backtest TagGenie against held-out data.

Compares TagGenie's ranked tags against a naive TF-IDF baseline,
computing precision@5 and precision@10. Outputs comparison report.

Usage:
    python -m evaluation.backtest
    python -m evaluation.backtest --niche gps-telematics
"""

import sys
import json
import random
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from backend.scoring import score_topic
from backend.baseline import score_baseline
from backend.niche_manager import get_available_niches, get_seed_corpus
from backend.reddit_ingest import build_held_out_dataset


def compute_precision(
    ranked_tags: list[dict],
    ground_truth: set[str],
    k: int = 5,
) -> float:
    """Compute precision@k: fraction of top-k tags that appear in ground truth."""
    top_k = ranked_tags[:k]
    if not top_k:
        return 0.0
    relevant = sum(1 for t in top_k if t["tag"] in ground_truth)
    return relevant / k


def extract_ground_truth_tags(title: str, text: str) -> set[str]:
    """Extract ground truth tags from a post's content using simple heuristics.

    This is a proxy — in a production system, ground truth would come from
    actual tags used on the post that drove engagement.
    """
    combined = f"{title} {text}".lower()
    # Use KeyBERT to extract key terms
    try:
        from keybert import KeyBERT
        kw_model = KeyBERT()
        keywords = kw_model.extract_keywords(
            combined,
            keyphrase_ngram_range=(1, 3),
            stop_words="english",
            top_n=15,
            use_mmr=True,
            diversity=0.4,
        )
        return {kw for kw, _ in keywords if len(kw) > 2}
    except Exception:
        # Fallback: extract meaningful words
        words = set()
        for w in combined.split():
            cleaned = w.strip(",.!?;:#()[]").lower()
            if len(cleaned) > 3 and cleaned not in {"this", "that", "with", "from", "have", "been", "what", "which", "their"}:
                words.add(cleaned)
        return words


def backtest_niche(
    niche_id: str,
    num_test_posts: int = 20,
    held_out_data: list[dict] = None,
) -> dict:
    """Run backtest evaluation for a single niche.

    Returns metrics comparing TagGenie vs baseline performance.
    """
    if held_out_data is None:
        held_out_data = build_held_out_dataset(niche_id, num_test_posts)

    if not held_out_data:
        return {
            "niche": niche_id,
            "error": "No held-out data available",
            "precision_at_5": 0.0,
            "precision_at_10": 0.0,
            "baseline_precision_at_5": 0.0,
            "baseline_precision_at_10": 0.0,
            "lift_at_5": 0.0,
            "lift_at_10": 0.0,
            "num_posts": 0,
        }

    tg_precisions_5 = []
    tg_precisions_10 = []
    bl_precisions_5 = []
    bl_precisions_10 = []

    platforms = ["LinkedIn", "Instagram", "X", "TikTok"]

    for post in held_out_data:
        title = post.get("title", "")
        text = post.get("text", "")
        ground_truth = extract_ground_truth_tags(title, text)

        if not ground_truth:
            continue

        # Use a generic product name based on the niche
        product_map = {
            "gps-telematics": "FleetTracker Pro",
            "b2b-saas": "SaaSPlatform Enterprise",
            "fintech": "FinPay Solutions",
        }
        product = product_map.get(niche_id, "TagGenie Pro")
        platform = random.choice(platforms)

        try:
            # TagGenie scoring
            tg_result = score_topic(title, product, platform, niche_id)
            tg_tags = [
                {"tag": t.tag, "score": t.final_score}
                for t in tg_result.ranked_tags
            ]

            # Baseline scoring
            bl_tags = score_baseline(title, product, niche_id)
        except Exception as e:
            print(f"  Error scoring post '{title[:50]}...': {e}")
            continue

        tg_p5 = compute_precision(tg_tags, ground_truth, 5)
        tg_p10 = compute_precision(tg_tags, ground_truth, 10)
        bl_p5 = compute_precision(bl_tags, ground_truth, 5)
        bl_p10 = compute_precision(bl_tags, ground_truth, 10)

        tg_precisions_5.append(tg_p5)
        tg_precisions_10.append(tg_p10)
        bl_precisions_5.append(bl_p5)
        bl_precisions_10.append(bl_p10)

    avg_tg_p5 = float(np.mean(tg_precisions_5)) if tg_precisions_5 else 0.0
    avg_tg_p10 = float(np.mean(tg_precisions_10)) if tg_precisions_10 else 0.0
    avg_bl_p5 = float(np.mean(bl_precisions_5)) if bl_precisions_5 else 0.0
    avg_bl_p10 = float(np.mean(bl_precisions_10)) if bl_precisions_10 else 0.0

    lift_5 = (
        ((avg_tg_p5 - avg_bl_p5) / max(0.001, avg_bl_p5)) * 100
        if avg_bl_p5 > 0
        else 0.0
    )
    lift_10 = (
        ((avg_tg_p10 - avg_bl_p10) / max(0.001, avg_bl_p10)) * 100
        if avg_bl_p10 > 0
        else 0.0
    )

    return {
        "niche": niche_id,
        "num_posts": len([p for p in held_out_data if p.get("title", "") and extract_ground_truth_tags(p["title"], p.get("text", ""))]),
        "precision_at_5": round(avg_tg_p5, 4),
        "precision_at_10": round(avg_tg_p10, 4),
        "baseline_precision_at_5": round(avg_bl_p5, 4),
        "baseline_precision_at_10": round(avg_bl_p10, 4),
        "lift_at_5": round(lift_5, 1),
        "lift_at_10": round(lift_10, 1),
    }


def generate_report(results: list[dict], output_path: str = None) -> str:
    """Generate a markdown comparison report from backtest results."""
    lines = []
    lines.append("# TagGenie Evaluation Report")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("\n## Summary")
    lines.append("\n| Niche | Posts | TG P@5 | BL P@5 | Lift@5 | TG P@10 | BL P@10 | Lift@10 |")
    lines.append("|-------|-------|--------|--------|--------|---------|---------|---------|")

    for r in results:
        if r.get("error"):
            lines.append(
                f"| {r['niche']} | — | — | — | — | — | — | — |"
            )
            continue
        lines.append(
            f"| {r['niche']} | {r.get('num_posts', 0)} "
            f"| {r.get('precision_at_5', 0):.1%} | {r.get('baseline_precision_at_5', 0):.1%} "
            f"| {r.get('lift_at_5', 0):+.1f}% "
            f"| {r.get('precision_at_10', 0):.1%} | {r.get('baseline_precision_at_10', 0):.1%} "
            f"| {r.get('lift_at_10', 0):+.1f}% |"
        )

    # Best lift
    best = max(results, key=lambda r: r.get("lift_at_5", -999))
    if best and not best.get("error"):
        lines.append(f"\n**Best lift:** {best['niche']} at {best['lift_at_5']:+.1f}% precision@5 lift over naive baseline.")

    lines.append("\n## Methodology")
    lines.append("- **TagGenie:** Uses trend volume (Google Trends), semantic relevance (sentence-transformers), competition density (ChromaDB cosine similarity), and platform-specific weights (learned via Thompson Sampling).")
    lines.append("- **Baseline:** Naive TF-IDF keyword extraction from topic + product text only — no trend data, no competition scoring, no engagement feedback.")
    lines.append("- **Ground truth:** KeyBERT-extracted keyphrases from each held-out post's title and text.")
    lines.append("- **Precision@k:** Fraction of top-k ranked tags that match ground truth terms.")
    lines.append("- **Held-out data:** Reddit posts with known engagement scores, not used during training.")

    lines.append("\n## Architecture Decisions")
    lines.append("- **Bandit over heuristic:** Thompson Sampling replaces the flat ±10% heuristic from Phase 2, modeling each platform/tag-type weight as a Beta distribution. More data = more confident posterior = tighter weight sampling.")
    lines.append("- **Reddit over LinkedIn scraping:** Reddit's official API (PRAW) provides terms-of-service-compliant access to engagement data. LinkedIn scraping would risk account suspension.")
    lines.append("- **Config-driven niches:** Each niche is a directory (seed corpus, jargon file, config) — no code changes needed to add a new industry.")

    report = "\n".join(lines)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            f.write(report)
        print(f"Report written to {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="TagGenie evaluation harness")
    parser.add_argument("--niche", type=str, default=None, help="Specific niche to evaluate (default: all)")
    parser.add_argument("--posts", type=int, default=10, help="Number of held-out posts per niche")
    parser.add_argument("--output", type=str, default="evaluation/results.md", help="Output report path")
    args = parser.parse_args()

    random.seed(42)

    if args.niche:
        niches = [args.niche]
    else:
        niches = [n["niche_id"] for n in get_available_niches()]

    results = []
    for niche_id in niches:
        print(f"\nEvaluating niche: {niche_id}")
        result = backtest_niche(niche_id, args.posts)
        print(f"  Posts scored: {result.get('num_posts', 0)}")
        print(f"  TagGenie P@5: {result.get('precision_at_5', 0):.1%}")
        print(f"  Baseline P@5: {result.get('baseline_precision_at_5', 0):.1%}")
        print(f"  Lift@5: {result.get('lift_at_5', 0):+.1f}%")
        results.append(result)

    print(f"\n{'='*60}")
    report = generate_report(results, args.output)
    print(report)


if __name__ == "__main__":
    main()
