"""Per-user persistent storage for history, saved sets, settings, and dashboard."""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"


def _db_path() -> Path:
    return DATA_DIR / "user_storage.db"


def _init_db():
    db = _db_path()
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            product TEXT NOT NULL,
            platform TEXT NOT NULL,
            niche TEXT NOT NULL,
            response_json TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            tag_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            topic TEXT NOT NULL,
            product TEXT NOT NULL,
            platform TEXT NOT NULL,
            niche TEXT NOT NULL,
            response_json TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            tag_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id TEXT PRIMARY KEY,
            preferred_platform TEXT DEFAULT 'LinkedIn',
            default_niche TEXT DEFAULT '',
            default_export_format TEXT DEFAULT 'json',
            theme TEXT DEFAULT 'dark',
            sort_preference TEXT DEFAULT 'score_desc',
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS niche_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            niche_id TEXT NOT NULL,
            last_used TEXT,
            usage_count INTEGER DEFAULT 0,
            recommendation_count INTEGER DEFAULT 0,
            avg_confidence REAL DEFAULT 0.0,
            avg_engagement REAL DEFAULT 0.0,
            most_successful_platform TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE(user_id, niche_id)
        )
    """)
    conn.commit()
    conn.close()


# ── History ──────────────────────────────────────────────────────────────

def save_history(user_id: str, topic: str, product: str, platform: str,
                 niche: str, response_dict: dict) -> int:
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    now = datetime.utcnow().isoformat()
    tag_count = len(response_dict.get("ranked_tags", []))
    confidence = response_dict.get("confidence", 0.0)
    conn.execute(
        """INSERT INTO recommendation_history
           (user_id, topic, product, platform, niche, response_json,
            confidence, tag_count, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, topic, product, platform, niche,
         json.dumps(response_dict), confidence, tag_count, now),
    )
    conn.commit()
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return row_id


def get_history(user_id: str, limit: int = 20) -> list[dict]:
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    rows = conn.execute(
        """SELECT id, topic, product, platform, niche, confidence,
                  tag_count, created_at
           FROM recommendation_history
           WHERE user_id = ?
           ORDER BY created_at DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r[0], "topic": r[1], "product": r[2], "platform": r[3],
            "niche": r[4], "confidence": r[5], "tag_count": r[6],
            "created_at": r[7],
        }
        for r in rows
    ]


def get_history_detail(user_id: str, history_id: int) -> dict | None:
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    row = conn.execute(
        "SELECT response_json FROM recommendation_history WHERE id = ? AND user_id = ?",
        (history_id, user_id),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return json.loads(row[0])


def clear_history(user_id: str):
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    conn.execute("DELETE FROM recommendation_history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ── Saved Sets ──────────────────────────────────────────────────────────

def save_set(user_id: str, name: str, topic: str, product: str,
             platform: str, niche: str, response_dict: dict) -> int:
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    now = datetime.utcnow().isoformat()
    tag_count = len(response_dict.get("ranked_tags", []))
    confidence = response_dict.get("confidence", 0.0)
    conn.execute(
        """INSERT INTO saved_sets
           (user_id, name, topic, product, platform, niche, response_json,
            confidence, tag_count, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, name, topic, product, platform, niche,
         json.dumps(response_dict), confidence, tag_count, now),
    )
    conn.commit()
    row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return row_id


