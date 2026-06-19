"""Bandit convergence sanity check.
Triggers the nightly recompute job multiple times with varied synthetic engagement
outcomes and logs the Beta(alpha, beta) parameters after each run.
Confirms distributions are concentrating (variance decreasing) as more data arrives,
and that the sampled weight moves in a sensible direction relative to the signal.

Usage:
    python -m evaluation.bandit_convergence_check
"""

import sys
import json
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.scheduler import _thompson_recompute, get_beta_summary, _load_beta_params, _save_beta_params, BETA_FILE
from backend.feedback import log_feedback, init_db, seed_synthetic_feedback
from backend.scoring import PLATFORM_WEIGHTS, load_weights, save_weights


def beta_variance(alpha, beta):
    """Variance of a Beta(alpha, beta) distribution."""
    if alpha + beta <= 0:
        return 1.0
    return (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))


def main():
    init_db()

    # Reset to fresh state for clean convergence test (save originals first)
    if BETA_FILE.exists():
        BETA_FILE.rename(BETA_FILE.with_suffix(".json.bak"))
    save_weights()
    load_weights()

    print("=" * 80)
    print("BANDIT CONVERGENCE SANITY CHECK")
    print("=" * 80)
    print()
    print("Phase 1: Log synthetic engagement data to drive Beta updates")
    print("-" * 60)

    niches = ["gps-telematics", "b2b-saas", "fintech"]
    platforms = ["LinkedIn", "Instagram", "X", "TikTok"]

    post_count = 0
    for round_num in range(10):
        for niche in niches:
            for platform in platforms:
                for i in range(3):
                    post_id = f"conv_check_{round_num}_{niche}_{platform}_{i}"
                    tags = (
                        [f"t{j}" for j in range(2)]
                        + [f"multi word keyword phrase variant {j}" for j in range(3)]
                    )
                    likes = int(abs(hash(f"{post_id}_likes")) % 300 + 10)
                    shares = int(abs(hash(f"{post_id}_shares")) % 80)
                    comments = int(abs(hash(f"{post_id}_comments")) % 50)
                    log_feedback(post_id, platform, tags, likes, shares, comments, niche, source="bandit_check")
                    post_count += 1

    print(f"  Logged {post_count} synthetic feedback entries for convergence testing")

    print()
    print("Phase 2: Run 10 sequential recompute jobs, logging Beta params after each")
    print("-" * 60)

    all_betas = []
    for i in range(10):
        _thompson_recompute()
        betas = get_beta_summary()
        all_betas.append(betas)
        print(f"  Run {i+1:2d}: {len(betas)} platform/tag-type distributions tracked")

    print()
    print("Phase 3: Analysis — Variance trend (should decrease)")
    print("-" * 60)

    header = f"{'Key':25s} | {'Run1 Var':>10s} | {'Run10 Var':>11s} | {'Delta':>8s} | {'Converging?':>11s}"
    print(header)
    print("-" * 70)

    keys = list(all_betas[0].keys())
    converging_count = 0
    for key in sorted(keys):
        first = all_betas[0][key]
        last = all_betas[-1][key]
        var_first = beta_variance(first["alpha"], first["beta"])
        var_last = beta_variance(last["alpha"], last["beta"])
        delta = var_last - var_first
        converging = "YES" if delta < 0 else "NO"
        if delta < 0:
            converging_count += 1
        a1, b1 = first["alpha"], first["beta"]
        a2, b2 = last["alpha"], last["beta"]
        print(f"{key:25s} | {var_first:>10.6f} | {var_last:>11.6f} | {delta:>+8.6f} | {converging:>11s}")

    print()
    total_keys = len(keys)
    print(f"  {converging_count}/{total_keys} distributions show decreasing variance (should be most/all)")

    print()
    print("Phase 4: Weight movement analysis")
    print("-" * 60)

    print(f"{'Key':25s} | {'Run 1 a,b':>14s} | {'Run 10 a,b':>15s} | {'Mean shift':>10s}")
    print("-" * 65)

    positive_delta_count = 0
    for key in sorted(keys):
        first = all_betas[0][key]
        last = all_betas[-1][key]
        a1, b1 = first["alpha"], first["beta"]
        a2, b2 = last["alpha"], last["beta"]

        p1 = a1 / (a1 + b1) if (a1 + b1) > 0 else 0.5
        p2 = a2 / (a2 + b2) if (a2 + b2) > 0 else 0.5
        delta_p = p2 - p1
        if delta_p > 0:
            positive_delta_count += 1
        print(f"{key:25s} | ({a1:>5.0f}, {b1:>5.0f})  | ({a2:>5.0f}, {b2:>5.0f})  | {delta_p:>+7.4f}")

    print()
    print(f"  {positive_delta_count}/{total_keys} distributions show positive mean shift (signal follows engagement)")

    print()
    print("Phase 5: Final weights in scoring engine")
    print("-" * 60)
    for platform, weights in PLATFORM_WEIGHTS.items():
        print(f"  {platform:12s} hashtag={weights['hashtag']:.2f}  keyword={weights['keyword']:.2f}")

    print()
    print("=" * 80)
    print("VERDICT:")
    if converging_count > total_keys * 0.5:
        print(f"  PASS: {converging_count}/{total_keys} distributions converging (variance decreasing)")
    else:
        print(f"  WARNING: Only {converging_count}/{total_keys} distributions show decreasing variance")
    if positive_delta_count > total_keys * 0.3:
        print(f"  PASS: {positive_delta_count}/{total_keys} distributions shifting toward positive mean")
    else:
        print(f"  WARNING: Only {positive_delta_count}/{total_keys} distributions shifted positively")
    print("=" * 80)

    # Restore original state
    bak = BETA_FILE.with_suffix(".json.bak")
    if bak.exists():
        BETA_FILE.unlink(missing_ok=True)
        bak.rename(BETA_FILE)
    load_weights()


if __name__ == "__main__":
    main()
