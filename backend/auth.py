"""JWT-based authentication: signup, login, per-user API key generation."""

import os
import json
import hashlib
import secrets
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv(Path(__file__).parent / ".env")

try:
    import jwt
except ImportError:
    jwt = None

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "auth.db"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "taggenie-dev-secret-do-not-use-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# In-memory guest session store: maps session_id -> user_data
_guest_sessions: dict[str, dict] = {}

GUEST_SESSION_PREFIX = "gst_"


def init_auth_db():
    """Initialize the auth database with users and user_niches tables."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            api_key TEXT UNIQUE,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_niches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            niche_id TEXT NOT NULL,
            is_custom INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, niche_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL,
            called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _generate_api_key() -> str:
    return f"tg_{secrets.token_hex(24)}"


def signup(email: str, password: str) -> dict:
    """Create a new user account. Returns user info (no password)."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        api_key = _generate_api_key()
        password_hash = _hash_password(password)
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, api_key) VALUES (?, ?, ?)",
            (email, password_hash, api_key),
        )
        user_id = cursor.lastrowid
        conn.commit()
        return {"user_id": user_id, "email": email, "api_key": api_key}
    except sqlite3.IntegrityError:
        raise ValueError(f"User with email '{email}' already exists")
    finally:
        conn.close()


def authenticate(email: str, password: str) -> dict:
    """Authenticate a user and return user data."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        row = conn.execute(
            "SELECT id, email, api_key, usage_count FROM users WHERE email = ? AND password_hash = ?",
            (email, _hash_password(password)),
        ).fetchone()
        if row is None:
            raise ValueError("Invalid email or password")
        return {"user_id": row[0], "email": row[1], "api_key": row[2], "usage_count": row[3]}
    finally:
        conn.close()


def create_access_token(user_id: int, email: str) -> str:
    """Create a JWT access token."""
    if jwt is None:
        raise ImportError("PyJWT is required for authentication")
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """Verify a JWT token and return the payload."""
    if jwt is None:
        raise ImportError("PyJWT is required for authentication")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def add_user_niche(user_id: int, niche_id: str) -> bool:
    """Associate a niche with a user (for multi-tenant isolation)."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            "INSERT OR IGNORE INTO user_niches (user_id, niche_id) VALUES (?, ?)",
            (user_id, niche_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_user_niches(user_id: int) -> list[str]:
    """Get all niches associated with a user."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        rows = conn.execute(
            "SELECT niche_id FROM user_niches WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def log_usage(user_id: int, endpoint: str):
    """Log an API call for usage tracking."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            "INSERT INTO usage_log (user_id, endpoint) VALUES (?, ?)",
            (user_id, endpoint),
        )
        conn.execute(
            "UPDATE users SET usage_count = usage_count + 1 WHERE id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


def get_usage(user_id: int) -> dict:
    """Get usage stats for a user."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        current = conn.execute(
            "SELECT usage_count FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        this_month = conn.execute(
            "SELECT COUNT(*) FROM usage_log WHERE user_id = ? AND strftime('%Y-%m', called_at) = strftime('%Y-%m', 'now')",
            (user_id,),
        ).fetchone()
        return {
            "total": current[0] if current else 0,
            "this_month": this_month[0] if this_month else 0,
        }
    finally:
        conn.close()


def get_user_by_api_key(api_key: str) -> dict:
    """Look up a user by API key (for API-key-based auth)."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        row = conn.execute(
            "SELECT id, email, usage_count FROM users WHERE api_key = ?",
            (api_key,),
        ).fetchone()
        if row is None:
            return None
        return {"user_id": row[0], "email": row[1], "usage_count": row[2]}
    finally:
        conn.close()


# ── Guest sessions ──────────────────────────────────────────────────────────

def create_guest_session() -> dict:
    """Create an in-memory guest session. Returns guest user data + session_id."""
    session_id = GUEST_SESSION_PREFIX + uuid.uuid4().hex[:16]
    _guest_sessions[session_id] = {
        "session_id": session_id,
        "is_guest": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return _guest_sessions[session_id]


def get_guest_session(session_id: str):
    """Look up a guest session by session_id."""
    return _guest_sessions.get(session_id)


def delete_guest_session(session_id: str):
    _guest_sessions.pop(session_id, None)


# ── Auth helpers ────────────────────────────────────────────────────────────

def _resolve_user(credentials):
    """Internal: resolve credentials to a user dict, or raise HTTPException."""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide a Bearer token or use guest mode.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    if token.startswith(GUEST_SESSION_PREFIX):
        session = get_guest_session(token)
        if session is None:
            raise HTTPException(status_code=401, detail="Invalid or expired guest session.")
        return {"user_id": token, "email": f"guest@{token[:8]}", "is_guest": True}

    if jwt is None:
        raise HTTPException(status_code=500, detail="PyJWT is required for authentication")
    try:
        payload = verify_token(token)
        return {"user_id": int(payload["sub"]), "email": payload.get("email"), "is_guest": False}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ── FastAPI dependencies ────────────────────────────────────────────────────

def require_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    """FastAPI dependency: return the authenticated user or raise 401."""
    return _resolve_user(credentials)


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    """FastAPI dependency: return user if authenticated, else None (no error)."""
    if credentials is None:
        return None
    try:
        return _resolve_user(credentials)
    except HTTPException:
        return None
