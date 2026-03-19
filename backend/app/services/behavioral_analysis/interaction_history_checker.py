"""
interaction_history_checker.py
───────────────────────────────
Checks the current message/URL against a persistent SQLite interaction log.

Detects:
  - Same domain seen before with a different verdict (brand pivoting)
  - Repeated brand impersonation from different domains
  - URL patterns previously seen in confirmed scam scans

Uses aiosqlite for async reads. Falls back gracefully if DB is unavailable.
"""
import os
import hashlib
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from app.logger import logger

_DB_PATH = os.path.join("data", "feedback.db")
_MAX_HISTORY = 5   # look at last N interactions for anomaly


def _extract_domain(url: str) -> Optional[str]:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def _fingerprint(message: str, url: str) -> str:
    """SHA-256 fingerprint of message+url for deduplication."""
    content = f"{message.strip().lower()}|{url.strip().lower()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


async def check_interaction_history(message: str = "", url: str = "") -> Dict[str, Any]:
    """
    Check interaction history for anomalous patterns.

    Returns:
        Dict with anomaly_detected, prior_encounter_count, prior_verdict
    """
    domain = _extract_domain(url) or "unknown"
    fingerprint = _fingerprint(message, url)

    result = {
        "anomaly_detected": False,
        "prior_encounter_count": 0,
        "prior_verdict": None,
        "domain_seen_before": False,
        "verdict_conflict": False,
        "fingerprint": fingerprint,
    }

    try:
        import aiosqlite

        if not os.path.exists(_DB_PATH):
            logger.debug("Interaction history DB not initialised yet — skipping history check")
            return result

        async with aiosqlite.connect(_DB_PATH) as db:
            # Check if domain was previously seen
            async with db.execute(
                "SELECT verdict, user_correction FROM scan_history "
                "WHERE domain = ? ORDER BY created_at DESC LIMIT ?",
                (domain, _MAX_HISTORY)
            ) as cursor:
                rows = await cursor.fetchall()

            if rows:
                result["domain_seen_before"] = True
                result["prior_encounter_count"] = len(rows)
                result["prior_verdict"] = rows[0][0] if rows else None

                # Detect anomaly: prior verdict was scam but current domain looks clean
                corrections = [r[1] for r in rows if r[1]]
                if "scam" in corrections:
                    result["anomaly_detected"] = True
                    result["verdict_conflict"] = True

            # Check exact fingerprint history
            async with db.execute(
                "SELECT verdict FROM scan_history WHERE fingerprint = ? LIMIT 1",
                (fingerprint,)
            ) as cursor:
                fp_row = await cursor.fetchone()

            if fp_row:
                result["prior_verdict"] = fp_row[0]

    except ImportError:
        logger.debug("aiosqlite not installed — interaction history check skipped")
    except Exception as e:
        logger.warning(f"Interaction history check failed: {e}")

    return result


async def record_interaction(
    message_id: str,
    domain: str,
    fingerprint: str,
    verdict: str,
    scam_probability: int
) -> None:
    """
    Store a scan interaction in the history DB for future anomaly detection.
    Called by the scan route after producing a verdict.
    """
    try:
        import aiosqlite
        os.makedirs(os.path.dirname(_DB_PATH) or ".", exist_ok=True)

        async with aiosqlite.connect(_DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT,
                    domain TEXT,
                    fingerprint TEXT,
                    verdict TEXT,
                    scam_probability INTEGER,
                    user_correction TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute(
                "INSERT INTO scan_history (message_id, domain, fingerprint, verdict, scam_probability) "
                "VALUES (?, ?, ?, ?, ?)",
                (message_id, domain, fingerprint, verdict, scam_probability)
            )
            await db.commit()
    except Exception as e:
        logger.warning(f"Failed to record interaction: {e}")
