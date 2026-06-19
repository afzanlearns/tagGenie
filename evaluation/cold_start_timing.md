# Cold-Start Timing Validation

*Generated: 2026-06-19*

## Objective
Confirm the startup model pre-loading (sentence-transformers + spaCy + KeyBERT) eliminates the ~32s model-loading penalty on the first live scoring request, bringing the very first request into an acceptable range for live demos.

## Methodology
1. Kill any running server process.
2. Start server fresh (uvicorn → model pre-loading occurs in lifespan event).
3. Wait for `/api/health` to respond 200 OK.
4. Issue two POST `/api/score` requests with **different topics** on the same niche (`gps-telematics`) and platform (`LinkedIn`). Using distinct topics rules out the response cache — any speedup is due to warm inference.
5. Record elapsed wall-clock time for both requests.

## Results

| Request | Topic | Elapsed | Notes |
|---------|-------|:-:|-------|
| 1 (first ever) | "electric vehicle fleet sustainability" | **5.8s** | First scoring request after cold restart. Models pre-loaded at startup, but ChromaDB seeds its corpus, KeyBERT runs first extraction, LLM generates rationales. |
| 2 (warm, diff topic) | "last mile delivery route optimization" | **1.6s** | Genuine warm inference — different topic, no cache hit. ChromaDB already seeded, KeyBERT warm, sentence-transformers cached. |

## Interpretation

| Measurement | Observed | Acceptable for demo? |
|-------------|----------|:--------------------:|
| Server startup (includes model loading) | ~37s | Yes — happens once before any requests |
| First `/api/score` request | 5.8s | **Yes** — well below the 30+ second penalty without pre-loading |
| Second `/api/score` (warm, diff topic) | 1.6s | **Yes** — comfortably within the 3-4s normal range |

## Verdict
> **PASS** — The startup pre-loading fix reduces the first-request latency from ~35s (32s model load + 3s scoring) to **5.8s** (scoring pipeline only). Warm subsequent requests land at **1.6s**, well within the expected 3-4s range. Both figures are acceptable for live demos: the 5.8s first request is noticeable but not jarring, and all subsequent requests complete in ~1-2s.
