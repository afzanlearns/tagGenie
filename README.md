# TagGenie — Distribution Intelligence Engine

The Hashtag & Keyword Mining Agent for the Vignan/AjnaView 19-agent intern project set. An autonomous scoring agent that explains its decisions, finds competitive gaps, and learns from feedback over time.

## Why This Beats a Static Hashtag List

Static hashtag lists are dead on arrival — they don't know the current competitive density of a term, can't tell you which tags are underused blue-ocean opportunities, and never improve with real outcome data.

TagGenie scores every candidate tag against three axes simultaneously:

- **Reach** (trend volume + semantic relevance to your topic)
- **Competition** (embedding similarity density against a real fleet-tech post corpus — high score = crowded, avoid)
- **Confidence** (are we on real Google Trends data, or fallback? Is our corpus representative?)

A nightly feedback loop quietly ingests post performance (likes, shares, comments), compares actual engagement against predictions, and adjusts the platform weight matrix by ±10% — clamped to [0.1, 2.0]. The weights persist to `weights.json` and take effect on the next `/api/score` call without any manual intervention.

The **Gap Finder** — "Blue Ocean" tags where reach > 60 and competition < 30 — is surfaced as a first-class citizen in both the API response and the UI. This is the single most actionable output.

If pytrends rate-limits, the engine falls back to a static dataset and flags `fallback_mode: true`, which docks confidence by 30 points. Uncertainty is never hidden.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI (async) |
| Keyword Extraction | KeyBERT + spaCy (`en_core_web_sm`) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Vector Store | ChromaDB (cosine space, persistent) |
| LLM | Groq API, Llama 3.3 70B — rationale text only, never scoring math |
| Trends | pytrends (unofficial Google Trends) with static fallback |
| Storage | SQLite (`feedback.db`) |
| Scheduler | APScheduler, nightly weight recompute |
| Frontend | React 18 + Vite + Tailwind (utility classes only), Geist Mono |

## Project Structure

```
taggenie/
  backend/
    __init__.py
    extraction.py      # KeyBERT keyword extraction + spaCy noun chunks
    scoring.py         # Composite ranking, gap finder, platform weights
    baseline.py        # Naive TF-IDF baseline for comparison mode
    embeddings.py      # Sentence transformer + ChromaDB embed/query
    llm.py             # Groq semantic expansion + rationale generation
    trends.py          # pytrends Google Trends + static fallback
    feedback.py        # SQLite post feedback logging + analysis
    scheduler.py       # APScheduler nightly weight recompute job
    cache.py           # In-memory response cache (10-min TTL)
    models.py          # Pydantic request/response schemas
    requirements.txt
    .env               # GROQ_API_KEY=your_key_here
  frontend/
    src/
      App.jsx
      main.jsx
      components/
        InputPanel.jsx
        ResultsTable.jsx
        ScoreBar.jsx
        RationalePanel.jsx
        GapFinder.jsx
        FeedbackSimulator.jsx
        ComparisonView.jsx    # Side-by-side TagGenie vs baseline
        DemoMode.jsx          # Guided auto-run demo with 3 pre-loaded topics
      styles/tokens.css
  mocks/
    mock_trendradar_payload.json   # Realistic TrendRadar fixture
    mock_omnipost_consumer.py      # OmniPost publish payload formatter
  tests/
    test_scoring.py     # Composite formula, weight clamping, gap thresholds
    test_api.py         # All 5 endpoints, valid + invalid payloads
  data/
    sample_topics.json  # Static fallback trend data
    seed_corpus.json    # 60 fleet-tech social posts for ChromaDB
    weights.json        # Persisted platform weight matrix
    feedback.db         # Created at runtime
  main.py              # FastAPI entry point
  demo_pipeline.py     # TrendRadar → TagGenie → OmniPost integration demo
  validate_cli.py      # Phase 2 CLI validation against 5 test topics
  test_api.py          # Integration test for all endpoints
  test_feedback.py     # Feedback loop weight adjustment test
```

## Setup

```bash
# 1. Install Python dependencies
pip install -r backend/requirements.txt
python -m spacy download en_core_web_sm

# 2. Install frontend dependencies
cd frontend && npm install

# 3. Set Groq API key (optional — engine works without it, falls back gracefully)
echo "GROQ_API_KEY=gsk_your_api_key_here" > backend/.env

# 4. Seed ChromaDB with fleet-tech corpus + synthetic feedback data
python -c "from backend.embeddings import seed_corpus; print(f'Seeded {seed_corpus()} docs')"
python -c "from backend.feedback import init_db, seed_synthetic_feedback; init_db(); seed_synthetic_feedback(); print('Feedback DB ready')"
```

## Running

**Backend only:**
```bash
uvicorn main:app --reload --port 8000
```

**Full stack (terminal 1 + terminal 2):**
```bash
# Terminal 1: Backend
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend dev server
cd frontend && npm run dev
```

Frontend proxies `/api/*` to `localhost:8000`. Open `http://localhost:5173`.

## API Endpoints

