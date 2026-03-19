"""
analytics_pipeline.py - Real-time Event Orchestrator (Analytics)
────────────────────────────────────────────────────────
Real-time analytics background task.
Queries Persistent Analytics Suite tables on an interval to aggregate metrics and
insert them into the system_metrics time-series table.
"""
import asyncio
from typing import Optional

from app.logger import logger
from app.services.database.db import get_conn, is_connected


_pipeline_task: Optional[asyncio.Task] = None
_INTERVAL_SECONDS = 60


async def _run_analytics_loop():
    """Background loop generating system-wide metrics every 60 seconds."""
    logger.info("Real-time Event Orchestrator: Analytics Pipeline started")
    
    while True:
        try:
            await asyncio.sleep(_INTERVAL_SECONDS)
            if not is_connected():
                continue
                
            async with get_conn() as conn:
                # 1. Total Notifications
                total = await conn.fetchval("SELECT COUNT(*) FROM user_notifications")
                
                # 2. High Risk Notifications (Scam >= 90 or Risk >= 80)
                high_risk = await conn.fetchval(
                    "SELECT COUNT(*) FROM user_notifications WHERE scam_probability >= 90 OR risk_score >= 80"
                )
                
                # 3. Total Interacted
                interacted = await conn.fetchval(
                    """SELECT COUNT(DISTINCT notification_id) 
                       FROM notification_interactions"""
                )

                # Insert into system_metrics
                await conn.execute(
                    """INSERT INTO system_metrics (metric_name, value)
                       VALUES ('total_notifications', $1),
                              ('high_risk_notifications', $2),
                              ('total_interactions', $3)""",
                    float(total or 0), float(high_risk or 0), float(interacted or 0)
                )

            logger.debug("Real-time Event Orchestrator: System metrics aggregated")
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Analytics loop error: {e}")


def start_analytics_pipeline():
    """Start the periodic metric aggregation task."""
    global _pipeline_task
    if _pipeline_task is None:
        _pipeline_task = asyncio.create_task(_run_analytics_loop())


async def stop_analytics_pipeline():
    global _pipeline_task
    if _pipeline_task:
        _pipeline_task.cancel()
        try:
            await _pipeline_task
        except asyncio.CancelledError:
            pass
        _pipeline_task = None
