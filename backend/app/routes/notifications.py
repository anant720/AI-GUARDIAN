"""
app/routes/notifications.py — Phase 7 Notification & Dashboard Endpoints
──────────────────────────────────────────────────────────────────────────
POST /notifications               — log notification, run Phase 1-6 scan
POST /notifications/interact      — record user interaction
GET  /dashboard/users/{user_id}   — user stats + history
GET  /dashboard/apps              — app-level aggregated stats
"""
import asyncio
import re
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.logger import logger
from app.services.database.auth import get_current_user, require_role
from app.services.database.db import is_connected
from app.services.monitoring.db_diagnostics import collect_env_and_dump
from app.services.monitoring.self_heal import orchestrate_self_healing
from app.services.database.schemas import (
    NotificationLogRequest, NotificationLogResponse,
    InteractionRequest, InteractionResponse,
    UserStatsResponse, AppStatsResponse, AppStatsItem, NotificationSummary
)
from app.services.database.notification_logger import log_notification
from app.services.database.interaction_tracker import log_interaction
from app.services.database.analytics import (
    update_user_stats, update_app_stats,
    get_user_dashboard, get_app_dashboard
)

router = APIRouter(tags=["notifications"])
limiter = Limiter(key_func=get_remote_address)


def _trigger_db_fallback():
    # Fire-and-forget: persist env diagnostics + attempt recovery.
    try:
        asyncio.create_task(asyncio.to_thread(collect_env_and_dump))
        asyncio.create_task(orchestrate_self_healing("postgres"))
    except Exception:
        # Never let diagnostics crash the request path.
        pass


def _sanitize_url_for_scan(url: str) -> str:
    """
    Accept common red-team URL obfuscations and normalize them back to a valid URL.
    This prevents downstream HTTP clients/parsers from throwing on inputs like:
      - https://example[.]com
      - hxxps://example.com
    """
    if not url:
        return ""
    u = url.strip()
    # Common dot obfuscation
    u = u.replace("[.]", ".").replace("(.)", ".")
    # Common scheme obfuscation
    u = re.sub(r"^hxxps://", "https://", u, flags=re.IGNORECASE)
    u = re.sub(r"^hxxp://", "http://", u, flags=re.IGNORECASE)
    return u


def _db_required():
    if not is_connected():
        _trigger_db_fallback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured. Add DATABASE_URL to .env"
        )


async def _run_full_scan(url: str, message: Optional[str]) -> Dict[str, Any]:
    """
    Run the complete Phase 1-6 pipeline using the optimized core/pipeline.py.
    Returns the structured scan result dict.
    """
    from app.core.pipeline import run_detection_pipeline

    response = await run_detection_pipeline(url=url, message=message)

    # Map new response format to what notification_logger expects
    return {
        "url_report":         response.get("url_report", {}),
        "message_report":     response.get("message_report"),
        "threat_report":      response.get("threat_intelligence", {}),
        "rag_context":        "",
        "rag_evidence":       response.get("evidence", []),
        "llm_verdict":        response.get("llm_verdict", {}),
        "phase3_reasoning":   response.get("explanation", ""),
        "phase5":             {
            "scam_probability":    response.get("combined_score", 0),
            "behavioral_analysis": response.get("behavioral_analysis"),
            "semantic_risk":       response.get("semantic_risk"),
            "domain_behavior":     response.get("domain_behavior"),
            "evidence":            response.get("evidence", []),
            "explanation":         response.get("explanation", ""),
        },
        "risk_score":        response.get("phase_scores", {}).get("url_score", 0),
        "scam_probability":  response.get("combined_score", 0),
        "performance":       response.get("performance", {}),
    }


