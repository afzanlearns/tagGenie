from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from backend.models import ScoreRequest, ScoreResponse, FeedbackRequest, IngestRequest
from backend.scoring import score_topic, load_weights
from backend.baseline import score_baseline
from backend.cache import cache_key, get as cache_get, set as cache_set
from backend.feedback import init_db, seed_synthetic_feedback, log_feedback
from backend.scheduler import start_scheduler, shutdown_scheduler, trigger_recompute

_ingested_topics = []

VALID_PLATFORMS = {"LinkedIn", "Instagram", "X", "TikTok"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_synthetic_feedback()
    load_weights()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="TagGenie", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/score", response_model=ScoreResponse)
async def api_score(req: ScoreRequest):
    if req.platform not in VALID_PLATFORMS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid platform '{req.platform}'. Must be one of: {', '.join(sorted(VALID_PLATFORMS))}",
        )

    if req.include_baseline:
        ck = cache_key(req.topic, req.platform)
        cached = cache_get(ck)
        if cached is not None:
            cached["timings"] = {"cache_hit": True}
            return cached

    timings = {}
    t0 = time.time()

    t_ext = time.time()
    result = score_topic(req.topic, req.product, req.platform)
    timings["scoring_total"] = round(time.time() - t_ext, 3)

    t_base = time.time()
    if req.include_baseline:
        baseline = score_baseline(req.topic, req.product)
        result.baseline_tags = baseline
    timings["baseline"] = round(time.time() - t_base, 3)

    timings["total"] = round(time.time() - t0, 3)
    result.timings = timings

    if req.include_baseline:
        cache_set(cache_key(req.topic, req.platform), result)

    return result


@app.post("/api/feedback")
async def api_feedback(req: FeedbackRequest):
    log_feedback(
        req.post_id,
        req.platform,
        req.tags_used,
        req.engagement.likes,
        req.engagement.shares,
        req.engagement.comments,
    )
    return {"status": "logged"}


@app.post("/api/ingest-candidates")
async def api_ingest(req: IngestRequest):
    _ingested_topics.extend([t.model_dump() for t in req.topics])
    return {
        "status": "accepted",
        "count": len(req.topics),
        "total_stored": len(_ingested_topics),
    }


@app.get("/api/health")
async def api_health():
    return {"status": "ok"}


@app.post("/api/trigger-recompute")
async def api_trigger():
    trigger_recompute()
    return {"status": "recompute_triggered"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

