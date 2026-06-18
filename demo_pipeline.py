import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import requests

API_BASE = "http://localhost:8000"
MOCKS_DIR = Path(__file__).parent / "mocks"
PLATFORMS = ["LinkedIn", "Instagram", "X", "TikTok"]

HEADER = "=" * 60


def print_stage(label: str, content: str = ""):
    print(f"\n{HEADER}")
    print(f"[STAGE] {label}")
    print(HEADER)
    if content:
        print(content)


def main():
    print_stage(
        "1. TrendRadar Ingest",
        "Loading mock trending topics from mocks/mock_trendradar_payload.json",
    )

    with open(MOCKS_DIR / "mock_trendradar_payload.json") as f:
        trendradar_payload = json.load(f)

    print(f"  Received {len(trendradar_payload['topics'])} topics from TrendRadar:")
    for t in trendradar_payload["topics"]:
        print(f"    {t['topic']} (momentum: {t['momentum_score']})")

    print("\n  POST /api/ingest-candidates ...")
    resp = requests.post(
        f"{API_BASE}/api/ingest-candidates",
        json={"topics": trendradar_payload["topics"]},
        timeout=10,
    )
    ingest_result = resp.json()
    print(f"  Status: {ingest_result['status']}")
    print(f"  Accepted: {ingest_result['count']} topics")
    print(f"  Total stored: {ingest_result['total_stored']}")

    print_stage("2. TagGenie Scoring", "Scoring each ingested topic through /api/score")

    all_payloads = []
    for i, topic_entry in enumerate(trendradar_payload["topics"]):
        topic = topic_entry["topic"]
        platform = PLATFORMS[i % len(PLATFORMS)]
        product = f"Demo-Product-{i + 1}"

        print(f"\n  [{i + 1}] Topic: {topic}")
        print(f"      Platform: {platform} | Product: {product}")

        start = time.time()
        resp = requests.post(
            f"{API_BASE}/api/score",
            json={
                "topic": topic,
                "product": product,
                "platform": platform,
                "include_baseline": True,
            },
            timeout=60,
        )
        elapsed = time.time() - start

        if resp.status_code != 200:
            print(f"      ERROR: {resp.status_code} - {resp.text[:100]}")
            continue

        data = resp.json()
        print(f"      Ranked tags: {len(data['ranked_tags'])}")
        print(f"      Gap tags: {len(data['gap_tags'])}")
        print(f"      Baseline tags: {len(data.get('baseline_tags', []))}")
        print(f"      Confidence: {data['confidence']}% | Fallback: {data['fallback_mode']}")
        print(f"      Response time: {elapsed:.2f}s")

        for tag in data["ranked_tags"][:5]:
            print(f"        -> {tag['tag']} ({tag['final_score']:.1f})")

        if data.get("gap_tags"):
            print(f"      BLUE OCEAN:")
            for gap in data["gap_tags"][:3]:
                print(f"        -> {gap['tag']} (reach={gap['reach_score']:.0f}, comp={gap['competition_score']:.0f})")

        all_payloads.append(
            {
                "source": "TagGenie",
                "platform": platform,
                "topic": topic,
                "publish_payload": {
                    "hashtags": [t["tag"] for t in data["ranked_tags"][:5] if t["type"] == "hashtag"],
                    "keywords": [t["tag"] for t in data["ranked_tags"][:5] if t["type"] == "keyword"],
                    "top_tag": data["ranked_tags"][0]["tag"] if data["ranked_tags"] else None,
                    "top_tag_score": data["ranked_tags"][0]["final_score"] if data["ranked_tags"] else 0,
                },
            }
        )

    print_stage("3. OmniPost Format", "Formatted publish-ready payloads for OmniPost consumption")

    for i, payload in enumerate(all_payloads):
        print(f"\n  [{i + 1}] {payload['topic']}")
        print(f"      Platform: {payload['platform']}")
        print(f"      Top tag: {payload['publish_payload']['top_tag']} ({payload['publish_payload']['top_tag_score']:.1f})")
        print(f"      Hashtags: {payload['publish_payload']['hashtags']}")
        print(f"      Keywords: {payload['publish_payload']['keywords']}")

    output_path = Path(__file__).parent / "data" / "demo_pipeline_output.json"
    with open(output_path, "w") as f:
        json.dump(all_payloads, f, indent=2)

    print(f"\n  Full output saved to: {output_path}")

    print_stage(
        "PIPELINE COMPLETE",
        "TrendRadar -> TagGenie ingest -> scoring -> gap-finding -> OmniPost publish",
    )
    print("  All stages executed successfully.")
    return all_payloads


if __name__ == "__main__":
    main()
