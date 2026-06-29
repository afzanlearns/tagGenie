"""Validate platform-specific ranking and diversity."""

from backend.scoring import score_topic


def test_coffee_instagram_ranks_hashtags_higher_than_linkedin():
    ig = score_topic("coffee", "coffee beans", "Instagram", "coffee", user_id=None)
    li = score_topic("coffee", "coffee beans", "LinkedIn", "coffee", user_id=None)

    def avg_ht_rank(tags):
        ht_ranks = [i for i, t in enumerate(tags) if t.type == "hashtag"]
        return sum(ht_ranks) / len(ht_ranks) if ht_ranks else 99

    ig_ht_avg = avg_ht_rank(ig.ranked_tags[:10])
    li_ht_avg = avg_ht_rank(li.ranked_tags[:10])

    assert ig_ht_avg < li_ht_avg, (
        f"Instagram should rank hashtags higher than LinkedIn does"
        f" (IG avg ht rank={ig_ht_avg:.1f}, LI avg ht rank={li_ht_avg:.1f})"
    )
    print(f"  [OK] Instagram avg hashtag rank: {ig_ht_avg:.1f} vs LinkedIn: {li_ht_avg:.1f}")


def test_coffee_linkedin_ranks_keywords_higher_than_instagram():
    ig = score_topic("coffee", "coffee beans", "Instagram", "coffee", user_id=None)
    li = score_topic("coffee", "coffee beans", "LinkedIn", "coffee", user_id=None)

    def avg_kw_rank(tags):
        kw_ranks = [i for i, t in enumerate(tags) if t.type == "keyword"]
        return sum(kw_ranks) / len(kw_ranks) if kw_ranks else 99

    ig_kw_avg = avg_kw_rank(ig.ranked_tags[:10])
    li_kw_avg = avg_kw_rank(li.ranked_tags[:10])

    assert li_kw_avg < ig_kw_avg, (
        f"LinkedIn should rank keywords higher than Instagram does"
        f" (LI avg kw rank={li_kw_avg:.1f}, IG avg kw rank={ig_kw_avg:.1f})"
    )
    print(f"  [OK] LinkedIn avg keyword rank: {li_kw_avg:.1f} vs Instagram: {ig_kw_avg:.1f}")


def test_platforms_produce_different_orderings():
    ig = score_topic("coffee", "coffee beans", "Instagram", "coffee", user_id=None)
    li = score_topic("coffee", "coffee beans", "LinkedIn", "coffee", user_id=None)
    tiktok = score_topic("coffee", "coffee beans", "TikTok", "coffee", user_id=None)

    ig_top5 = [t.tag for t in ig.ranked_tags[:5]]
    li_top5 = [t.tag for t in li.ranked_tags[:5]]
    tk_top5 = [t.tag for t in tiktok.ranked_tags[:5]]

    assert ig_top5 != li_top5, "Instagram and LinkedIn should have different rankings"
    assert li_top5 != tk_top5, "LinkedIn and TikTok should have different rankings"
    print(f"  [OK] IG top: {ig_top5}")
    print(f"  [OK] LI top: {li_top5}")
    print(f"  [OK] TK top: {tk_top5}")


def test_scores_have_meaningful_spread():
    r = score_topic("coffee", "coffee beans", "Instagram", "coffee", user_id=None)
    scores = [t.final_score for t in r.ranked_tags[:5]]
    spread = max(scores) - min(scores)
    assert spread > 5.0, (
        f"Scores too tightly clustered: {scores} (spread={spread:.1f})"
    )
    print(f"  [OK] Score spread: {spread:.1f} pts ({scores})")


def test_explanations_use_actual_values():
    r = score_topic("coffee", "coffee beans", "Instagram", "coffee", user_id=None)
    for t in r.ranked_tags[:3]:
        assert t.explanation, f"Missing explanation for {t.tag}"
        assert str(int(t.semantic_relevance)) in t.explanation or str(round(t.semantic_relevance)) in t.explanation, (
            f"Explanation for {t.tag} doesn't reference relevance ({t.semantic_relevance}): {t.explanation}"
        )
    print("  [OK] Explanations reference actual metric values")
