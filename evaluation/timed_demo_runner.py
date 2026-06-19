"""Timed cold-start demo runner.
Fully restarts/clears cache, then runs the complete scoring pipeline twice
across two different niches. Records actual timings at each stage.

Usage:
    # Start the server first:
    python main.py &
    # Then run:
    python -m evaluation.timed_demo_runner
"""

import time
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

API_BASE = "http://localhost:8000"
PLATFORMS = ["LinkedIn", "Instagram", "X", "TikTok"]

DEMO_TOPICS = [
    "fleet safety with AI dashcams",
    "predictive maintenance for commercial vehicles",
    "driver behavior coaching",
    "route optimization algorithms",
    "ELD compliance automation",
]

B2B_TOPICS = [
    "SaaS customer retention metrics",
    "product-led growth strategies",
    "enterprise sales automation tools",
    "churn prediction analytics",
    "B2B content marketing ROI",
]


def print_header(label):
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")


def run_demo(niche: str, topics: list[str], run_label: str) -> list[dict]:
    print_header(f"{run_label}: Niche = {niche}")

    timings = []
    for i, topic in enumerate(topics):
        platform = PLATFORMS[i % len(PLATFORMS)]
        product = f"Demo-{niche}-{i+1}"

        print(f"\n  [{i+1}/{len(topics)}] Topic: {topic}")
        print(f"      Platform: {platform}")

        t_start = time.time()
        try:
            resp = requests.post(
                f"{API_BASE}/api/score",
                json={
                    "topic": topic,
                    "product": product,
                    "platform": platform,
                    "niche": niche,
                    "include_baseline": True,
                },
                timeout=120,
            )
            elapsed = time.time() - t_start

            if resp.status_code != 200:
                print(f"      ERROR: {resp.status_code} - {resp.text[:100]}")
                timings.append({
                    "topic": topic,
                    "platform": platform,
                    "status": "error",
                    "total_seconds": round(elapsed, 3),
                })
                continue

            data = resp.json()
            resp_timings = data.get("timings", {})

            entry = {
                "topic": topic,
                "platform": platform,
                "status": "ok",
                "total_seconds": round(elapsed, 3),
                "scoring_seconds": resp_timings.get("scoring_total", "?"),
                "baseline_seconds": resp_timings.get("baseline", "?"),
                "n_tags": len(data.get("ranked_tags", [])),
                "n_gaps": len(data.get("gap_tags", [])),
                "confidence": data.get("confidence", 0),
            }
            timings.append(entry)

            print(f"      Total: {elapsed:.2f}s | Score: {resp_timings.get('scoring_total', '?')}s | Baseline: {resp_timings.get('baseline', '?')}s")
            print(f"      Tags: {entry['n_tags']} | Gaps: {entry['n_gaps']} | Confidence: {entry['confidence']}%")

            if len(data.get("ranked_tags", [])) > 0:
                top = data["ranked_tags"][0]
                print(f"      Top tag: {top['tag']} ({top['final_score']:.1f})")

        except requests.exceptions.ConnectionError:
            elapsed = time.time() - t_start
            print(f"      CONNECTION ERROR after {elapsed:.1f}s — is the server running on port 8000?")
            timings.append({
                "topic": topic,
                "platform": platform,
                "status": "connection_error",
                "total_seconds": round(elapsed, 3),
            })

    return timings


def check_landing_page():
    print("\n  Checking landing page endpoint...")
    try:
        resp = requests.get(f"{API_BASE}/api/evaluation-summary", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"    Status: OK")
            print(f"    Best lift: +{data.get('best_lift_pct', '?')}% ({data.get('niche', '?')})")
            print(f"    Results: {len(data.get('results', []))} niches")
            return data
        else:
            print(f"    Status: ERROR {resp.status_code}")
    except Exception as e:
        print(f"    Status: ERROR - {e}")
    return None


def check_health():
    try:
        resp = requests.get(f"{API_BASE}/api/health", timeout=5)
        return resp.status_code == 200
    except:
        return False


def main():
    print_header("TIMED COLD-START DRY RUN")
    print("  Make sure the backend is running on port 8000 first!")
    print("  (If server was restarted, in-memory cache is cleared)")

    if not check_health():
        print("\n  ERROR: Cannot reach server at http://localhost:8000")
        print("  Start the server first: python main.py")
        return

    all_runs = []

    # Run 1: GPS-Telematics
    timings_1 = run_demo("gps-telematics", DEMO_TOPICS, "RUN 1")
    all_runs.append({"run": 1, "niche": "gps-telematics", "timings": timings_1})

    # Check landing page between runs
    print()
    eval_check_1 = check_landing_page()

    # Run 2: B2B SaaS
    timings_2 = run_demo("b2b-saas", B2B_TOPICS, "RUN 2")
    all_runs.append({"run": 2, "niche": "b2b-saas", "timings": timings_2})

    print()
    eval_check_2 = check_landing_page()

    # Summary
    print_header("RESULTS SUMMARY")

    for run_data in all_runs:
        print(f"\n  Run {run_data['run']} — Niche: {run_data['niche']}")
        print(f"  {'Topic':50s} {'Total':>7s} {'Score':>7s} {'Base':>7s} {'Tags':>5s}")
        print(f"  {'-'*50} {'-'*7} {'-'*7} {'-'*7} {'-'*5}")

        max_duration = 0
        over_threshold = []
        for t in run_data["timings"]:
            total = t.get("total_seconds", 0)
            scoring = t.get("scoring_seconds", 0)
            baseline = t.get("baseline_seconds", 0)
            tags = t.get("n_tags", 0)
            topic_short = t["topic"][:48]
            print(f"  {topic_short:50s} {total:>7.2f}s {str(scoring):>7s} {str(baseline):>7s} {tags:>5d}")
            if total > max_duration:
                max_duration = total
            if total > 4.0:
                over_threshold.append(t["topic"])

        avg = sum(t.get("total_seconds", 0) for t in run_data["timings"]) / max(1, len(run_data["timings"]))
        print(f"\n  Max stage: {max_duration:.2f}s | Average: {avg:.2f}s")

        if over_threshold:
            print(f"  [!] Exceeded 4s threshold: {len(over_threshold)} stages")
            for t in over_threshold:
                print(f"     - {t}")
        else:
            print(f"  [OK] All stages under 4s threshold")

    print(f"\n  Landing page /api/evaluation-summary check:")
    if eval_check_1:
        print(f"    Pre-run 2: OK — lift={eval_check_1.get('best_lift_pct', '?')}%")
    if eval_check_2:
        print(f"    Post-run 4: OK — lift={eval_check_2.get('best_lift_pct', '?')}%")

    print_header("DRY RUN COMPLETE")


if __name__ == "__main__":
    main()