### POST /api/score
```json
// Request
{ "topic": "AI dashcams for fleet safety", "product": "Vignan Dashcam AI", "platform": "LinkedIn" }

// Response
{
  "topic": "AI dashcams for fleet safety",
  "platform": "LinkedIn",
  "ranked_tags": [
    {
      "tag": "fleet safety vignan",
      "type": "keyword",
      "reach_score": 65.9,
      "competition_score": 37.9,
      "final_score": 65.6,
      "confidence": 70.0,
      "rationale": "High reach (66) with low saturation (38)..."
    }
  ],
  "gap_tags": [...],
  "confidence": 70.0,
  "fallback_mode": true
}
```

### POST /api/feedback
```json
{ "post_id": "post_001", "platform": "LinkedIn", "tags_used": ["fleet safety"], "engagement": { "likes": 120, "shares": 15, "comments": 8 } }
```

### POST /api/ingest-candidates
```json
{ "topics": [{ "topic": "autonomous truck platooning", "momentum_score": 87.5 }] }
```

### POST /api/trigger-recompute
Manually triggers the nightly weight adjustment job for testing.

## CLI Validation

```bash
python validate_cli.py
```

Scores 5 fleet-tech topics across different platforms and prints ranked output with rationales and gap analysis.

## 60-Second Demo Script

Exact sequence of clicks and narration beats — anyone can run this cold.

### Setup (before demo)
```bash
# Terminal 1: Backend
uvicorn main:app --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```
Open `http://localhost:5173` in a browser. Confirm "DEMO MODE" button is visible in header.

### The Demo (0:00 → 1:00)

| Time | Click | Narration |
|------|-------|-----------|
| 0:00 | Click **DEMO MODE** button | "TagGenie is an autonomous scoring agent — one of 19 agents in the Vignan/AjnaView intern set. It doesn't just suggest hashtags — it scores them against real competitive data, explains WHY, finds gaps nobody else is using, and learns from post performance automatically." |
| 0:05 | Click the first demo topic card: **"AI dashcams for fleet safety"** | "I've pre-loaded three fleet-tech topics. Watch what happens when I select one — the pipeline auto-runs every stage." |
| 0:10 | (Pipeline auto-advances — watch the stage list fill in) | "Seven stages fire in sequence: topic expansion through Groq LLM... scoring against trend volume, semantic relevance, and competition density... baseline comparison against plain TF-IDF... gap finding for under-served terms... rationale generation per tag... simulated feedback posting... and the weight shift that learns from it all." |
| 0:40 | When pipeline completes, switch to **COMPARISON** tab | "Here's the killer feature — side by side with a naive TF-IDF baseline. Same topic, same input. TagGenie finds fleet-specific compound terms the baseline can't see, and flags blue-ocean gaps with the diamond marker. The baseline has no competitive awareness, no trend data, no learning loop." |
| 0:50 | Switch to **BLUE OCEAN** tab | "These are the tags with high reach and low saturation — first-mover advantage opportunities the baseline completely misses." |
| 0:55 | Switch to **FEEDBACK SIM** tab, click **SIMULATE POST** | "And this closes the loop — every simulated post feeds the nightly weight recompute. The engine gets smarter every time someone posts with these tags." |

### Post-demo (if time allows)
```bash
# Prove the cross-agent integration story
python demo_pipeline.py
```
Shows `[STAGE]`-labeled output: TrendRadar ingest → TagGenie scoring → OmniPost publish payload.

### Cross-Agent Integration Pipeline
```bash
python demo_pipeline.py
```
Loads `mocks/mock_trendradar_payload.json` (simulating TrendRadar input), POSTs each topic to `/api/score`, and formats publish-ready payloads shaped for OmniPost consumption. Printed with clear `[STAGE]` labels for live narration.

## Design

- Canvas: #0C0C0C, Text: #F0EDE6, Accent: #D42B2B (primary actions + critical scores only)
- Border radius: 0px everywhere. No gradients. No box-shadows. No rounded corners.
- Font: Geist Mono, monospace alignment for all data tables
- Reference aesthetic: Linear, Vercel Dashboard

## Scoring Formulas

```
reach_score = (trend_volume * 0.6) + (semantic_relevance_to_topic * 0.4)
composite = (reach_score * 0.5) + ((100 - competition_score) * 0.3) + (confidence * 0.2)
final_score = composite * platform_weight_for_type
confidence = 100 - (fallback_mode ? 30 : 0) - (corpus < 20 ? 10 : 0)
```

Platform weight matrix (hardcoded, adjusted by feedback loop):

| Platform   | hashtag_weight | keyword_weight |
|------------|----------------|----------------|
| LinkedIn   | 0.3            | 1.0            |
| Instagram  | 1.0            | 0.4            |
| X          | 0.7            | 0.6            |
| TikTok     | 0.9            | 0.5            |

## What This Doesn't Do

- Doesn't use the LLM for scoring math — Groq writes rationale text only
- Doesn't fabricate engagement numbers as real — synthetic feedback is labeled "SIMULATED" in the UI
- Doesn't use card-shadow UI patterns, gradients, rounded corners, or Inter font
