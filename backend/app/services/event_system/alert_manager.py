"""
phase8/alert_manager.py
────────────────────────
Listens to event bus topics (e.g. notification_scanned).
Evaluates conditions to generate Alerts into the `system_alerts` table.
Capable of firing webhooks for enterprise alerting integration.
"""
import os
import asyncio
from typing import Dict, Any

from app.logger import logger
from app.services.database.db import get_conn, is_connected
from app.services.event_system.event_bus import subscribe

try:
    import httpx
except ImportError:
    httpx = None

_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")


async def setup_alert_manager():
    """Register subscriptions for alert manager."""
    subscribe("notification_scanned", process_scan_for_alerts)
    logger.info("Real-time Event Orchestrator: Alert Manager subscribed to 'notification_scanned'")


async def process_scan_for_alerts(payload: Dict[str, Any]):
    """
    Callback for 'notification_scanned' event.
    Evaluates risk and creates alerts if necessary.
    """
    risk_score = payload.get("risk_score", 0)
    scam_prob = payload.get("scam_probability", 0)
    user_id = payload.get("user_id")
    notification_id = payload.get("notification_id")

    # Rule 1: High Risk Scam Detected
    if scam_prob >= 90:
        await generate_alert(
            user_id=user_id,
            notification_id=notification_id,
            alert_type="HIGH_RISK_SCAM",
            severity=1, # 1=Critical, 2=High, 3=Medium, 4=Low
            message=f"Critical scam detected (Prob: {scam_prob}%) for App: {payload.get('app_name', 'Unknown')}"
        )
    
    elif risk_score >= 80:
        await generate_alert(
            user_id=user_id,
            notification_id=notification_id,
            alert_type="ELEVATED_RISK",
            severity=2,
            message=f"Elevated risk URL/Domain detected (Score: {risk_score})"
        )


async def generate_alert(user_id: int, notification_id: int, alert_type: str, severity: int, message: str):
    """
    Inserts alert into PostgreSQL and optionally fires a webhook.
    """
    if not is_connected():
        return

    try:
        async with get_conn() as conn:
            row = await conn.fetchrow(
                """INSERT INTO system_alerts
                   (user_id, notification_id, alert_type, severity, message)
                   VALUES ($1, $2, $3, $4, $5)
                   RETURNING alert_id""",
                user_id, notification_id, alert_type, severity, message
            )
        alert_id = row["alert_id"]
        logger.warning(f"🚨 ALERT GENERATED: {alert_type} (Sev {severity}) - {message}")

        # Fire Webhook if configured
        if _WEBHOOK_URL and httpx:
            asyncio.create_task(_fire_webhook({
                "alert_id": alert_id,
                "type": alert_type,
                "severity": severity,
                "message": message,
                "user_id": user_id,
                "notification_id": notification_id
            }))

    except Exception as e:
        logger.error(f"Failed to generate alert: {e}")


async def _fire_webhook(payload: dict):
    """Internal: Fire HTTP POST to configured webhook."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(_WEBHOOK_URL, json=payload, timeout=5.0)
            resp.raise_for_status()
            logger.debug(f"Webhook fired successfully for Alert {payload['alert_id']}")
    except Exception as e:
        logger.error(f"Webhook delivery failed: {e}")
