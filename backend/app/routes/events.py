"""
app/routes/events.py
─────────────────────
Phase 8 Endpoints:
POST /events/publish    → Manual event publishing
POST /retrain/trigger   → Trigger automated continuous learning
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, BackgroundTasks

from app.services.database.auth import require_role, get_current_user
from app.services.event_system.event_bus import publish_event
from app.services.event_system.retrain_orchestrator import trigger_manual_retrain

router = APIRouter(tags=["events", "retrain"])

@router.post("/events/publish")
async def manual_publish(
    topic: str,
    payload: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    Manually inject an event into the bus.
    Useful for testing scaling behaviors or debugging subscriptions.
    """
    # Force injection of user context
    payload["triggered_by"] = current_user["user_id"]
    await publish_event(topic, payload)
    return {"status": "published", "topic": topic}

@router.post("/retrain/trigger")
async def trigger_retraining(
    background: BackgroundTasks,
    dry_run: bool = True,
    current_user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    Manually execute the Phase 6 Continuous Learning pipeline (wrapped inside the Event Bus).
    Executes in the background because the pipeline includes external OpenAI/Groq API calls.
    """
    # Fire off as a background task to prevent blocking the API response
    background.add_task(trigger_manual_retrain, current_user["user_id"], dry_run)
    
    return {
        "status": "accepted",
        "message": "Retraining job queued successfully. Check alerts and event logs for completion status."
    }
