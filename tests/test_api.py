"""API integration tests covering all endpoints with valid and invalid payloads."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from backend.feedback import init_db, seed_synthetic_feedback
from backend.scoring import load_weights
from main import app

init_db()
seed_synthetic_feedback()
load_weights()

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_headers():
    """Get guest token for protected endpoints."""
    resp = client.get("/api/auth/guest")
    assert resp.status_code == 200
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


class TestScoreEndpoint:

    def test_valid_request(self, auth_headers):
        resp = client.post("/api/score", json={
            "topic": "AI dashcams for fleet safety",
            "product": "Vignan Dashcam AI",
            "platform": "LinkedIn",
            "niche": "gps-telematics",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "ranked_tags" in data
        assert "gap_tags" in data
        assert "confidence" in data
        assert "fallback_mode" in data
        assert "niche" in data
        assert len(data["ranked_tags"]) > 0

    def test_valid_request_default_niche(self, auth_headers):
        resp = client.post("/api/score", json={
            "topic": "GPS tracking for fleet",
            "product": "Tracker Pro",
            "platform": "LinkedIn",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["niche"] == "gps-telematics"

    def test_with_baseline(self, auth_headers):
        resp = client.post("/api/score", json={
            "topic": "real-time GPS telematics",
            "product": "AjnaView GPS",
            "platform": "Instagram",
            "niche": "gps-telematics",
            "include_baseline": True,
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "baseline_tags" in data
        assert len(data["baseline_tags"]) > 0
        assert "timings" in data

    def test_invalid_platform_returns_422(self, auth_headers):
        resp = client.post("/api/score", json={
            "topic": "test",
            "product": "test",
            "platform": "Discord",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_invalid_niche_returns_422(self, auth_headers):
        resp = client.post("/api/score", json={
            "topic": "test",
            "product": "test",
            "platform": "LinkedIn",
            "niche": "nonexistent-niche",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_missing_topic_returns_422(self, auth_headers):
        resp = client.post("/api/score", json={
            "product": "test",
            "platform": "LinkedIn",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_missing_product_returns_422(self, auth_headers):
        resp = client.post("/api/score", json={
            "topic": "test",
            "platform": "LinkedIn",
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_empty_topic(self, auth_headers):
        resp = client.post("/api/score", json={
            "topic": "",
            "product": "Vignan",
            "platform": "LinkedIn",
            "niche": "gps-telematics",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "ranked_tags" in data

    def test_long_topic(self, auth_headers):
        resp = client.post("/api/score", json={
            "topic": "advanced real-time computer vision for fleet driver behavior monitoring",
            "product": "Vignan Dashcam AI",
            "platform": "X",
            "niche": "gps-telematics",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "ranked_tags" in data

    def test_all_platforms(self, auth_headers):
        for platform in ["LinkedIn", "Instagram", "X", "TikTok"]:
            resp = client.post("/api/score", json={
                "topic": f"fleet safety for {platform}",
                "product": "Test Product",
                "platform": platform,
                "niche": "gps-telematics",
            }, headers=auth_headers)
            assert resp.status_code == 200


class TestFeedbackEndpoint:

    def test_valid_feedback(self, auth_headers):
        resp = client.post("/api/feedback", json={
            "post_id": "test_fb_001",
            "platform": "LinkedIn",
            "niche": "gps-telematics",
            "tags_used": ["fleet safety", "AI dashcams"],
            "engagement": {"likes": 100, "shares": 20, "comments": 10},
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "logged"

    def test_feedback_all_platforms(self, auth_headers):
        for platform in ["LinkedIn", "Instagram", "X", "TikTok"]:
            resp = client.post("/api/feedback", json={
                "post_id": f"test_{platform}",
                "platform": platform,
                "niche": "gps-telematics",
                "tags_used": ["test tag"],
                "engagement": {"likes": 10, "shares": 1, "comments": 1},
            }, headers=auth_headers)
            assert resp.status_code == 200

    def test_missing_engagement_returns_422(self, auth_headers):
        resp = client.post("/api/feedback", json={
            "post_id": "test",
            "platform": "LinkedIn",
            "niche": "gps-telematics",
            "tags_used": ["test"],
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_invalid_platform_returns_422(self, auth_headers):
        resp = client.post("/api/feedback", json={
            "post_id": "test",
            "platform": "Discord",
            "niche": "gps-telematics",
            "tags_used": ["test"],
            "engagement": {"likes": 1, "shares": 1, "comments": 1},
        }, headers=auth_headers)
        assert resp.status_code == 422


class TestNicheEndpoints:

    def test_list_niches(self, auth_headers):
        resp = client.get("/api/niches", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "niches" in data
        assert "active" in data
        assert len(data["niches"]) >= 3

    def test_switch_niche(self, auth_headers):
        resp = client.post("/api/niches/switch", json={"niche_id": "b2b-saas"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] == "b2b-saas"

        # Switch back
        client.post("/api/niches/switch", json={"niche_id": "gps-telematics"}, headers=auth_headers)

    def test_switch_invalid_niche(self, auth_headers):
        resp = client.post("/api/niches/switch", json={"niche_id": "nonexistent"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_niche_validation(self, auth_headers):
        resp = client.post("/api/niches/create", json={
            "niche_id": "test-niche",
            "display_name": "Test Niche",
            "description": "Testing",
            "sample_posts": ["only one post"],
        }, headers=auth_headers)
        assert resp.status_code == 422
        assert "20" in resp.json()["detail"]


class TestIngestEndpoint:

    def test_valid_ingest(self, auth_headers):
        resp = client.post("/api/ingest-candidates", json={
            "topics": [
                {"topic": "AI fleet management 2025", "momentum_score": 92.0},
                {"topic": "autonomous truck platooning", "momentum_score": 87.5},
            ]
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["count"] == 2

    def test_empty_topics_list(self, auth_headers):
        resp = client.post("/api/ingest-candidates", json={
            "topics": []
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0

    def test_missing_topics_returns_422(self, auth_headers):
        resp = client.post("/api/ingest-candidates", json={}, headers=auth_headers)
        assert resp.status_code == 422


class TestHealthEndpoint:

    def test_health_returns_ok(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestRecomputeEndpoint:

    def test_trigger_recompute(self, auth_headers):
        resp = client.post("/api/trigger-recompute", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "recompute_triggered"
