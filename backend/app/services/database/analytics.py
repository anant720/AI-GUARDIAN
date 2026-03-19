"""
phase7/analytics.py
─────────────────────
Compute and store aggregated stats for users and apps.

All writes use UPSERT (INSERT ... ON CONFLICT DO UPDATE) so they
are idempotent and safe to call on every scan.
"""
from typing import Dict, Any, List, Optional

from app.logger import logger
from app.services.database.db import get_conn, is_connected


async def update_user_stats(user_id: int) -> bool:
    """
    Recompute and upsert user_notification_stats for a given user.
    Called in background after each notification is logged.
    """
    if not is_connected():
        return False
    try:
        async with get_conn() as conn:
            await conn.execute(
                """INSERT INTO user_notification_stats
                   (user_id, total_notifications, scam_notifications, avg_risk_score)
                   SELECT
                       $1,
                       COUNT(*),
                       SUM(CASE WHEN scam_probability >= 60 THEN 1 ELSE 0 END),
                       COALESCE(AVG(risk_score), 0)
                   FROM user_notifications
                   WHERE user_id = $1
                   ON CONFLICT (user_id) DO UPDATE SET
                       total_notifications = EXCLUDED.total_notifications,
                       scam_notifications  = EXCLUDED.scam_notifications,
                       avg_risk_score      = EXCLUDED.avg_risk_score,
                       last_updated        = NOW()""",
                user_id
            )
        return True
    except Exception as e:
        logger.error(f"update_user_stats failed: {e}")
        return False


async def update_app_stats(app_name: str) -> bool:
    """
    Recompute and upsert app_notification_stats for a given app.
    Called in background after each notification is logged.
    """
    if not is_connected():
        return False
    try:
        async with get_conn() as conn:
            await conn.execute(
                """INSERT INTO app_notification_stats
                   (app_name, total_notifications, high_risk_notifications)
                   SELECT
                       $1::varchar,
                       COUNT(*),
                       SUM(CASE WHEN scam_probability >= 60 THEN 1 ELSE 0 END)
                   FROM user_notifications
                   WHERE app_name = $1::varchar
                   ON CONFLICT (app_name) DO UPDATE SET
                       total_notifications     = EXCLUDED.total_notifications,
                       high_risk_notifications = EXCLUDED.high_risk_notifications,
                       last_updated            = NOW()""",
                app_name
            )
        return True
    except Exception as e:
        logger.error(f"update_app_stats failed: {e}")
        return False


async def get_user_dashboard(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Return aggregated stats + last 10 notifications for a user.
    Returns None if user not found.
    """
    if not is_connected():
        return None
    try:
        async with get_conn() as conn:
            # User info + stats
            stats_row = await conn.fetchrow(
                """SELECT u.user_id, u.username,
                          COALESCE(s.total_notifications, 0) AS total_notifications,
                          COALESCE(s.scam_notifications,  0) AS scam_notifications,
                          COALESCE(s.avg_risk_score,      0) AS avg_risk_score
                   FROM users u
                   LEFT JOIN user_notification_stats s USING (user_id)
                   WHERE u.user_id = $1""",
                user_id
            )
            if not stats_row:
                return None

            # Recent notifications
            recent_rows = await conn.fetch(
                """SELECT notification_id, app_name, url,
                          risk_score, scam_probability, created_at
                   FROM user_notifications
                   WHERE user_id = $1
                   ORDER BY created_at DESC
                   LIMIT 10""",
                user_id
            )

        return {
            "user_id":             stats_row["user_id"],
            "username":            stats_row["username"],
            "total_notifications": stats_row["total_notifications"],
            "scam_notifications":  stats_row["scam_notifications"],
            "avg_risk_score":      round(float(stats_row["avg_risk_score"]), 1),
            "recent":              [dict(r) for r in recent_rows]
        }
    except Exception as e:
        logger.error(f"get_user_dashboard failed: {e}")
        return None


async def get_app_dashboard() -> List[Dict[str, Any]]:
    """Return all app stats sorted by high_risk_notifications DESC."""
    if not is_connected():
        return []
    try:
        async with get_conn() as conn:
            rows = await conn.fetch(
                """SELECT app_name, total_notifications,
                          high_risk_notifications, last_updated
                   FROM app_notification_stats
                   ORDER BY high_risk_notifications DESC, total_notifications DESC"""
            )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"get_app_dashboard failed: {e}")
        return []
