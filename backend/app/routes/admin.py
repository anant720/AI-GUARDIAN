"""
admin.py — Phase 6 Admin API Routes
─────────────────────────────────────
Endpoints:
  POST /admin/retrain         — trigger full Phase 6 pipeline
  GET  /admin/models          — list all model versions + metrics
  POST /admin/rollback        — activate a previous model version
  GET  /admin/feedback/stats  — FP/FN counts, scheduler status, DB health
"""
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from app.logger import logger
from app.services.database.auth import require_role
from app.services.database.db import get_conn, is_connected
from app.services.continuous_learning import run_full_retrain_pipeline
from app.services.continuous_learning.model_registry import list_versions, rollback_to

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Request models ─────────────────────────────────────────────────────────────
class RollbackRequest(BaseModel):
    version: str


class RetrainRequest(BaseModel):
    dry_run:       Optional[bool]   = None   # None = use FINETUNE_DRY_RUN env
    auto_activate: Optional[bool]   = False
    provider:      Optional[str]    = None   # None = use FINETUNE_PROVIDER env
    base_model:    Optional[str]    = None


# ── POST /admin/retrain ────────────────────────────────────────────────────────
@router.post("/retrain")
async def trigger_retrain(
    req: Optional[RetrainRequest] = None,
    dry_run: Optional[bool] = Query(None, description="Override dry_run flag")
):
    """
    Trigger the full Phase 6 retrain pipeline.

    - dry_run=true (default): validates dataset, estimates cost — no API call.
    - dry_run=false: submits actual fine-tuning job to configured provider.

    JSON body (all optional):
      dry_run, auto_activate, provider, base_model
    """
    req = req or RetrainRequest()

    # Query param overrides body
    effective_dry_run = dry_run if dry_run is not None else req.dry_run

    try:
        result = await run_full_retrain_pipeline(
            dry_run=effective_dry_run,
            auto_activate=req.auto_activate or False,
            provider=req.provider,
            base_model=req.base_model
        )
        return result

    except Exception as e:
        logger.error(f"Retrain endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /admin/models ──────────────────────────────────────────────────────────
@router.get("/models")
async def get_models():
    """
    List all registered fine-tuned model versions.
    Returns version, provider, accuracy, FP/FN rate, is_active.
    """
    try:
        versions = await list_versions()
        return {
            "models": versions,
            "total": len(versions),
            "active": next((v["version"] for v in versions if v.get("is_active")), None)
        }
    except Exception as e:
        logger.error(f"Models endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /admin/rollback ───────────────────────────────────────────────────────
@router.post("/rollback")
async def rollback(req: RollbackRequest):
    """
    Roll back to a specific model version.
    Sets is_active=1 for target version and 0 for all others.
    Also updates in-memory llm_client override immediately.
    """
    if not req.version:
        raise HTTPException(status_code=400, detail="version is required")
    try:
        result = await rollback_to(req.version)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Rollback failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rollback endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /admin/feedback/stats ─────────────────────────────────────────────────
@router.get("/feedback/stats")
async def feedback_stats():
    """
    Return feedback database health and training readiness.
    """
    import os, aiosqlite
    db_path = os.path.join("data", "feedback.db")

    stats = {
        "db_exists": os.path.exists(db_path),
        "total_feedback": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "ready_for_training": False,
        "min_threshold": int(os.getenv("RETRAIN_MIN_FEEDBACK", "20")),
        "scheduler": {}
    }

    if not stats["db_exists"]:
        return stats

    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM scan_feedback") as c:
                stats["total_feedback"] = (await c.fetchone())[0]
            async with db.execute(
                "SELECT COUNT(*) FROM scan_feedback "
                "WHERE system_verdict='scam' AND user_correction='safe'"
            ) as c:
                stats["false_positives"] = (await c.fetchone())[0]
            async with db.execute(
                "SELECT COUNT(*) FROM scan_feedback "
                "WHERE system_verdict='safe' AND user_correction='scam'"
            ) as c:
                stats["false_negatives"] = (await c.fetchone())[0]
    except Exception:
        pass

    usable = stats["false_positives"] + stats["false_negatives"]
    stats["ready_for_training"] = usable >= stats["min_threshold"]
    stats["usable_for_training"] = usable

    # Scheduler status
    try:
        from app.services.continuous_learning.retrain_scheduler import scheduler
        stats["scheduler"] = scheduler.get_status()
    except Exception:
        stats["scheduler"] = {"running": False}

    return stats


# ── GET /admin/users (admin dashboard) ────────────────────────────────────────
@router.get("/users")
async def list_users(
    current_user: Dict[str, Any] = Depends(require_role("admin", "analyst"))
):
    """
    List users for the admin dashboard.
    (Frontend calls this endpoint.)
    """
    if not is_connected():
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        async with get_conn() as conn:
            rows = await conn.fetch(
                "SELECT user_id, username, email, role, created_at, last_login "
                "FROM users ORDER BY user_id ASC LIMIT 500"
            )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Admin list_users failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")
