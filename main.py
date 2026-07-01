from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path
import time

from backend.models import (
    ScoreRequest, ScoreResponse, FeedbackRequest, IngestRequest,
    CreateNicheRequest, GenerateDraftRequest, SaveNicheDraftRequest,
    SignupRequest, LoginRequest, AuthResponse,
    SaveHistoryRequest, SavedSetRequest, UserSettingsRequest,
)
from backend.niche_generator import generate_niche_draft
from backend.niche_manager import save_niche_draft
from backend.slug import slugify
from backend.scoring import score_topic, load_weights, _get_sim_model
from backend.baseline import score_baseline, _get_nlp as _get_baseline_nlp
from backend.cache import cache_key, get as cache_get, set as cache_set
from backend.feedback import init_db, seed_synthetic_feedback, log_feedback, get_feedback_by_niche
from backend.scheduler import start_scheduler, shutdown_scheduler, trigger_recompute, get_beta_summary
from backend.niche_manager import (
    get_available_niches, get_niche_config, set_active_niche,
    get_active_niche, create_custom_niche, _init_user_niches_db,
)
from backend.migration import run_migrations
from backend.auth import (
    init_auth_db, signup, authenticate, create_access_token,
    log_usage, get_usage,
    require_user, create_guest_session,
)
from backend.embeddings import _get_embedder
from backend.candidate_filter import _get_nlp as _get_filter_nlp
from backend.user_storage import (
    save_history, get_history, get_history_detail, clear_history,
    save_set, get_saved_sets, get_saved_set_detail, delete_saved_set,
    save_settings, get_settings,
    get_niche_metadata, update_niche_metadata,
    get_dashboard_stats,
)

_ingested_topics = []

VALID_PLATFORMS = {"LinkedIn", "Instagram", "X", "TikTok"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_auth_db()
    _init_user_niches_db()
    run_migrations()
    seed_synthetic_feedback()
    load_weights()
    start_scheduler()

    _get_embedder()
    _get_sim_model()
    _get_filter_nlp()
    _get_baseline_nlp()

    yield
    shutdown_scheduler()


app = FastAPI(title="TagGenie", version="3.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_user_id(current_user: dict) -> str:
    if current_user is None:
        return None
    if current_user.get("is_guest"):
        return current_user["user_id"]
    return str(current_user["user_id"])


# ── Public endpoints ─────────────────────────────────────────────────────


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


@app.get("/api/auth/guest")
async def api_guest_login():
    session = create_guest_session()
    return {
        "access_token": session["session_id"],
        "token_type": "bearer",
        "user_id": session["session_id"],
        "email": f"guest@{session['session_id'][:8]}",
        "is_guest": True,
    }


@app.get("/api/evaluation-summary")
async def api_evaluation_summary():
    results_file = Path(__file__).parent / "evaluation" / "results.md"
    if not results_file.exists():
        return {"best_lift_pct": 0, "niche": "none", "results": []}
    text = results_file.read_text()
    lines = text.split("\n")
    results = []
    best_lift = 0
    best_niche = ""
    in_table = False
    for line in lines:
        if line.startswith("|") and "TG P@5" in line:
            in_table = True
            continue
        if in_table and line.startswith("|") and "-------" not in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 8:
                r = {
                    "niche": parts[0],
                    "posts": int(parts[1]) if parts[1].isdigit() else 0,
                    "tg_p5": parts[2],
                    "bl_p5": parts[3],
                    "lift_p5": parts[4],
                    "tg_p10": parts[5],
                    "bl_p10": parts[6],
                    "lift_p10": parts[7],
                }
                results.append(r)
                try:
                    lift_val = float(parts[4].replace("+", "").replace("%", ""))
                    if lift_val > best_lift:
                        best_lift = lift_val
                        best_niche = parts[0]
                except ValueError:
                    pass
    return {"best_lift_pct": best_lift, "niche": best_niche, "results": results}


@app.get("/api/health")
async def api_health():
    return {"status": "ok"}


# ── Protected endpoints ──────────────────────────────────────────────────


@app.get("/api/auth/me")
async def api_me(current_user: dict = Depends(require_user)):
    if not current_user.get("is_guest"):
        log_usage(current_user["user_id"], "/api/auth/me")
    return current_user


@app.get("/api/auth/usage")
async def api_usage(current_user: dict = Depends(require_user)):
    if current_user.get("is_guest"):
        return {"total": 0, "this_month": 0, "guest": True}
    return get_usage(current_user["user_id"])


@app.post("/api/score", response_model=ScoreResponse)
async def api_score(
    req: ScoreRequest,
    current_user: dict = Depends(require_user),
):
    uid = _get_user_id(current_user)

    if req.platform not in VALID_PLATFORMS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid platform '{req.platform}'. Must be one of: {', '.join(sorted(VALID_PLATFORMS))}",
        )

    niche_id = req.niche or get_active_niche(uid)
    if get_niche_config(niche_id, uid) is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown niche '{niche_id}'. Available: {[n['niche_id'] for n in get_available_niches(uid)]}",
        )

    if not current_user.get("is_guest"):
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
    result = score_topic(req.topic, req.product, req.platform, niche_id, uid)
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

    # Save history for authenticated (non-guest) users
    if not current_user.get("is_guest"):
        save_history(
            uid, req.topic, req.product, req.platform, niche_id, result.model_dump()
        )
        update_niche_metadata(uid, niche_id, result.confidence)

    return result


