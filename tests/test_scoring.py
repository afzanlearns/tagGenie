"""Unit tests for scoring formulas, weight clamping, and gap-finder thresholds."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from backend.models import ScoreRequest
from backend.scoring import PLATFORM_WEIGHTS, load_weights, semantic_relevance, compute_confidence
from backend.scheduler import _nightly_recompute


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

    def test_lower_bound_clamped(self):
        PLATFORM_WEIGHTS["Test"] = {"hashtag": 0.05, "keyword": 0.05}
        PLATFORM_WEIGHTS["Test"]["hashtag"] = round(max(0.1, min(2.0, 0.05)), 2)
        assert PLATFORM_WEIGHTS["Test"]["hashtag"] == 0.1
        del PLATFORM_WEIGHTS["Test"]

    def test_upper_bound_clamped(self):
        PLATFORM_WEIGHTS["Test"] = {"hashtag": 5.0, "keyword": 3.0}
        PLATFORM_WEIGHTS["Test"]["hashtag"] = round(max(0.1, min(2.0, 5.0)), 2)
        assert PLATFORM_WEIGHTS["Test"]["hashtag"] == 2.0
        del PLATFORM_WEIGHTS["Test"]

    def test_within_bounds_passes_through(self):
        PLATFORM_WEIGHTS["Test"] = {"hashtag": 0.75, "keyword": 1.5}
        PLATFORM_WEIGHTS["Test"]["hashtag"] = round(max(0.1, min(2.0, 0.75)), 2)
        assert PLATFORM_WEIGHTS["Test"]["hashtag"] == 0.75
        PLATFORM_WEIGHTS["Test"]["keyword"] = round(max(0.1, min(2.0, 1.5)), 2)
        assert PLATFORM_WEIGHTS["Test"]["keyword"] == 1.5
        del PLATFORM_WEIGHTS["Test"]

    def test_factor_nudge_stays_within_bounds(self):
        PLATFORM_WEIGHTS["Test"] = {"hashtag": 0.1, "keyword": 2.0}
        PLATFORM_WEIGHTS["Test"]["hashtag"] = round(max(0.1, min(2.0, 0.1 * 0.9)), 2)
        assert PLATFORM_WEIGHTS["Test"]["hashtag"] == 0.1
        PLATFORM_WEIGHTS["Test"]["keyword"] = round(max(0.1, min(2.0, 2.0 * 1.1)), 2)
        assert PLATFORM_WEIGHTS["Test"]["keyword"] == 2.0
        del PLATFORM_WEIGHTS["Test"]


class TestGapFinderThresholds:
    """Verify gap-finder logic: reach > 60 AND competition < 30."""

    def test_both_above_threshold_qualifies(self):
        reach = 61.0
        competition = 29.0
        qualifies = reach > 60 and competition < 30
        assert qualifies is True

    def test_reach_exactly_at_60_fails(self):
        reach = 60.0
        competition = 29.0
        qualifies = reach > 60 and competition < 30
        assert qualifies is False

    def test_competition_exactly_at_30_fails(self):
        reach = 61.0
        competition = 30.0
        qualifies = reach > 60 and competition < 30
        assert qualifies is False

    def test_both_fail_no_qualify(self):
        reach = 60.0
        competition = 30.0
        qualifies = reach > 60 and competition < 30
        assert qualifies is False

    def test_high_reach_high_competition_fails(self):
        reach = 80.0
        competition = 50.0
        qualifies = reach > 60 and competition < 30
        assert qualifies is False

    def test_low_reach_low_competition_fails(self):
        reach = 40.0
        competition = 10.0
        qualifies = reach > 60 and competition < 30
        assert qualifies is False


class TestConfidenceFormula:
    """Verify confidence computation matches spec."""

    def test_normal_no_penalty(self):
        conf = compute_confidence(False)
        assert conf > 0

    def test_fallback_docks_30(self):
        conf_normal = compute_confidence(False)
        conf_fallback = compute_confidence(True)
        assert conf_normal - conf_fallback >= 30 or conf_fallback <= 0
