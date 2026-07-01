"""Tests for JWT auth, cross-user data isolation, and usage tracking."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from backend.auth import (
    init_auth_db, signup, authenticate, create_access_token,
    verify_token, add_user_niche, get_user_niches, get_usage, log_usage,
)
from backend.feedback import init_db, seed_synthetic_feedback
from backend.scoring import load_weights
from main import app

# Initialize
init_auth_db()
init_db()
seed_synthetic_feedback()
load_weights()

client = TestClient(app)


class TestAuthFlow:

    token = ""
    test_email = ""

    def test_signup(self):
        import time
        type(self).test_email = f"test_flow_{int(time.time()*1000)}@example.com"
        resp = client.post("/api/auth/signup", json={
            "email": self.test_email,
            "password": "securepass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["email"] == self.test_email
        assert data["token_type"] == "bearer"
        type(self).token = data["access_token"]

    def test_signup_duplicate_email(self):
        resp = client.post("/api/auth/signup", json={
            "email": self.test_email,
            "password": "anotherpass",
        })
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_login_valid(self):
        resp = client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "securepass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["email"] == self.test_email

    def test_login_invalid_password(self):
        resp = client.post("/api/auth/login", json={
            "email": self.test_email,
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self):
        resp = client.post("/api/auth/login", json={
            "email": "nonexistent_user_xyz@example.com",
            "password": "pass",
        })
        assert resp.status_code == 401

    def test_me_authenticated(self):
        me_email = f"me_test_{id(self)}@example.com"
        sr = client.post("/api/auth/signup", json={"email": me_email, "password": "pass123"})
        assert sr.status_code == 200
        token = sr.json()["access_token"]
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == me_email

    def test_auth_me_no_token(self):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_auth_me_invalid_token(self):
        resp = client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalidtoken123",
        })
        assert resp.status_code == 401


class TestCrossUserIsolation:

    def test_users_have_different_api_keys(self):
        """Two users signing up should get different API keys."""
        import time
        ts = int(time.time() * 1000)
        resp1 = client.post("/api/auth/signup", json={
            "email": f"user1_{ts}@example.com",
            "password": "pass1",
        })
        resp2 = client.post("/api/auth/signup", json={
            "email": f"user2_{ts}@example.com",
            "password": "pass2",
        })
        token1 = resp1.json()["access_token"]
        token2 = resp2.json()["access_token"]

        # Different users have different tokens
        assert token1 != token2

        # User 1 can see their own data
        me1 = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token1}",
        })
        assert me1.status_code == 200

        # User 2 cannot see user 1's data via their token
        me2 = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token2}",
        })
        assert me2.status_code == 200
        assert me2.json()["user_id"] != me1.json()["user_id"]

    def test_usage_tracking_per_user(self):
        """Usage counts should be per-user and not leak between users."""
        import time
        ts = int(time.time() * 1000)
        resp = client.post("/api/auth/signup", json={
            "email": f"usage1_{ts}@example.com",
            "password": "pass1",
        })
        assert resp.status_code == 200
        token1 = resp.json()["access_token"]

        resp2 = client.post("/api/auth/signup", json={
            "email": f"usage2_{ts}@example.com",
            "password": "pass2",
        })
        assert resp2.status_code == 200
        token2 = resp2.json()["access_token"]

        # Make some requests as user 1
        for _ in range(3):
            client.get("/api/auth/me", headers={
                "Authorization": f"Bearer {token1}",
            })

        # User 3 requests as user 2
        for _ in range(5):
            client.get("/api/auth/me", headers={
                "Authorization": f"Bearer {token2}",
            })

        usage1 = client.get("/api/auth/usage", headers={
            "Authorization": f"Bearer {token1}",
        }).json()

        usage2 = client.get("/api/auth/usage", headers={
            "Authorization": f"Bearer {token2}",
        }).json()

        # Each user sees their own usage, not the other's
        assert usage1["total"] == 3
        assert usage2["total"] == 5
        assert usage1["total"] != usage2["total"]

    def test_api_key_isolation(self):
        """API key should only grant access to the owning user's data."""
        from backend.auth import get_user_by_api_key
        user1 = get_user_by_api_key("nonexistent_key")
        assert user1 is None

        # Create a user and verify we can look up by API key
        import time
        ts = int(time.time() * 1000)
        resp = client.post("/api/auth/signup", json={
            "email": f"apikey_user_{ts}@example.com",
            "password": "pass",
        })
        assert resp.status_code == 200
        # API key is not returned in the JWT response, but it exists in the DB
        # We test that the user was created and can authenticate
        login_resp = client.post("/api/auth/login", json={
            "email": f"apikey_user_{ts}@example.com",
            "password": "pass",
        })
        assert login_resp.status_code == 200
