"""
phase7/interaction_tracker.py
──────────────────────────────
Record user interactions with notifications:
  read | clicked | ignored
"""
from typing import Optional

from app.logger import logger
from app.services.database.db import get_conn, is_connected

_VALID_ACTIONS = {"read", "clicked", "ignored"}


async def log_interaction(
    notification_id: int,
    action_type:     str
) -> Optional[int]:
    """
    Insert an interaction record.

    Returns interaction_id or None on failure.
    """
    if action_type not in _VALID_ACTIONS:
        logger.warning(f"Invalid action_type: {action_type}")
        return None

    if not is_connected():
        logger.warning("Persistent Analytics Suite: DB not connected — interaction not logged")
        return None

    try:
        async with get_conn() as conn:
            row = await conn.fetchrow(
                """INSERT INTO notification_interactions
                   (notification_id, action_type)
                   VALUES ($1, $2)
                   RETURNING interaction_id""",
                notification_id, action_type
            )
        iid = row["interaction_id"]
        logger.info(
            f"Interaction logged: id={iid} "
            f"notification={notification_id} action={action_type}"
        )
        return iid
    except Exception as e:
        logger.error(f"log_interaction failed: {e}")
        return None


async def get_interactions(notification_id: int) -> list:
    """Retrieve interaction history for a notification."""
    if not is_connected():
        return []
    try:
        async with get_conn() as conn:
            rows = await conn.fetch(
                """SELECT interaction_id, action_type, action_timestamp
                   FROM notification_interactions
                   WHERE notification_id = $1
                   ORDER BY action_timestamp""",
                notification_id
            )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"get_interactions failed: {e}")
        return []
