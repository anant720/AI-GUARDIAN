"""
feedback_processor.py — Phase 6
─────────────────────────────────
Cleans and validates raw feedback from scan_feedback table.

Steps:
  1. Fetch all unprocessed feedback records from SQLite
  2. Filter: remove invalid URLs, missing verdicts, empty content
  3. Deduplicate: keep latest correction per message_id
  4. Mask PII in notes fields
  5. Assign confidence score to each record:
     - HIGH   (0.9) : TI + LLM both agreed with correction
     - MEDIUM (0.6) : Only LLM agreed OR only TI agreed
     - LOW    (0.3) : No corroborating signal — user-correction only
  6. Return List[LabeledExample] for dataset_generator
"""
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

from app.logger import logger
from app.services.continuous_learning.utils import mask_pii

_DB_PATH = os.path.join("data", "feedback.db")


@dataclass
class LabeledExample:
    message_id:       str
    url:              str
    message:          str = ""
    system_verdict:   str = "safe"
    user_correction:  str = "safe"
    scam_probability: int = 0
    notes:            str = ""
    confidence:       float = 0.6
    label:            str = "safe"   # final ground truth: "scam" | "safe"
    metadata:         Dict[str, Any] = field(default_factory=dict)


def _is_valid_url(url: str) -> bool:
    try:
        r = urlparse(url)
        return bool(r.scheme and r.netloc)
    except Exception:
        return False


def _assign_confidence(
    system_verdict: str,
    user_correction: str,
    scam_probability: int
) -> float:
    """
    Confidence in the user correction:
      HIGH   — system was close but wrong (probability 40-70%), likely genuine FP/FN
      MEDIUM — system was confident wrong (>70% on safe or <30% on scam)
      LOW    — ambiguous; probability near 50%
    """
    prob = scam_probability or 0
    is_fp = system_verdict == "scam" and user_correction == "safe"
    is_fn = system_verdict == "safe" and user_correction == "scam"

    if not (is_fp or is_fn):
        return 0.0  # system was correct — not useful for training

    if is_fp:
        # False positive: system over-flagged a safe URL
        if prob >= 75:   return 0.9   # high confidence system was wrong
        if prob >= 50:   return 0.7
        return 0.5
    else:
        # False negative: system under-flagged a scam
        if prob <= 25:   return 0.9
        if prob <= 45:   return 0.7
        return 0.5


async def process_feedback(
    min_confidence: float = 0.4,
    limit: int = 500
) -> List[LabeledExample]:
    """
    Fetch and clean feedback records from SQLite.

    Returns:
        List of LabeledExample, deduplicated and PII-masked,
        filtered to min_confidence threshold.
    """
    raw: List[Dict] = []

    try:
        import aiosqlite
        async with aiosqlite.connect(_DB_PATH) as db:
            async with db.execute(
                """SELECT message_id, url, system_verdict, user_correction,
                          scam_probability, notes, created_at
                   FROM scan_feedback
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()

        for row in rows:
            raw.append({
                "message_id":       row[0],
                "url":              row[1] or "",
                "system_verdict":   row[2] or "",
                "user_correction":  row[3] or "",
                "scam_probability": row[4] or 0,
                "notes":            row[5] or "",
                "created_at":       row[6] or ""
            })

    except ImportError:
        logger.warning("aiosqlite not installed — feedback processing skipped")
        return []
    except Exception as e:
        logger.warning(f"Feedback DB read failed: {e}")
        return []

    if not raw:
        logger.info("No feedback records found in database")
        return []

    # ── Deduplication: keep latest per message_id ─────────────────────────────
    seen: Dict[str, Dict] = {}
    for rec in raw:
        mid = rec["message_id"]
        if mid not in seen:
            seen[mid] = rec

    records = list(seen.values())

    # ── Filter, clean, label ──────────────────────────────────────────────────
    labeled: List[LabeledExample] = []
    skipped = 0

    for rec in records:
        url = rec["url"].strip()
        system  = rec["system_verdict"].strip().lower()
        correction = rec["user_correction"].strip().lower()

        # Skip: invalid URL, missing verdicts, or system was already correct
        if not _is_valid_url(url):
            skipped += 1
            continue
        if system not in ("scam", "safe") or correction not in ("scam", "safe"):
            skipped += 1
            continue
        if system == correction:
            continue  # system was already right — not needed for FT

        confidence = _assign_confidence(system, correction, rec["scam_probability"])

        if confidence < min_confidence:
            skipped += 1
            continue

        notes_clean = mask_pii(rec["notes"])

        labeled.append(LabeledExample(
            message_id=rec["message_id"],
            url=url,
            system_verdict=system,
            user_correction=correction,
            scam_probability=rec["scam_probability"],
            notes=notes_clean,
            confidence=confidence,
            label=correction,   # ground truth is what user says
            metadata={"created_at": rec.get("created_at", "")}
        ))

    # Sort by confidence DESC for best examples first
    labeled.sort(key=lambda x: x.confidence, reverse=True)

    logger.info(
        f"Feedback processed: {len(labeled)} usable examples "
        f"({skipped} skipped) from {len(records)} records"
    )
    return labeled
