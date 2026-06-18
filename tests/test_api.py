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


class TestScoreEndpoint:

    def test_valid_request(self):
        resp = client.post("/api/score", json={
            "topic": "AI dashcams for fleet safety",
            "product": "Vignan Dashcam AI",
            "platform": "LinkedIn",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "ranked_tags" in data
        assert "gap_tags" in data
        assert "confidence" in data
        assert "fallback_mode" in data
        assert len(data["ranked_tags"]) > 0

    def test_with_baseline(self):
        resp = client.post("/api/score", json={
            "topic": "real-time GPS telematics",
            "product": "AjnaView GPS",
            "platform": "Instagram",
            "include_baseline": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "baseline_tags" in data
        assert len(data["baseline_tags"]) > 0
        assert "timings" in data

    def test_invalid_platform_returns_422(self):
        resp = client.post("/api/score", json={
            "topic": "test",
            "product": "test",
            "platform": "Discord",
        })
        assert resp.status_code == 422

    def test_missing_topic_returns_422(self):
        resp = client.post("/api/score", json={
            "product": "test",
            "platform": "LinkedIn",
        })
        assert resp.status_code == 422

    def test_missing_product_returns_422(self):
        resp = client.post("/api/score", json={
            "topic": "test",
            "platform": "LinkedIn",
        })
        assert resp.status_code == 422

    def test_empty_topic(self):
        resp = client.post("/api/score", json={
            "topic": "",
            "product": "Vignan",
            "platform": "LinkedIn",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "ranked_tags" in data

    def test_long_topic(self):
        resp = client.post("/api/score", json={
            "topic": "advanced real-time computer vision for fleet driver behavior monitoring",
            "product": "Vignan Dashcam AI",
            "platform": "X",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "ranked_tags" in data

    def test_all_platforms(self):
        for platform in ["LinkedIn", "Instagram", "X", "TikTok"]:
            resp = client.post("/api/score", json={
                "topic": f"fleet safety for {platform}",
                "product": "Test Product",
                "platform": platform,
            })
            assert resp.status_code == 200


class TestFeedbackEndpoint:

    def test_valid_feedback(self):
        resp = client.post("/api/feedback", json={
            "post_id": "test_fb_001",
            "platform": "LinkedIn",
            "tags_used": ["fleet safety", "AI dashcams"],
            "engagement": {"likes": 100, "shares": 20, "comments": 10},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "logged"

    def test_feedback_all_platforms(self):
        for platform in ["LinkedIn", "Instagram", "X", "TikTok"]:
            resp = client.post("/api/feedback", json={
                "post_id": f"test_{platform}",
                "platform": platform,
                "tags_used": ["test tag"],
                "engagement": {"likes": 10, "shares": 1, "comments": 1},
            })
            assert resp.status_code == 200

    def test_missing_engagement_returns_422(self):
        resp = client.post("/api/feedback", json={
            "post_id": "test",
            "platform": "LinkedIn",
            "tags_used": ["test"],
        })
        assert resp.status_code == 422

    def test_invalid_platform_returns_422(self):
        resp = client.post("/api/feedback", json={
            "post_id": "test",
            "platform": "Discord",
            "tags_used": ["test"],
            "engagement": {"likes": 1, "shares": 1, "comments": 1},
        })
        assert resp.status_code == 422


class TestIngestEndpoint:

    def test_valid_ingest(self):
        resp = client.post("/api/ingest-candidates", json={
            "topics": [
                {"topic": "AI fleet management 2025", "momentum_score": 92.0},
                {"topic": "autonomous truck platooning", "momentum_score": 87.5},
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["count"] == 2

    def test_empty_topics_list(self):
        resp = client.post("/api/ingest-candidates", json={
            "topics": []
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0

    def test_missing_topics_returns_422(self):
        resp = client.post("/api/ingest-candidates", json={})
        assert resp.status_code == 422


class TestHealthEndpoint:

    def test_health_returns_ok(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestRecomputeEndpoint:

    def test_trigger_recompute(self):
        resp = client.post("/api/trigger-recompute")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "recompute_triggered"
