# TagGenie Evaluation Report

*Generated: 2026-06-19 16:52*

## Summary

| Niche | Posts | TG P@5 | BL P@5 | Lift@5 | TG P@10 | BL P@10 | Lift@10 |
|-------|-------|--------|--------|--------|---------|---------|---------|
| b2b-saas | 10 | 80.0% | 60.0% | +33.3% | 55.0% | 62.0% | -11.3% |
| fintech | 10 | 66.0% | 54.0% | +22.2% | 45.0% | 60.0% | -25.0% |
| gps-telematics | 10 | 80.0% | 54.0% | +48.1% | 57.0% | 63.0% | -9.5% |

**Best lift:** gps-telematics at +48.1% precision@5 lift over naive baseline.

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