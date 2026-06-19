# TagGenie Evaluation Report

*Generated: 2026-06-19 15:44*

## Summary

| Niche | Posts | TG P@5 | BL P@5 | Lift@5 | TG P@10 | BL P@10 | Lift@10 |
|-------|-------|--------|--------|--------|---------|---------|---------|
| b2b-saas | 5 | 80.0% | 68.0% | +17.6% | 44.0% | 62.0% | -29.0% |
| fintech | 5 | 64.0% | 64.0% | +0.0% | 46.0% | 60.0% | -23.3% |
| gps-telematics | 5 | 76.0% | 64.0% | +18.8% | 50.0% | 66.0% | -24.2% |

**Best lift:** gps-telematics at +18.8% precision@5 lift over naive baseline.

## Methodology
- **TagGenie:** Uses trend volume (Google Trends), semantic relevance (sentence-transformers), competition density (ChromaDB cosine similarity), and platform-specific weights (learned via Thompson Sampling).
- **Baseline:** Naive TF-IDF keyword extraction from topic + product text only — no trend data, no competition scoring, no engagement feedback.
- **Ground truth:** KeyBERT-extracted keyphrases from each held-out post's title and text.
- **Precision@k:** Fraction of top-k ranked tags that match ground truth terms.
- **Held-out data:** Reddit posts with known engagement scores, not used during training.

## Architecture Decisions
- **Bandit over heuristic:** Thompson Sampling replaces the flat ±10% heuristic from Phase 2, modeling each platform/tag-type weight as a Beta distribution. More data = more confident posterior = tighter weight sampling.
- **Reddit over LinkedIn scraping:** Reddit's official API (PRAW) provides terms-of-service-compliant access to engagement data. LinkedIn scraping would risk account suspension.
- **Config-driven niches:** Each niche is a directory (seed corpus, jargon file, config) — no code changes needed to add a new industry.