"""Reddit ingestion using PRAW to pull real posts and engagement data per niche.

Uses Reddit's official API (free tier). Requires REDDIT_CLIENT_ID and
REDDIT_CLIENT_SECRET in the .env file.

Usage:
    python -c "from backend.reddit_ingest import ingest_niche_subreddits; ingest_niche_subreddits('gps-telematics')"
    python -c "from backend.reddit_ingest import build_held_out_dataset; print(build_held_out_dataset())"
"""

import os
import json
import random
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

from backend.feedback import log_feedback

load_dotenv(Path(__file__).parent / ".env")

# Niche -> relevant subreddits for real data collection
SUBREDDIT_MAP = {
    "gps-telematics": [
        "fleetmanagement",
        "logistics",
        "IoT",
        "gps",
        "truckers",
        "supplychain",
    ],
    "b2b-saas": [
        "SaaS",
        "sales",
        "startups",
        "growthmarketing",
        "productmanagement",
        "entrepreneur",
    ],
    "fintech": [
        "fintech",
        "payments",
        "banking",
        "personalfinance",
        "cryptocurrency",
        "investing",
    ],
}

_reddit_instance = None


def _get_reddit():
    global _reddit_instance
    if _reddit_instance is not None:
        return _reddit_instance

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None  # Not configured, will skip Reddit ingestion

    import praw

    _reddit_instance = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="windows:taggenie:v3.0.0 (by /u/taggenie_dev)",
    )
    return _reddit_instance


def fetch_subreddit_posts(
    subreddit_name: str, limit: int = 25, time_filter: str = "month"
) -> list[dict]:
    """Fetch top posts from a subreddit with engagement metrics."""
    reddit = _get_reddit()
    if reddit is None:
        return []

    try:
        subreddit = reddit.subreddit(subreddit_name)
        posts = []
        for post in subreddit.top(time_filter=time_filter, limit=limit):
            posts.append(
                {
                    "post_id": f"reddit_{post.id}",
                    "platform": "Reddit",
                    "title": post.title,
                    "text": post.selftext[:500] if post.selftext else "",
                    "tags_used": _extract_tags_from_post(post),
                    "likes": post.score,  # upvotes
                    "shares": 0,  # Reddit doesn't expose share count via API
                    "comments": post.num_comments,
                    "ups": post.ups,
                    "downs": post.downs,
                    "upvote_ratio": post.upvote_ratio,
                    "posted_at": datetime.fromtimestamp(
                        post.created_utc, tz=timezone.utc
                    ).isoformat(),
                    "subreddit": subreddit_name,
                    "url": post.url,
                }
            )
        return posts
    except Exception:
        return []


def _extract_tags_from_post(post) -> list[str]:
    """Extract tags from post title and flair."""
    tags = []
    title_lower = post.title.lower()

    # Add post flair as tag if available
    if hasattr(post, "link_flair_text") and post.link_flair_text:
        tags.append(post.link_flair_text.lower().strip())

    # Extract hashtags from title
    for word in title_lower.split():
        if word.startswith("#") and len(word) > 2:
            tags.append(word[1:])

    # Add subreddit name as a context tag
    tags.append(post.subreddit.display_name.lower())

    return tags[:5] if tags else [post.subreddit.display_name.lower()]


def ingest_niche_subreddits(
    niche_id: str,
    max_posts_per_subreddit: int = 15,
    store_to_db: bool = True,
) -> list[dict]:
    """Pull posts from subreddits relevant to a niche and optionally store feedback.

    Returns the list of fetched posts.
    """
    subreddits = SUBREDDIT_MAP.get(niche_id, [])
    if not subreddits:
        print(f"No subreddits configured for niche '{niche_id}'")
        return []

    all_posts = []
    for sub_name in subreddits:
        posts = fetch_subreddit_posts(sub_name, limit=max_posts_per_subreddit)
        for p in posts:
            p["niche"] = niche_id
            p["source"] = "real"
            all_posts.append(p)

            if store_to_db:
                log_feedback(
                    post_id=p["post_id"],
                    platform="Reddit",
                    tags_used=p["tags_used"],
                    likes=p["likes"],
                    shares=p["shares"],
                    comments=p["comments"],
                    niche=niche_id,
                    source="real",
                )

    print(
        f"Ingested {len(all_posts)} real posts for '{niche_id}' "
        f"from {len([p for p in all_posts if p])} subreddits"
    )
    return all_posts