# ── POST /notifications ────────────────────────────────────────────────────────
@router.post("/notifications", response_model=NotificationLogResponse, status_code=201)
@limiter.limit("60/minute")
async def log_notification_endpoint(
    request:         Request,
    req:             NotificationLogRequest,
    background:      BackgroundTasks,
    current_user:    Dict[str, Any] = Depends(get_current_user)
):
    """
    Log a notification for the authenticated user.

    If risk_score/scam_probability are not provided in the request body,
    runs the full Phase 1-6 scan automatically and logs all outputs.
    """
    _db_required()
    user_id = current_user["user_id"]

    # If URL not supplied, try to extract one from the message body.
    url = (req.url or "").strip()
    if not url and req.message_text:
        m = re.search(r"(https?://[^\s<>\"]+)", req.message_text)
        if m:
            url = m.group(1).strip().rstrip(").,;")
    url = _sanitize_url_for_scan(url)

    # Non-negotiable: POST /notifications always runs full Phase 1–6 scan
    # (Phase 7 is the DB logging step below).
    try:
        scan = await _run_full_scan(url, req.message_text)
    except Exception as e:
        logger.error(f"Phase 1-6 scan failed during notification log: {e}")
        scan = {
            "risk_score": 0,
            "scam_probability": 0,
            "phase5": {},
            "llm_verdict": {},
            "phase3_reasoning": None,
            "url_report": {},
            "threat_report": {},
        }

    risk_score        = scan["risk_score"]
    scam_probability  = scan["scam_probability"]
    phase5_behavior   = scan.get("phase5", {})
    llm_verdict       = scan.get("llm_verdict", {})
    phase3_reasoning  = scan.get("phase3_reasoning")
    full_scan_result  = scan

    nid = await log_notification(
        user_id=user_id,
        app_name=req.app_name,
        message_text=req.message_text,
        url=url,
        risk_score=risk_score,
        scam_probability=scam_probability,
        phase5_behavior=phase5_behavior,
        llm_verdict=llm_verdict,
        phase_outputs=full_scan_result
    )

    if nid is None:
        raise HTTPException(status_code=500, detail="Failed to log notification")

    # Background: update analytics stats
    background.add_task(update_user_stats, user_id)
    background.add_task(update_app_stats, req.app_name)

    return NotificationLogResponse(
        notification_id=nid,
        user_id=user_id,
        scam_probability=scam_probability,
        risk_score=risk_score,
        phase3_reasoning=phase3_reasoning,
        phase4_threat_intel=full_scan_result.get("threat_report") if full_scan_result else None,
        phase5_behavioral_analysis=phase5_behavior.get("behavioral_analysis") if isinstance(phase5_behavior, dict) else None,
        logging={"stored": True, "notification_id": nid},
        scan_result=full_scan_result
    )


# ── POST /notifications/interact ──────────────────────────────────────────────
@router.post("/notifications/interact", response_model=InteractionResponse)
async def interact(
    req:          InteractionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Record a user interaction (read / clicked / ignored)."""
    _db_required()

    iid = await log_interaction(req.notification_id, req.action_type)
    if iid is None:
        raise HTTPException(status_code=500, detail="Failed to log interaction")

    return InteractionResponse(
        interaction_id=iid,
        notification_id=req.notification_id,
        action_type=req.action_type
    )


# ── GET /dashboard/users/{user_id} ────────────────────────────────────────────
@router.get("/dashboard/users/{user_id}", response_model=UserStatsResponse)
async def user_dashboard(
    user_id:      int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Fetch stats and notification history for a user.
    Users can only view their own dashboard; admins can view any.
    """
    _db_required()

    # RBAC: standard users can only see their own data
    if current_user["role"] not in ("admin", "analyst"):
        if current_user["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own dashboard"
            )

    data = await get_user_dashboard(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    recent = [
        NotificationSummary(
            notification_id=r["notification_id"],
            app_name=r.get("app_name"),
            url=r.get("url"),
            risk_score=r.get("risk_score", 0),
            scam_probability=r.get("scam_probability", 0),
            created_at=r.get("created_at")
        )
        for r in data.get("recent", [])
    ]

    return UserStatsResponse(
        user_id=data["user_id"],
        username=data["username"],
        total_notifications=data["total_notifications"],
        scam_notifications=data["scam_notifications"],
        avg_risk_score=data["avg_risk_score"],
        recent=recent
    )


# ── GET /dashboard/apps ───────────────────────────────────────────────────────
@router.get("/dashboard/apps", response_model=AppStatsResponse)
async def app_dashboard(
    current_user: Dict[str, Any] = Depends(require_role("admin", "analyst"))
):
    """
    Return aggregated per-app notification stats.
    Requires analyst or admin role.
    """
    _db_required()
    apps_data = await get_app_dashboard()
    items = [
        AppStatsItem(
            app_name=r["app_name"],
            total_notifications=r["total_notifications"],
            high_risk_notifications=r["high_risk_notifications"],
            last_updated=r.get("last_updated")
        )
        for r in apps_data
    ]
    return AppStatsResponse(apps=items, total=len(items))
