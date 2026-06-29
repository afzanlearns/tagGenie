"""Validate the new ranking engine."""

from backend.ranking import (
    normalise_tag, deduplicate, compute_platform_fit,
    compute_semantic_relevance, compute_profile_confidence,
    compute_trend_score, compute_low_competition,
)


def test_deduplication():
    candidates = [
        {"tag": "coffee farmers", "type": "keyword", "semantic_relevance": 73.0},
        {"tag": "coffeefarmers", "type": "hashtag", "semantic_relevance": 65.0},
        {"tag": "coffee lover", "type": "keyword", "semantic_relevance": 80.0},
        {"tag": "coffeelover", "type": "hashtag", "semantic_relevance": 78.0},
    ]
    deduped = deduplicate(candidates)
    assert len(deduped) == 2, f"Expected 2, got {len(deduped)}"
    tags = [d["tag"] for d in deduped]
    assert "coffee farmers" in tags
    assert "coffee lover" in tags
    assert "coffeefarmers" not in tags
    assert "coffeelover" not in tags
    print("  [OK] Deduplication keeps best variant")


def test_platform_fit():
    ig_hash = compute_platform_fit("coffee", "hashtag", "Instagram")
    ig_kw = compute_platform_fit("coffee", "keyword", "Instagram")
    li_hash = compute_platform_fit("coffee", "hashtag", "LinkedIn")
    li_kw = compute_platform_fit("coffee", "keyword", "LinkedIn")
    assert ig_hash > li_hash, "Instagram should prefer hashtags over LinkedIn"
    assert li_kw > ig_kw, "LinkedIn should prefer keywords over Instagram"
    print("  [OK] Platform fit preferences correct")


def test_platform_boost_patterns():
    tiktok = compute_platform_fit("coffeetok", "hashtag", "TikTok")
    vanilla = compute_platform_fit("coffee", "hashtag", "TikTok")
    assert tiktok > vanilla, "coffeetok should get TikTok boost"
    print("  [OK] Platform boost patterns work")


def test_semantic_relevance():
    rel = compute_semantic_relevance("specialty coffee", "coffee", "coffee beans")
    low = compute_semantic_relevance("business", "coffee", "coffee beans")
    assert rel > low, "specialty coffee should be more relevant than business"
    assert 0 <= rel <= 100
    print("  [OK] Semantic relevance ranges correctly")


def test_low_competition():
    assert compute_low_competition(80.0) == 20.0
    assert compute_low_competition(20.0) == 80.0
    assert compute_low_competition(0.0) == 100.0
    print("  [OK] Low competition computed correctly")


def test_trend_score():
    assert compute_trend_score(85.0) == 85.0
    assert compute_trend_score(120.0) == 100.0
    assert compute_trend_score(-5.0) == 0.0
    print("  [OK] Trend score clamped correctly")


def test_profile_confidence():
    conf = compute_profile_confidence("gps-telematics")
    assert 0 <= conf <= 100
    print(f"  [OK] Profile confidence computed: {conf}")


def test_normalise_tag():
    assert normalise_tag("Coffee Farmers") == "coffeefarmers"
    assert normalise_tag("coffeefarmers") == "coffeefarmers"
    assert normalise_tag("  Coffee Farmers  ") == "coffeefarmers"
    print("  [OK] Tag normalisation strips spaces and lowercases")
