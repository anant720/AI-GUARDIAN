"""
feedback_collector.py
─────────────────────
Collects user feedback on scan verdicts and stores them in SQLite.

Feedback schema:
  - message_id: str (from scan response)
  - url: str
  - system_verdict: str  (what AI said: scam/safe)
  - user_correction: str (what user says it actually was: scam/safe)
  - scam_probability: int
  - notes: str (optional)
  - created_at: datetime

Used by:
  - interaction_history_checker (anomaly detection)
  - llm_retrainer (generate fine-tuning dataset)
"""
import os
from typing import Optional
from app.logger import logger

_DB_PATH = os.path.join("data", "feedback.db")

# SQLite schema — created on first feedback write
_SCHEMA = """
CREATE TABLE IF NOT EXISTS scan_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL,
    url TEXT,
    domain TEXT,
    system_verdict TEXT,
    user_correction TEXT,
    scam_probability INTEGER,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scan_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT,
    domain TEXT,
    fingerprint TEXT,
    verdict TEXT,
    scam_probability INTEGER,
    user_correction TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_feedback_db() -> None:
    """Initialise feedback SQLite DB on startup."""
    try:
        import aiosqlite
        os.makedirs(os.path.dirname(_DB_PATH) or ".", exist_ok=True)
        async with aiosqlite.connect(_DB_PATH) as db:
            await db.executescript(_SCHEMA)
            await db.commit()
        logger.info("Feedback DB initialised")
    except ImportError:
        logger.warning("aiosqlite not installed — feedback DB disabled")
    except Exception as e:
        logger.error(f"Feedback DB init failed: {e}")


async def store_feedback(
    message_id: str,
    url: str,
    system_verdict: str,
    user_correction: str,
    scam_probability: int = 0,
    notes: Optional[str] = None
) -> bool:
    """
    Store a user feedback record.

    Returns True on success, False on failure.
    """
    from urllib.parse import urlparse
    domain = (urlparse(url).hostname or "").lstrip("www.")

    try:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            await db.execute(
                """INSERT INTO scan_feedback
                   (message_id, url, domain, system_verdict, user_correction,
                    scam_probability, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (message_id, url, domain, system_verdict,
                 user_correction, scam_probability, notes)
            )
            # Also update scan_history if verdict changed
            await db.execute(
                """UPDATE scan_history SET user_correction = ?
                   WHERE message_id = ?""",
                (user_correction, message_id)
            )
            await db.commit()
        logger.info(
            f"Feedback stored: id={message_id} "
            f"system={system_verdict} user={user_correction}"
        )
        return True
    except ImportError:
        logger.warning("aiosqlite not installed — feedback not stored")
        return False
    except Exception as e:
        logger.error(f"Failed to store feedback: {e}")
        return False


async def get_false_positives(limit: int = 100) -> list:
    """Retrieve false positives (system said scam, user says safe)."""
    try:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            async with db.execute(
                """SELECT message_id, url, system_verdict, user_correction, notes
                   FROM scan_feedback
                   WHERE system_verdict='scam' AND user_correction='safe'
                   LIMIT ?""",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(zip(["message_id", "url", "system_verdict", "user_correction", "notes"], r)) for r in rows]
    except Exception:
        return []


async def get_false_negatives(limit: int = 100) -> list:
    """Retrieve false negatives (system said safe, user says scam)."""
    try:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            async with db.execute(
                """SELECT message_id, url, system_verdict, user_correction, notes
                   FROM scan_feedback
                   WHERE system_verdict='safe' AND user_correction='scam'
                   LIMIT ?""",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(zip(["message_id", "url", "system_verdict", "user_correction", "notes"], r)) for r in rows]
    except Exception:
        return []
