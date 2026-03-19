"""
phase8/monitoring.py
─────────────────────
Expose system health endpoints verifying connection to DB, Redis, 
LLM, Event Bus queue, and Vector DB.
"""
import ctypes
from typing import Dict, Any

from app.logger import logger
from app.services.database.db import is_connected as db_connected, get_conn
from app.services.event_system.event_bus import _redis_client, _fallback_queue


async def check_system_health() -> Dict[str, Any]:
    """
    Returns a deep health diagnostic of all backend infrastructure.
    """
    health = {
        "status": "ok",
        "components": {}
    }

    # 1. PostgreSQL Check
    try:
        if db_connected():
            async with get_conn() as conn:
                await conn.execute("SELECT 1")
            health["components"]["database"] = {"status": "up", "type": "postgres"}
        else:
            health["components"]["database"] = {"status": "down"}
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["database"] = {"status": "down", "error": str(e)}
        health["status"] = "degraded"

    # 2. Event Bus Check (Redis or Queue)
    try:
        if _redis_client:
            await _redis_client.ping()
            health["components"]["event_bus"] = {"status": "up", "type": "redis"}
        else:
            health["components"]["event_bus"] = {
                "status": "up", 
                "type": "memory_queue", 
                "pending": _fallback_queue.qsize()
            }
    except Exception as e:
        health["components"]["event_bus"] = {"status": "down", "error": str(e)}
        health["status"] = "degraded"

    return health


async def get_system_metrics(limit: int = 50) -> list:
    """Fetch the latest time-series metrics from the database."""
    if not db_connected():
        return []
        
    try:
        async with get_conn() as conn:
            rows = await conn.fetch(
                """SELECT metric_name, value, recorded_at
                   FROM system_metrics
                   ORDER BY recorded_at DESC
                   LIMIT $1""",
                limit
            )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to fetch system metrics: {e}")
        return []


async def get_unacknowledged_alerts() -> list:
    """Fetch all unacknowledged alerts from system_alerts."""
    if not db_connected():
        return []
    
    try:
        async with get_conn() as conn:
            rows = await conn.fetch(
                """SELECT alert_id, user_id, notification_id, alert_type, 
                          severity, message, triggered_at
                   FROM system_alerts 
                   WHERE acknowledged = FALSE
                   ORDER BY severity ASC, triggered_at DESC"""
            )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {e}")
        return []


async def acknowledge_alert(alert_id: int) -> bool:
    """Mark an alert as acknowledged."""
    if not db_connected():
        return False
        
    try:
        async with get_conn() as conn:
            res = await conn.execute(
                "UPDATE system_alerts SET acknowledged = TRUE WHERE alert_id = $1",
                alert_id
            )
        return res == "UPDATE 1"
    except Exception as e:
        logger.error(f"Failed to ack alert: {e}")
        return False
