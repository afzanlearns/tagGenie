# TagGenie

**Distribution intelligence for content tagging.** TagGenie scores hashtags and keywords on real reach and competition signals, explains its own reasoning, and learns from outcomes over time — instead of guessing.

---

## Overview

Most hashtag and keyword tools work off frequency counts: pull the most common terms for a topic and call it a recommendation. TagGenie takes a different approach. For any topic and platform, it estimates real-world reach using search trend data, measures how saturated a term already is by comparing it against a corpus of existing posts in the same industry, and weights everything according to platform-specific behavior — a hashtag-heavy strategy that works on Instagram actively hurts performance on LinkedIn, and TagGenie's scoring reflects that asymmetry rather than treating every platform the same.

Beyond ranking, TagGenie surfaces a dedicated **gap list**: terms with strong reach and low competition, the recommendations most likely to be worth acting on. Every top-ranked tag comes with a short, numbers-grounded explanation of why it scored the way it did, so the system's reasoning is visible rather than a black box.

TagGenie is also built to plug into a larger content pipeline rather than operate in isolation. It can ingest trending topics from an upstream discovery agent and feed its ranked output downstream to a content generation or publishing system, acting as the distribution-intelligence layer between topic discovery and content delivery.

---

## How It Works

**Extraction.** Candidate keywords and hashtags are generated using KeyBERT and spaCy, working against a topic that's first expanded by an LLM to surface industry-specific terminology a generic extractor would miss.

**Reach scoring.** Each candidate is scored against real Google Trends interest data, normalized and blended with semantic relevance to the original topic. If trend data is unavailable, the system falls back to a static reference dataset and flags the response accordingly, so reduced confidence is always visible rather than silent.

**Competition scoring.** Candidates are embedded and compared against a seed corpus of real posts from the relevant industry using vector similarity search. Higher similarity density means a term is already saturated; lower density signals room to stand out.

**Platform weighting.** A weight matrix adjusts each candidate's score based on platform and type (hashtag vs. keyword), reflecting how differently LinkedIn, Instagram, X, and TikTok reward each format.

**Composite ranking.** Reach, inverse competition, and confidence are combined into a single ranking formula, scaled by the platform weight, to produce the final ordered recommendation list.

**Gap finding.** Candidates with high reach and low competition are pulled out into a separate, prioritized "blue ocean" list — the system's highest-confidence recommendations.

**Explainability.** The top-ranked candidates each receive a one-line, LLM-generated rationale grounded strictly in their computed scores, not invented claims.

---

## Adaptive Learning

TagGenie logs how posts using its recommended tags actually perform — both real engagement data pulled from public sources and clearly-labeled synthetic data for testing — and uses that feedback to improve over time. Rather than a fixed adjustment rule, platform and tag-type weights are modeled as Beta distributions and updated nightly using Thompson Sampling, giving the system a principled way to balance exploring uncertain recommendations against exploiting ones it's already confident about. The result is a scoring system that gets sharper the more it's used, rather than one that's static from day one.

---

## Multi-Industry Support

TagGenie isn't tied to a single vertical. It ships with pre-configured niches — each with its own seed corpus, industry jargon mapping, and isolated vector collection — and supports creating new niches from scratch: paste a sample of posts from any industry, and the system generates a starter corpus and jargon list for review before saving. This makes TagGenie a configurable platform rather than a single-purpose script, usable anywhere distribution intelligence matters, not just the industry it was first built for.

---

## Proof of Value

TagGenie includes an honest, side-by-side comparison against a standard TF-IDF keyword baseline — not a deliberately weakened strawman — so the value of its scoring approach is visible directly in the interface rather than asserted. It also includes a formal evaluation harness that backtests ranking quality against held-out historical data, computing precision at top-5 and top-10 against the same baseline. Current results are documented in `evaluation/results.md`.

---

## Architecture & Tech Stack

| Layer | Technology |
|---|---|
| API | Python, FastAPI |
| Extraction | KeyBERT, spaCy |
| Embeddings & vector search | sentence-transformers, ChromaDB |
| Reasoning & explainability | Groq (Llama 3.3 70B) |
| Trend signal | Google Trends (pytrends), with static fallback |
| Real engagement data | Reddit API (PRAW) |
| Adaptive weighting | Thompson Sampling (Beta-distribution bandit) |
| Persistence | SQLite |
| Scheduling | APScheduler |
| Auth | JWT, per-user API keys |
| Frontend | React 18, Vite, Tailwind |

```
taggenie/
├── backend/
│   ├── extraction.py        # candidate generation
│   ├── embeddings.py        # vector search & competition scoring
│   ├── trends.py             # reach scoring
│   ├── scoring.py            # composite ranking & gap finder
│   ├── baseline.py           # TF-IDF comparison engine
│   ├── llm.py                 # expansion & rationale generation
│   ├── feedback.py           # engagement logging
│   ├── reddit_ingest.py      # real engagement data collection
│   ├── scheduler.py          # nightly bandit weight recompute
│   ├── auth.py                # JWT auth & multi-tenancy
│   ├── cache.py               # response caching
│   └── models.py             # request/response schemas
├── niches/                   # per-industry config: corpus, jargon, settings
├── evaluation/                # backtesting harness & results
├── mocks/                     # upstream/downstream integration fixtures
├── frontend/
│   └── src/components/        # dashboard, comparison view, demo mode
├── tests/
├── demo_pipeline.py            # end-to-end cross-agent integration demo
├── CASE_STUDY.md
└── README.md
```

---

## Getting Started

**Backend**
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# configure .env with GROQ_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
# REDDIT_USER_AGENT, and JWT_SECRET
uvicorn main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

---

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/score` | Score and rank tags for a topic, platform, and niche |
| `POST /api/feedback` | Log real or simulated post engagement |
| `POST /api/ingest-candidates` | Accept trending topics from an upstream discovery agent |
| `POST /api/trigger-recompute` | Manually trigger the adaptive weight recompute job |
| `POST /api/auth/signup`, `/login` | Account creation and authentication |
| `GET /health` | Service health check |

Full request/response schemas are defined in `backend/models.py`.

---

## Testing

The project includes a full automated test suite covering scoring logic, API contract validation, and authentication/data isolation:

```bash
pytest tests/ -v
```

An end-to-end integration script (`demo_pipeline.py`) validates the full upstream-to-downstream pipeline using realistic mock payloads, and a guided in-app demo mode walks through the scoring, gap-finding, explainability, and feedback-adjustment flow on pre-selected topics for live presentation.

---

## Design

The interface follows a deliberate brutalist-minimal system: near-black canvas, high-contrast cream text, a single red accent reserved for primary actions and critical signals, zero border-radius, and Geist Mono throughout. No gradients, no shadows, no decorative animation — the aesthetic prioritizes legibility and confidence in the data over visual noise.