def get_saved_sets(user_id: str) -> list[dict]:
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    rows = conn.execute(
        """SELECT id, name, topic, product, platform, niche, confidence,
                  tag_count, created_at
           FROM saved_sets WHERE user_id = ?
           ORDER BY created_at DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r[0], "name": r[1], "topic": r[2], "product": r[3],
            "platform": r[4], "niche": r[5], "confidence": r[6],
            "tag_count": r[7], "created_at": r[8],
        }
        for r in rows
    ]


def get_saved_set_detail(user_id: str, set_id: int) -> dict | None:
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    row = conn.execute(
        "SELECT response_json FROM saved_sets WHERE id = ? AND user_id = ?",
        (set_id, user_id),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return json.loads(row[0])


def delete_saved_set(user_id: str, set_id: int):
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    conn.execute("DELETE FROM saved_sets WHERE id = ? AND user_id = ?", (set_id, user_id))
    conn.commit()
    conn.close()


# ── User Settings ──────────────────────────────────────────────────────

def save_settings(user_id: str, settings: dict):
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    now = datetime.utcnow().isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO user_settings
           (user_id, preferred_platform, default_niche, default_export_format,
            theme, sort_preference, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            settings.get("preferred_platform", "LinkedIn"),
            settings.get("default_niche", ""),
            settings.get("default_export_format", "json"),
            settings.get("theme", "dark"),
            settings.get("sort_preference", "score_desc"),
            now,
        ),
    )
    conn.commit()
    conn.close()


def get_settings(user_id: str) -> dict:
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    row = conn.execute(
        """SELECT preferred_platform, default_niche, default_export_format,
                  theme, sort_preference
           FROM user_settings WHERE user_id = ?""",
        (user_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return {
            "preferred_platform": "LinkedIn",
            "default_niche": "",
            "default_export_format": "json",
            "theme": "dark",
            "sort_preference": "score_desc",
        }
    return {
        "preferred_platform": row[0],
        "default_niche": row[1],
        "default_export_format": row[2],
        "theme": row[3],
        "sort_preference": row[4],
    }


# ── Niche Metadata ─────────────────────────────────────────────────────

def update_niche_metadata(user_id: str, niche_id: str, confidence: float = 0.0):
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    now = datetime.utcnow().isoformat()
    existing = conn.execute(
        "SELECT usage_count, recommendation_count, avg_confidence, avg_engagement FROM niche_metadata WHERE user_id = ? AND niche_id = ?",
        (user_id, niche_id),
    ).fetchone()
    if existing:
        usage_count = existing[0] + 1
        rec_count = existing[1]
        avg_conf = existing[2]
        avg_eng = existing[3]
        conn.execute(
            """UPDATE niche_metadata SET last_used = ?, usage_count = ?,
               avg_confidence = ? WHERE user_id = ? AND niche_id = ?""",
            (now, usage_count, round((avg_conf * (usage_count - 1) + confidence) / usage_count, 1),
             user_id, niche_id),
        )
    else:
        conn.execute(
            """INSERT INTO niche_metadata
               (user_id, niche_id, last_used, usage_count, usage_count,
                recommendation_count, avg_confidence, avg_engagement, created_at)
               VALUES (?, ?, ?, 1, 1, 0, ?, 0.0, ?)""",
            (user_id, niche_id, now, confidence, now),
        )
    conn.commit()
    conn.close()


def get_niche_metadata(user_id: str) -> list[dict]:
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    rows = conn.execute(
        """SELECT niche_id, last_used, usage_count, recommendation_count,
                  avg_confidence, avg_engagement, most_successful_platform, created_at
           FROM niche_metadata WHERE user_id = ?
           ORDER BY usage_count DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "niche_id": r[0], "last_used": r[1], "usage_count": r[2],
            "recommendation_count": r[3], "avg_confidence": r[4],
            "avg_engagement": r[5], "most_successful_platform": r[6],
            "created_at": r[7],
        }
        for r in rows
    ]


# ── Dashboard Stats ────────────────────────────────────────────────────

def get_dashboard_stats(user_id: str) -> dict:
    _init_db()
    conn = sqlite3.connect(str(_db_path()))
    total_niches = conn.execute(
        "SELECT COUNT(DISTINCT niche_id) FROM niche_metadata WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0] or 0

    total_recs = conn.execute(
        "SELECT COALESCE(SUM(tag_count), 0) FROM recommendation_history WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0] or 0

    total_scores = conn.execute(
        "SELECT COUNT(*) FROM recommendation_history WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0] or 0

    avg_conf = conn.execute(
        "SELECT COALESCE(AVG(confidence), 0) FROM recommendation_history WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0] or 0.0

    most_used_platform = conn.execute(
        """SELECT platform, COUNT(*) as cnt FROM recommendation_history
           WHERE user_id = ? GROUP BY platform ORDER BY cnt DESC LIMIT 1""",
        (user_id,),
    ).fetchone()
    most_used_platform = most_used_platform[0] if most_used_platform else "LinkedIn"

    most_used_niche = conn.execute(
        """SELECT niche, COUNT(*) as cnt FROM recommendation_history
           WHERE user_id = ? GROUP BY niche ORDER BY cnt DESC LIMIT 1""",
        (user_id,),
    ).fetchone()
    most_used_niche = most_used_niche[0] if most_used_niche else "gps-telematics"

    blue_ocean_count = conn.execute(
        "SELECT COUNT(*) FROM recommendation_history WHERE user_id = ? AND confidence >= 60",
        (user_id,),
    ).fetchone()[0] or 0

    history_timeline = conn.execute(
        """SELECT created_at, topic, platform, tag_count, confidence
           FROM recommendation_history WHERE user_id = ?
           ORDER BY created_at DESC LIMIT 10""",
        (user_id,),
    ).fetchall()

    conn.close()

    return {
        "total_niches": total_niches,
        "recommendations_generated": total_recs,
        "total_sessions": total_scores,
        "blue_ocean_opportunities_found": blue_ocean_count,
        "most_used_platform": most_used_platform,
        "most_used_niche": most_used_niche,
        "average_confidence": round(avg_conf, 1),
        "history_timeline": [
            {"created_at": r[0], "topic": r[1], "platform": r[2],
             "tag_count": r[3], "confidence": r[4]}
            for r in history_timeline
        ],
    }
