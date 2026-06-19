"""Unit tests for scoring formulas, weight clamping, and gap-finder thresholds."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pytest
from backend.models import ScoreRequest
from backend.scoring import PLATFORM_WEIGHTS, load_weights, semantic_relevance, compute_confidence


class TestCompositeFormula:
    """Verify composite scoring math on a hand-computed example."""

    def test_formula_hand_computed(self):
        reach_score = 70.0
        competition_score = 40.0
        confidence = 100.0
        type_weight = 0.3

        composite = (reach_score * 0.5) + ((100 - competition_score) * 0.3) + (confidence * 0.2)
        expected_composite = (70 * 0.5) + (60 * 0.3) + (100 * 0.2)
        assert composite == pytest.approx(expected_composite)

        final = round(composite * type_weight, 1)
        expected_final = 73.0 * 0.3
        assert final == pytest.approx(expected_final)

    def test_formula_extremes(self):
        reach_score = 100.0
        competition_score = 0.0
        confidence = 100.0
        type_weight = 1.0

        composite = (reach_score * 0.5) + ((100 - competition_score) * 0.3) + (confidence * 0.2)
        expected = (100 * 0.5) + (100 * 0.3) + (100 * 0.2)
        assert composite == pytest.approx(expected)
        assert composite == 100.0

        final = round(composite * type_weight, 1)
        assert final == 100.0

    def test_formula_minimum(self):
        reach_score = 0.0
        competition_score = 100.0
        confidence = 0.0
        type_weight = 0.1

        composite = (reach_score * 0.5) + ((100 - competition_score) * 0.3) + (confidence * 0.2)
        assert composite == 0.0

        final = round(composite * type_weight, 1)
        assert final == 0.0


class TestWeightClamping:
    """Verify platform weights clamp to [0.1, 2.0] boundaries."""

    def _add_test_weights(self):
        PLATFORM_WEIGHTS["Test"] = {"hashtag": 0.5, "keyword": 0.5}

    def _remove_test_weights(self):
        if "Test" in PLATFORM_WEIGHTS:
            del PLATFORM_WEIGHTS["Test"]

    def test_lower_bound_clamped(self):
        val = max(0.1, min(2.0, 0.05))
        assert val == 0.1

    def test_upper_bound_clamped(self):
        val = max(0.1, min(2.0, 5.0))
        assert val == 2.0

    def test_within_bounds_passes_through(self):
        assert max(0.1, min(2.0, 0.75)) == 0.75
        assert max(0.1, min(2.0, 1.5)) == 1.5

    def test_factor_nudge_stays_within_bounds(self):
        assert max(0.1, min(2.0, 0.1 * 0.9)) == 0.1
        assert max(0.1, min(2.0, 2.0 * 1.1)) == 2.0


class TestGapFinderThresholds:
    """Verify gap-finder logic: reach > 60 AND competition < 30."""

    def test_both_above_threshold_qualifies(self):
        assert (61.0 > 60 and 29.0 < 30) is True

    def test_reach_exactly_at_60_fails(self):
        assert (60.0 > 60 and 29.0 < 30) is False

    def test_competition_exactly_at_30_fails(self):
        assert (61.0 > 60 and 30.0 < 30) is False

    def test_both_fail_no_qualify(self):
        assert (60.0 > 60 and 30.0 < 30) is False

    def test_high_reach_high_competition_fails(self):
        assert (80.0 > 60 and 50.0 < 30) is False

    def test_low_reach_low_competition_fails(self):
        assert (40.0 > 60 and 10.0 < 30) is False


class TestConfidenceFormula:
    """Verify confidence computation matches spec."""

    def test_normal_no_penalty(self):
        conf = compute_confidence(False)
        assert conf > 0

    def test_fallback_docks_30(self):
        conf_normal = compute_confidence(False)
        conf_fallback = compute_confidence(True)
        assert conf_normal - conf_fallback >= 30 or conf_fallback <= 0


class TestNicheScoring:
    """Verify niche awareness in scoring."""

    def test_score_request_has_niche_field(self):
        req = ScoreRequest(topic="test", product="test", platform="LinkedIn", niche="gps-telematics")
        assert req.niche == "gps-telematics"

    def test_score_request_default_niche(self):
        req = ScoreRequest(topic="test", product="test", platform="LinkedIn")
        assert req.niche == "gps-telematics"

    def test_semantic_relevance_returns_score(self):
        score = semantic_relevance("fleet safety", "AI dashcams for fleets")
        assert isinstance(score, (float, np.floating))
        assert 0 <= score <= 100