@app.get("/api/niches")
async def api_list_niches(current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    return {"niches": get_available_niches(uid), "active": get_active_niche(uid)}


@app.post("/api/niches/switch")
async def api_switch_niche(data: dict, current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    niche_id = slugify(data.get("niche_id", ""))
    if not set_active_niche(niche_id, uid):
        raise HTTPException(status_code=422, detail=f"Unknown niche '{niche_id}'")
    return {"niche": get_niche_config(niche_id, uid), "active": niche_id}


@app.post("/api/niches/create")
async def api_create_niche(req: CreateNicheRequest, current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    req.niche_id = slugify(req.niche_id)
    if req.niche_id.startswith("gst_") or req.niche_id.startswith("guest_"):
        raise HTTPException(status_code=422, detail="Invalid niche_id: reserved prefix")
    if len(req.sample_posts) < 20:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 20 sample posts, got {len(req.sample_posts)}",
        )
    if get_niche_config(req.niche_id, uid) is not None:
        raise HTTPException(
            status_code=422,
            detail=f"Niche '{req.niche_id}' already exists",
        )

    config = create_custom_niche(
        req.niche_id, req.display_name, req.description, req.sample_posts, uid
    )
    return {"status": "created", "niche": config}


@app.post("/api/niches/generate-draft")
async def api_generate_draft(req: GenerateDraftRequest, current_user: dict = Depends(require_user)):
    req.niche_id = slugify(req.niche_id)
    if len(req.sample_posts) < 5:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least 5 sample posts, got {len(req.sample_posts)}",
        )
    if get_niche_config(req.niche_id, _get_user_id(current_user)) is not None:
        raise HTTPException(
            status_code=422,
            detail=f"Niche '{req.niche_id}' already exists",
        )

    draft = generate_niche_draft(req.niche_id, req.display_name, req.sample_posts)
    profile = draft.get("profile", {})
    return {
        "status": "draft_generated",
        "draft": {
            "niche_id": req.niche_id,
            "display_name": req.display_name,
            "description": draft.get("description", f"Auto-generated niche for {req.display_name}"),
            "sample_topics": draft.get("sample_topics", []),
            "corpus": draft.get("corpus", []),
            "jargon": profile,
            "sample_posts": req.sample_posts,
            "profile": profile,
            "_fallback": draft.get("_fallback"),
        },
    }


@app.post("/api/niches/save-draft")
async def api_save_draft(req: SaveNicheDraftRequest, current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    req.niche_id = slugify(req.niche_id)
    if get_niche_config(req.niche_id, uid) is not None:
        raise HTTPException(
            status_code=422,
            detail=f"Niche '{req.niche_id}' already exists",
        )

    draft_profile = req.jargon if isinstance(req.jargon, dict) and "industry_terms" in req.jargon else None
    config = save_niche_draft(
        niche_id=req.niche_id,
        display_name=req.display_name,
        description=req.description,
        sample_posts=req.sample_posts,
        corpus=req.corpus,
        jargon=req.jargon if isinstance(req.jargon, dict) else {},
        sample_topics=req.sample_topics,
        user_id=uid,
        profile=draft_profile,
    )
    return {"status": "created", "niche": config}


@app.get("/api/niches/metadata")
async def api_niche_metadata(current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    if current_user.get("is_guest"):
        return {"niches": []}
    return {"niches": get_niche_metadata(uid)}


@app.post("/api/feedback")
async def api_feedback(req: FeedbackRequest, current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    log_feedback(
        req.post_id,
        req.platform,
        req.tags_used,
        req.engagement.likes,
        req.engagement.shares,
        req.engagement.comments,
        req.niche,
        source="simulated",
        user_id=uid,
    )
    return {"status": "logged"}


@app.get("/api/feedback/{niche}")
async def api_feedback_history(niche: str, current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    return {"posts": get_feedback_by_niche(niche, uid)}


@app.get("/api/beta-summary")
async def api_beta_summary(current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    return {"beta_params": get_beta_summary(uid)}


@app.post("/api/ingest-candidates")
async def api_ingest(req: IngestRequest, current_user: dict = Depends(require_user)):
    _ingested_topics.extend([t.model_dump() for t in req.topics])
    return {
        "status": "accepted",
        "count": len(req.topics),
        "total_stored": len(_ingested_topics),
    }


@app.post("/api/trigger-recompute")
async def api_trigger(current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    trigger_recompute(uid)
    return {"status": "recompute_triggered"}


# ── History endpoints ───────────────────────────────────────────────────


@app.get("/api/history")
async def api_history(current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    if current_user.get("is_guest"):
        return {"history": []}
    return {"history": get_history(uid)}


@app.get("/api/history/{history_id}")
async def api_history_detail(history_id: int, current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    if current_user.get("is_guest"):
        raise HTTPException(status_code=403, detail="Guests cannot access history")
    detail = get_history_detail(uid, history_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="History entry not found")
    return detail


@app.delete("/api/history")
async def api_clear_history(current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    if not current_user.get("is_guest"):
        clear_history(uid)
    return {"status": "cleared"}


# ── Saved Sets endpoints ────────────────────────────────────────────────


@app.get("/api/saved-sets")
async def api_saved_sets(current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    if current_user.get("is_guest"):
        return {"saved_sets": []}
    return {"saved_sets": get_saved_sets(uid)}


@app.post("/api/saved-sets")
async def api_save_new_set(req: SavedSetRequest, current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    if current_user.get("is_guest"):
        raise HTTPException(status_code=403, detail="Guests cannot save sets")
    response_dict = {
        "ranked_tags": [t.model_dump() for t in req.ranked_tags],
        "gap_tags": [g.model_dump() for g in req.gap_tags],
        "analytics": req.analytics.model_dump() if req.analytics else {},
        "mix_summary": req.mix_summary.model_dump() if req.mix_summary else {},
        "confidence": req.confidence,
    }
    set_id = save_set(uid, req.name, req.topic, req.product, req.platform, req.niche, response_dict)
    return {"status": "saved", "id": set_id}


@app.get("/api/saved-sets/{set_id}")
async def api_saved_set_detail(set_id: int, current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    if current_user.get("is_guest"):
        raise HTTPException(status_code=403, detail="Guests cannot access saved sets")
    detail = get_saved_set_detail(uid, set_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Saved set not found")
    return detail


@app.delete("/api/saved-sets/{set_id}")
async def api_delete_saved_set(set_id: int, current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    if not current_user.get("is_guest"):
        delete_saved_set(uid, set_id)
    return {"status": "deleted"}


# ── Settings endpoints ──────────────────────────────────────────────────


@app.get("/api/settings")
async def api_get_settings(current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    if current_user.get("is_guest"):
        return {
            "preferred_platform": "LinkedIn",
            "default_niche": "",
            "default_export_format": "json",
            "theme": "dark",
            "sort_preference": "score_desc",
        }
    return get_settings(uid)


@app.post("/api/settings")
async def api_save_settings(req: UserSettingsRequest, current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    if current_user.get("is_guest"):
        return {"status": "skipped"}
    save_settings(uid, req.model_dump(exclude_none=True))
    return {"status": "saved"}


# ── Dashboard endpoint ──────────────────────────────────────────────────


@app.get("/api/dashboard")
async def api_dashboard(current_user: dict = Depends(require_user)):
    uid = _get_user_id(current_user)
    if current_user.get("is_guest"):
        return {
            "total_niches": 0,
            "recommendations_generated": 0,
            "total_sessions": 0,
            "blue_ocean_opportunities_found": 0,
            "most_used_platform": "LinkedIn",
            "most_used_niche": "gps-telematics",
            "average_confidence": 0.0,
            "history_timeline": [],
        }
    return get_dashboard_stats(uid)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
