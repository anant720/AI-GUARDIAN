"""
app/routes/monitoring_tests.py
──────────────────────────────
Phase 9 API endpoints extending the 'monitoring' router with automated test 
triggering, HTML report fetching, and KanTool diagnostics commands.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import os

from app.logger import logger
from app.services.database.auth import require_role
from app.services.database.db import is_connected as pg_connected

from app.services.monitoring.test_runner import run_full_suite
from app.services.monitoring.report_manager import get_latest_report
from app.services.monitoring.self_heal import orchestrate_self_healing
from app.services.monitoring.db_diagnostics import collect_env_and_dump

router = APIRouter(prefix="/monitor", tags=["monitoring", "testing"])

@router.get("/tests/run")
async def execute_tests(current_user: Dict[str, Any] = Depends(require_role("admin"))):
    """
    On-demand execution of the full test suite (Unit + Integration endpoints).
    Saves a report locally to `logs/test_reports` and returns JSON.
    """
    return await run_full_suite()

@router.get("/tests/report")
async def fetch_latest_report(current_user: Dict[str, Any] = Depends(require_role("admin", "analyst"))):
    """
    Returns the JSON representation of the latest test report run on the server.
    """
    report = get_latest_report()
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    return report

@router.get("/db_status")
async def get_db_status_and_kantool(current_user: Dict[str, Any] = Depends(require_role("admin"))):
    """
    If DB is DOWN, deliberately invokes KanTool `collect_env_and_dump()`.
    Returns current active DB state tracking status.
    """
    status = {"postgres_active": pg_connected()}
    if not status["postgres_active"]:
        success = collect_env_and_dump()
        status["kantool_diagnostic_saved"] = success
        status["kantool_path"] = os.getenv("KAN_TOOL_PATH", "C:/KanTool/ai_guardian_env.json")
        
    return status

@router.post("/self_heal")
async def manually_trigger_self_heal(
    component: str,
    background: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_role("admin"))
):
    """
    Invoke backend self-healing targeting either 'postgres' or 'redis'. 
    Component queue connection will be safely destroyed and rebuilt in background.
    """
    if component not in ["postgres", "redis"]:
        raise HTTPException(status_code=400, detail="Component must be postgres or redis")
        
    logger.info(f"Phase 9: Manual self-heal dispatched for {component} by {current_user['username']}")
    background.add_task(orchestrate_self_healing, component)
    return {"message": f"Self-healing task queued for '{component}'"}
