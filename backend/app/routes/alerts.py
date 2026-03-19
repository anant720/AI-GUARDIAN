"""
app/routes/alerts.py
─────────────────────
Phase 8 Endpoints:
GET  /alerts                       → List unacknowledged alerts
POST /alerts/{alert_id}/acknowledge → Mark alert handled
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException

from app.services.database.auth import require_role, get_current_user
from app.services.event_system.monitoring import get_unacknowledged_alerts, acknowledge_alert

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.get("", response_model=List[Dict[str, Any]])
async def list_alerts(
    current_user: Dict[str, Any] = Depends(require_role("admin", "analyst"))
):
    """Fetch all unacknowledged system alerts."""
    return await get_unacknowledged_alerts()

@router.post("/{alert_id}/acknowledge")
async def ack_alert(
    alert_id: int,
    current_user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    Acknowledge a specific alert, hiding it from the active dashboard.
    Only an Admin can acknowledge an alert.
    """
    success = await acknowledge_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")
    
    return {"status": "success", "message": f"Alert {alert_id} acknowledged by {current_user['username']}"}
