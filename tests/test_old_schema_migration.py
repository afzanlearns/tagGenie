"""Test that the migration system correctly upgrades an old-style database."""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)

from backend.migration import (
    _ensure_version_table, _current_version, _set_version,
    _add_column, _create_index,
)


def test_old_schema_migration():
    db_path = "data/test_old_schema.db"

    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE post_feedback (
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

    conn = sqlite3.connect(db_path)

    _ensure_version_table(conn)
    current = _current_version(conn)
    assert current == 0, f"Expected version 0, got {current}"
    print(f"  [OK] Version starts at {current}")

    _add_column(conn, "post_feedback", "user_id", "TEXT DEFAULT ''")
    _add_column(conn, "post_feedback", "niche", "TEXT DEFAULT 'gps-telematics'")
    _add_column(conn, "post_feedback", "source", "TEXT DEFAULT 'synthetic'")

    cols = [r[1] for r in conn.execute("PRAGMA table_info(post_feedback)").fetchall()]
    assert "user_id" in cols, f"user_id missing: {cols}"
    assert "niche" in cols, f"niche missing: {cols}"
    assert "source" in cols, f"source missing: {cols}"
    print(f"  [OK] All columns added: {cols}")

    _add_column(conn, "post_feedback", "user_id", "TEXT DEFAULT ''")
    print("  [OK] Re-adding user_id is idempotent (no error)")

    _set_version(conn, 1)
    assert _current_version(conn) == 1
    print("  [OK] Version advanced to 1")

    _create_index(
        conn, "post_feedback", "idx_feedback_user", "user_id"
    )
    _create_index(
        conn, "post_feedback", "idx_feedback_user", "user_id"
    )
    print("  [OK] Index creation is idempotent")

    conn.close()

    import os
    os.remove(db_path)

    print()
    print("  All old-schema migration tests passed")
