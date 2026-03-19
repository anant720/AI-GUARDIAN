"""
app/routes/monitoring.py
─────────────────────────
Real-time Event Orchestrator Endpoints:
GET /monitor/health          → Deep system check
GET /monitor/metrics/system  → Recent system_metrics
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends

from app.services.database.auth import get_current_user, require_role
from app.services.event_system.monitoring import check_system_health, get_system_metrics

router = APIRouter(prefix="/monitor", tags=["monitoring"])

@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    Public health check returning the deep validation of PostgreSQL, Redis/Queue, etc.
    Useful for Kubernetes or load balancer health probes.
    """
    return await check_system_health()

@router.get("/metrics/system", response_model=Dict[str, Any])
async def system_metrics(
    current_user: Dict[str, Any] = Depends(require_role("admin", "analyst"))
):
    """
    Fetch the latest system-wide time-series metrics aggregated for the Dashboard.
    """
    raw_history = await get_system_metrics(limit=50)
    
    # Aggregate latest values for KPICards
    latest_data = {}
    if raw_history:
        # Get most recent value for each metric name
        seen = set()
        for m in raw_history:
            name = m['metric_name']
            if name not in seen:
                latest_data[name] = m['value']
                seen.add(name)
    
    return {
        "status": "success",
        "data": latest_data,
        "history": raw_history
    }
