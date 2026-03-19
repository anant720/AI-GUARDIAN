"""
app/routes/scan.py
───────────────────
Slim route handlers that delegate all detection logic to core/pipeline.py.

POST /scan      → run_detection_pipeline()
POST /feedback  → store user corrections
POST /admin/retrain → trigger fine-tuning
"""
import asyncio
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.pipeline import run_detection_pipeline
from app.core.llm_cache import get_cache_stats
from app.services.behavioral_engine.feedback_collector import store_feedback
from app.logger import logger

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ── Request / Response Models ─────────────────────────────────────────────────
class ScanRequest(BaseModel):
    url: Optional[str] = None
    message: Optional[str] = None


class FeedbackRequest(BaseModel):
    message_id: str
    url: str
    system_verdict: str      # "scam" | "safe"
    user_correction: str     # "scam" | "safe"
    scam_probability: Optional[int] = 0
    notes: Optional[str] = None


# ── POST /scan ─────────────────────────────────────────────────────────────────
@router.post("/scan")
@limiter.limit("30/minute")
async def scan(request: Request, body: ScanRequest):
    """
    Main detection endpoint. Runs the full optimized detection pipeline.

    Pipeline:
      Signal Discovery (Parallel) → Adaptive Behavioral Index → AI Deep-Reasoning Gating → Score → Response

    Performance: < 800ms (no LLM) | < 1.5s (with LLM) | < 200ms (cached)
    """
    try:
        return await run_detection_pipeline(
            url=body.url,
            message=body.message,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scan pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /feedback ─────────────────────────────────────────────────────────────
@router.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """Accept user corrections on scan verdicts for continuous learning."""
    success = await store_feedback(
        message_id=feedback.message_id,
        url=feedback.url,
        system_verdict=feedback.system_verdict,
        user_correction=feedback.user_correction,
        scam_probability=feedback.scam_probability or 0,
        notes=feedback.notes,
    )
    if success:
        return {
            "status": "accepted",
            "message_id": feedback.message_id,
            "correction": feedback.user_correction,
        }
    return {"status": "failed", "detail": "Feedback storage unavailable"}


# ── GET /scan/cache/stats ──────────────────────────────────────────────────────
@router.get("/scan/cache/stats")
async def cache_stats():
    """Return LLM cache performance stats."""
    return get_cache_stats()


# ── POST /admin/retrain ────────────────────────────────────────────────────────
@router.post("/admin/retrain")
async def trigger_retrain():
    """Trigger fine-tuning dataset generation from feedback."""
    from app.services.behavioral_engine.llm_retrainer import generate_finetune_dataset
    result = await generate_finetune_dataset()
    return result
