import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "feedback.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS post_feedback (
            post_id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            tags_used TEXT NOT NULL,
            likes INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def log_feedback(post_id: str, platform: str, tags_used: list[str],
                 likes: int, shares: int, comments: int):
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO post_feedback (post_id, platform, tags_used, likes, shares, comments, posted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (post_id, platform, json.dumps(tags_used), likes, shares, comments, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_platform_stats(platform: str) -> dict:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT tags_used, likes, shares, comments FROM post_feedback WHERE platform = ?",
        (platform,),
    ).fetchall()
    conn.close()

    tag_engagement = {}
    total_engagement = 0
    post_count = 0

    for row in rows:
        tags = json.loads(row["tags_used"])
        eng = row["likes"] + row["shares"] * 2 + row["comments"] * 1.5
        total_engagement += eng
        post_count += 1
        for tag in tags:
            if tag not in tag_engagement:
                tag_engagement[tag] = {"engagement": 0, "count": 0}
            tag_engagement[tag]["engagement"] += eng
            tag_engagement[tag]["count"] += 1

    return {
        "platform": platform,
        "post_count": post_count,
        "total_engagement": total_engagement,
        "avg_engagement": total_engagement / max(1, post_count),
        "tag_engagement": tag_engagement,
    }


def seed_synthetic_feedback():
    conn = _get_conn()
    count = conn.execute("SELECT COUNT(*) FROM post_feedback").fetchone()[0]
    if count > 0:
        conn.close()
        return

    import random
    random.seed(42)

    synthetic_posts = []
    base_time = datetime(2025, 1, 1)
    platforms = ["LinkedIn", "Instagram", "X", "TikTok"]
    tag_pools = {
        "LinkedIn": [
            ["fleet safety", "AI dashcams", "driver coaching", "predictive maintenance"],
            ["telematics integration", "fleet management", "real-time tracking", "GPS telematics"],
            ["commercial fleets", "EV fleet", "sustainability", "fuel efficiency"],
            ["driver safety", "dashcam analytics", "fleet compliance", "ELD mandate"],
            ["last-mile delivery", "route optimization", "logistics tech", "supply chain"],
        ],
        "Instagram": [
            ["fleetlife", "dashcam", "trucktech", "safetyfirst"],
            ["telematics", "fleetmanagement", "logistics", "innovation"],
            ["electricfleet", "sustainability", "greentech", "future"],
            ["driversafety", "ai", "computervision", "roadsafety"],
            ["lastmile", "delivery", "logistics", "ecommerce"],
        ],
        "X": [
            ["fleet safety", "AI", "dashcams", "tech"],
            ["telematics", "GPS", "fleet", "data"],
            ["EV fleet", "climate", "logistics", "sustainability"],
            ["driver safety", "AI", "computer vision", "insurance"],
            ["last-mile", "delivery", "automation", "robotics"],
        ],
        "TikTok": [
            ["fleettech", "dashcam", "safety", "trucking"],
            ["telematics", "fleet", "logistics", "data"],
            ["evfleet", "sustainable", "green", "future"],
            ["driversafety", "ai", "tech", "innovation"],
            ["lastmiledelivery", "logistics", "automation", "robotics"],
        ],
    }

    for i in range(60):
        platform = random.choice(platforms)
        tags_pool = tag_pools[platform]
        tags = random.choice(tags_pool)
        likes = random.randint(5, 200)
        shares = random.randint(0, 50)
        comments = random.randint(0, 30)
        post_time = base_time
        base_time = base_time.replace(hour=(base_time.hour + 6) % 24)
        if i % 5 == 0:
            base_time = base_time.replace(day=min(28, base_time.day + 1))

        synthetic_posts.append((
            f"synth_{i}", platform, json.dumps(tags),
            likes, shares, comments, post_time.isoformat(),
        ))

    conn.executemany(
        "INSERT INTO post_feedback (post_id, platform, tags_used, likes, shares, comments, posted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        synthetic_posts,
    )
    conn.commit()
    conn.close()
