from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import time

from backend.models import (
    ScoreRequest, ScoreResponse, FeedbackRequest, IngestRequest,
    CreateNicheRequest, SignupRequest, LoginRequest, AuthResponse,
)
from backend.scoring import score_topic, load_weights
from backend.baseline import score_baseline
from backend.cache import cache_key, get as cache_get, set as cache_set
from backend.feedback import init_db, seed_synthetic_feedback, log_feedback, get_feedback_by_niche
from backend.scheduler import start_scheduler, shutdown_scheduler, trigger_recompute, get_beta_summary
from backend.niche_manager import (
    get_available_niches, get_niche_config, set_active_niche,
    get_active_niche, create_custom_niche,
)
from backend.auth import (
    init_auth_db, signup, authenticate, create_access_token,
    verify_token, log_usage, get_usage, get_user_by_api_key,
)

_ingested_topics = []

VALID_PLATFORMS = {"LinkedIn", "Instagram", "X", "TikTok"}
security = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_auth_db()
    seed_synthetic_feedback()
    load_weights()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="TagGenie", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract the authenticated user from the Authorization header."""
    if credentials is None:
        return None
    try:
        payload = verify_token(credentials.credentials)
        return {"user_id": int(payload["sub"]), "email": payload.get("email")}
    except Exception:
        return None


@app.post("/api/auth/signup")
async def api_signup(req: SignupRequest):
    try:
        user = signup(req.email, req.password)
        token = create_access_token(user["user_id"], user["email"])
        return AuthResponse(
            access_token=token, user_id=user["user_id"], email=user["email"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def api_login(req: LoginRequest):
    try:
        user = authenticate(req.email, req.password)
        token = create_access_token(user["user_id"], user["email"])
        return AuthResponse(
            access_token=token, user_id=user["user_id"], email=user["email"]
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get("/api/auth/me")
async def api_me(current_user: dict = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    log_usage(current_user["user_id"], "/api/auth/me")
    return current_user


@app.get("/api/auth/usage")
async def api_usage(current_user: dict = Depends(get_current_user)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return get_usage(current_user["user_id"])


@app.post("/api/score", response_model=ScoreResponse)
async def api_score(
    req: ScoreRequest,
    current_user: dict = Depends(get_current_user),
):
    if req.platform not in VALID_PLATFORMS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid platform '{req.platform}'. Must be one of: {', '.join(sorted(VALID_PLATFORMS))}",
        )

    niche_id = req.niche or get_active_niche()
    if get_niche_config(niche_id) is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown niche '{niche_id}'. Available: {[n['niche_id'] for n in get_available_niches()]}",
        )

    if current_user:
        log_usage(current_user["user_id"], "/api/score")

    if req.include_baseline:
        ck = cache_key(f"{niche_id}:{req.topic}", req.platform)
        cached = cache_get(ck)
        if cached is not None:
            cached["timings"] = {"cache_hit": True}
            return cached

    timings = {}
    t0 = time.time()

    t_ext = time.time()
    result = score_topic(req.topic, req.product, req.platform, niche_id)
    timings["scoring_total"] = round(time.time() - t_ext, 3)

    t_base = time.time()
    if req.include_baseline:
        baseline = score_baseline(req.topic, req.product, niche_id)
        result.baseline_tags = baseline
    timings["baseline"] = round(time.time() - t_base, 3)

    timings["total"] = round(time.time() - t0, 3)
    result.timings = timings

    if req.include_baseline:
        cache_set(cache_key(f"{niche_id}:{req.topic}", req.platform), result)

    return result


@app.get("/api/niches")
async def api_list_niches():
    return {"niches": get_available_niches(), "active": get_active_niche()}


@app.post("/api/niches/switch")
async def api_switch_niche(data: dict):
    niche_id = data.get("niche_id", "")
    if not set_active_niche(niche_id):
        raise HTTPException(status_code=422, detail=f"Unknown niche '{niche_id}'")
    return {"niche": get_niche_config(niche_id), "active": niche_id}


@app.post("/api/niches/create")
async def api_create_niche(req: CreateNicheRequest):
    if len(req.sample_posts) < 20:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 20 sample posts, got {len(req.sample_posts)}",
        )
    if get_niche_config(req.niche_id) is not None:
        raise HTTPException(
            status_code=422,
            detail=f"Niche '{req.niche_id}' already exists",
        )

    config = create_custom_niche(
        req.niche_id, req.display_name, req.description, req.sample_posts
    )
    return {"status": "created", "niche": config}


@app.post("/api/feedback")
async def api_feedback(req: FeedbackRequest):
    log_feedback(
        req.post_id,
        req.platform,
        req.tags_used,
        req.engagement.likes,
        req.engagement.shares,
        req.engagement.comments,
        req.niche,
        source="simulated",
    )
    return {"status": "logged"}


@app.get("/api/feedback/{niche}")
async def api_feedback_history(niche: str):
    return {"posts": get_feedback_by_niche(niche)}


@app.get("/api/beta-summary")
async def api_beta_summary():
    return {"beta_params": get_beta_summary()}


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
