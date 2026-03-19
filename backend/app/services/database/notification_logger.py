"""
phase7/notification_logger.py
─────────────────────────────
Insert and query user_notifications in PostgreSQL.

PII in message_text is masked before saving.
Phase5 behavioral outputs and LLM verdicts stored as JSONB.
"""
import json
import asyncio
from typing import Optional, Dict, Any, List

from app.logger import logger
from app.services.database.db import get_conn, is_connected
from app.services.database.utils import mask_message_pii
from app.services.event_system.event_bus import publish_event


async def log_notification(
    user_id:          int,
    app_name:         str,
    message_text:     Optional[str],
    url:              str,
    risk_score:       int,
    scam_probability: int,
    phase5_behavior:  Optional[Dict[str, Any]] = None,
    llm_verdict:      Optional[Dict[str, Any]] = None,
    phase_outputs:    Optional[Dict[str, Any]] = None
) -> Optional[int]:
    """
    Insert a notification record. Returns notification_id or None on failure.
    """
    if not is_connected():
        logger.warning("Persistent Analytics Suite: DB not connected — notification not logged")
        return None

    try:
        clean_msg = mask_message_pii(message_text or "")
        p5_json   = json.dumps(phase5_behavior or {})
        llm_json  = json.dumps(llm_verdict    or {})
        phases_json = json.dumps(phase_outputs or {}, default=str)

        async with get_conn() as conn:
            row = await conn.fetchrow(
                """INSERT INTO user_notifications
                   (user_id, app_name, message_text, url,
                    risk_score, scam_probability, phase5_behavior, llm_verdict, phase_outputs)
                   VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,$9::jsonb)
                   RETURNING notification_id""",
                user_id, app_name, clean_msg, url,
                risk_score, scam_probability, p5_json, llm_json, phases_json
            )
        nid = row["notification_id"]
        logger.info(
            f"Notification logged: id={nid} user={user_id} "
            f"app={app_name} score={scam_probability}%"
        )
        
        # Real-time Event Orchestrator: Fire Discovery Event
        asyncio.create_task(
            publish_event(
                "notification_scanned",
                {
                    "notification_id": nid,
                    "user_id": user_id,
                    "app_name": app_name,
                    "risk_score": risk_score,
                    "scam_probability": scam_probability,
                    "url": url,
                },
            )
        )
        
        return nid

    except Exception as e:
        logger.error(f"log_notification failed: {e}")
        return None


async def get_user_notifications(
    user_id: int,
    limit:   int = 20,
    offset:  int = 0
) -> List[Dict[str, Any]]:
    """Paginated notification history for a user."""
    if not is_connected():
        return []
    try:
        async with get_conn() as conn:
            rows = await conn.fetch(
                """SELECT notification_id, app_name, url, risk_score,
                          scam_probability, created_at
                   FROM user_notifications
                   WHERE user_id = $1
                   ORDER BY created_at DESC
                   LIMIT $2 OFFSET $3""",
                user_id, limit, offset
            )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"get_user_notifications failed: {e}")
        return []


async def mark_processed(notification_id: int) -> bool:
    """Set processed=true once analytics have run."""
    if not is_connected():
        return False
    try:
        async with get_conn() as conn:
            await conn.execute(
                "UPDATE user_notifications SET processed=TRUE WHERE notification_id=$1",
                notification_id
            )
        return True
    except Exception as e:
        logger.error(f"mark_processed failed: {e}")
        return False
