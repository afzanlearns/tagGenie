"""Automatic, versioned SQLite schema migration engine.

Each database has a _schema_version table tracking which migrations have been
applied.  On startup, the engine checks the current version and applies any
pending migrations in order.  All operations are idempotent.
"""

import sqlite3
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


# helpers -----------------------------------------------------------------

def _ensure_version_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def _current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(version), 0) FROM _schema_version"
    ).fetchone()
    return row[0] if row else 0


def _set_version(conn: sqlite3.Connection, version: int):
    conn.execute("INSERT OR IGNORE INTO _schema_version (version) VALUES (?)", (version,))
    conn.commit()


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    return column in cols


def _add_column(conn: sqlite3.Connection, table: str, column: str, col_def: str):
    if not _column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
        conn.commit()
        logger.info("  [OK] Added column %s to %s", column, table)
    else:
        logger.info("  [--] Column %s already exists in %s", column, table)


def _index_exists(conn: sqlite3.Connection, index_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (index_name,)
    ).fetchone()
    return row is not None


def _create_index(conn: sqlite3.Connection, table: str, index_name: str, columns: str):
    if not _index_exists(conn, index_name):
        conn.execute(f"CREATE INDEX {index_name} ON {table}({columns})")
        conn.commit()
        logger.info("  [OK] Created index %s on %s(%s)", index_name, table, columns)
    else:
        logger.info("  [--] Index %s already exists", index_name)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _create_table(conn: sqlite3.Connection, ddl: str, table: str):
    if not _table_exists(conn, table):
        conn.execute(ddl)
        conn.commit()
        logger.info("  [OK] Created table %s", table)
    else:
        logger.info("  [--] Table %s already exists", table)


# migration definition ----------------------------------------------------

@dataclass
class Migration:
    version: int
    description: str
    apply: callable  # (sqlite3.Connection) -> None


# per-database migration lists -------------------------------------------

FEEDBACK_DB_MIGRATIONS: list[Migration] = [
    Migration(
        1,
        "Add user_id, niche, source columns to post_feedback (non-destructive)",
        lambda c: (
            _add_column(c, "post_feedback", "user_id", "TEXT DEFAULT ''"),
            _add_column(c, "post_feedback", "niche", "TEXT DEFAULT 'gps-telematics'"),
            _add_column(c, "post_feedback", "source", "TEXT DEFAULT 'synthetic'"),
        ),
    ),
    Migration(
        2,
        "Add indexes for user-isolation queries on feedback.db",
        lambda c: (
            _create_index(c, "post_feedback", "idx_feedback_user", "user_id"),
            _create_index(c, "post_feedback", "idx_feedback_niche", "niche"),
            _create_index(c, "post_feedback", "idx_feedback_platform", "platform"),
        ),
    ),
]

AUTH_DB_MIGRATIONS: list[Migration] = [
    Migration(
        1,
        "Add indexes on auth.db user_niches and usage_log for user lookups",
        lambda c: (
            _create_index(c, "user_niches", "idx_auth_user_niches_user", "user_id"),
            _create_index(c, "usage_log", "idx_usage_log_user", "user_id"),
        ),
    ),
    Migration(
        2,
        "Add api_key index on users table",
        lambda c: (
            _create_index(c, "users", "idx_users_api_key", "api_key"),
        ),
    ),
]

NICHES_DB_MIGRATIONS: list[Migration] = [
    Migration(
        1,
        "Add index on user_id in user_niches.db",
        lambda c: (
            _create_index(c, "user_niches", "idx_usr_niches_user", "user_id"),
        ),
    ),
]


# engine -----------------------------------------------------------------

def _apply_migrations(db_label: str, db_path: Path, migrations: list[Migration]):
    """Apply pending migrations to *db_path* in order.  Idempotent."""
    if not db_path.exists():
        logger.info("  (database does not exist yet - will be created by init functions)")
        return

    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_version_table(conn)
        current = _current_version(conn)
        latest = max(m.version for m in migrations) if migrations else current

        if current >= latest:
            logger.info("  Schema at version %s (latest) - no migrations needed", current)
            return

        logger.info("  Schema at version %s, target %s - applying migrations ...", current, latest)

        for m in sorted(migrations, key=lambda x: x.version):
            if m.version > current:
                logger.info("  > [v%i] %s", m.version, m.description)
                m.apply(conn)
                _set_version(conn, m.version)
                logger.info("    [OK] Migration v%i complete", m.version)

        final = _current_version(conn)
        logger.info("  Schema now at version %s", final)
    finally:
        conn.close()


def run_migrations():
    """Run all pending migrations for every known database.

    Must be called **after** the database files have been created by the
    individual init functions (init_db, init_auth_db, _init_user_niches_db).
    """
    databases: list[tuple[str, Path, list[Migration]]] = [
        ("feedback.db", DATA_DIR / "feedback.db", FEEDBACK_DB_MIGRATIONS),
        ("auth.db", DATA_DIR / "auth.db", AUTH_DB_MIGRATIONS),
        ("user_niches.db", DATA_DIR / "user_niches.db", NICHES_DB_MIGRATIONS),
    ]

    logger.info("-" * 50)
    logger.info("Migration engine started")
    logger.info("-" * 50)

    for label, path, mlist in databases:
        logger.info("Checking %s ...", label)
        _apply_migrations(label, path, mlist)

    logger.info("-" * 50)
    logger.info("All migrations complete")
    logger.info("-" * 50)
