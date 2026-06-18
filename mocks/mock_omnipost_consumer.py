import requests
import json


def format_for_omnipost(scored_tags: list[dict], platform: str, topic: str) -> dict:
    top_tags = scored_tags[:5]
    return {
        "source": "TagGenie",
        "platform": platform,
        "topic": topic,
        "publish_payload": {
            "hashtags": [t["tag"] for t in top_tags if t["type"] == "hashtag"],
            "keywords": [t["tag"] for t in top_tags if t["type"] == "keyword"],
            "top_tag": top_tags[0]["tag"],
            "top_tag_score": top_tags[0]["final_score"],
        },
    }


def consume_topic(topic: str, platform: str, api_base: str = "http://localhost:8000") -> dict:
    resp = requests.post(
        f"{api_base}/api/score",
        json={"topic": topic, "product": "Auto-product", "platform": platform, "include_baseline": False},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return format_for_omnipost(data["ranked_tags"], platform, topic)


if __name__ == "__main__":
    payload = consume_topic("AI dashcams for fleet safety", "LinkedIn")
    print(json.dumps(payload, indent=2))