def build_held_out_dataset(
    niche_id: str = "gps-telematics",
    num_posts: int = 20,
) -> list[dict]:
    """Build a small held-out dataset of Reddit posts with their actual engagement.

    These posts are NOT used for training the scoring engine — they serve as
    ground truth for the evaluation harness in Week 3.

    Returns a list of dicts with known engagement outcomes for evaluation.
    """
    reddit = _get_reddit()
    if reddit is None:
        # Generate synthetic held-out data for testing when Reddit isn't configured
        return _generate_synthetic_held_out(niche_id, num_posts)

    random.seed(42)
    subreddits = SUBREDDIT_MAP.get(niche_id, ["all"])
    sub_name = random.choice(subreddits)

    try:
        subreddit = reddit.subreddit(sub_name)
        held_out = []
        count = 0
        for post in subreddit.top(time_filter="year", limit=num_posts * 2):
            if count >= num_posts:
                break
            if post.score > 10:  # Only include posts with meaningful engagement
                held_out.append(
                    {
                        "post_id": f"heldout_{post.id}",
                        "title": post.title,
                        "text": post.selftext[:500] if post.selftext else "",
                        "actual_upvotes": post.score,
                        "actual_comments": post.num_comments,
                        "upvote_ratio": post.upvote_ratio,
                        "subreddit": sub_name,
                        "niche": niche_id,
                        "url": post.url,
                        "posted_at": datetime.fromtimestamp(
                            post.created_utc, tz=timezone.utc
                        ).isoformat(),
                    }
                )
                count += 1
        return held_out
    except Exception:
        return _generate_synthetic_held_out(niche_id, num_posts)


def _generate_synthetic_held_out(niche_id: str, num_posts: int) -> list[dict]:
    """Generate synthetic held-out data for testing when Reddit API unavailable."""
    random.seed(42)
    niches = [
        "gps-telematics",
        "b2b-saas",
        "fintech",
    ]
    titles = {
        "gps-telematics": [
            "How real-time GPS tracking reduced our fleet costs by 22%",
            "The state of ELD compliance in 2026",
            "Why we switched from paper logs to digital telematics",
            "Best dashcam for long-haul trucking?",
            "Fleet electrification — is it worth it for last-mile?",
            "Trailer tracking solutions that actually work",
            "Cold chain monitoring saved us $50K in spoilage",
            "Route optimization AI vs human dispatchers",
            "Predictive maintenance ROI — our numbers after 1 year",
            "Fuel theft prevention using telematics data",
        ],
        "b2b-saas": [
            "We grew from $0 to $5M ARR with no enterprise sales",
            "The PLG playbook that doubled our activation rate",
            "Why we switched from per-seat to usage-based pricing",
            "Our churn analysis revealed a surprising segment",
            "Building a sales team at $3M ARR — lessons learned",
            "The integration strategy that accelerated enterprise deals",
            "Customer health scores that actually predict churn",
            "How we reduced CAC by 40% with content marketing",
            "Pricing page A/B test increased conversions by 25%",
            "The real cost of poor product documentation",
        ],
        "fintech": [
            "Embedded finance is eating banking — here's the data",
            "Open banking adoption numbers 2026",
            "The hidden costs of payment orchestration",
            "Why BNPL is not going away despite regulation",
            "Building a neobank for SMEs — our tech stack",
            "KYC verification abandonment rates and how to fix them",
            "The state of real-time payments in the US",
            "Fintech partnerships with incumbent banks — a playbook",
            "Cross-border payment infrastructure comparison",
            "AI credit scoring for thin-file borrowers",
        ],
    }

    held_out = []
    for i in range(num_posts):
        niche = random.choice(niches)
        topic_list = titles.get(niche, titles["gps-telematics"])
        title = topic_list[i % len(topic_list)]
        score = random.randint(50, 500)
        comments = random.randint(5, 80)

        held_out.append(
            {
                "post_id": f"heldout_synth_{i}",
                "title": title,
                "text": "",
                "actual_upvotes": score,
                "actual_comments": comments,
                "upvote_ratio": round(random.uniform(0.7, 0.98), 2),
                "subreddit": niche.replace("-", ""),
                "niche": niche,
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "source": "simulated",
            }
        )
    return held_out
