"""
timing_detector.py
───────────────────
Detects artificial time-pressure language designed to rush victims
into acting before they can think critically.

Uses layered detection:
  1. Hard time-limit phrases ("within 24 hours", "expires tonight")
  2. Countdown / deadline language
  3. Immediate action demands
"""
import re
from typing import Dict, Any, List

from app.logger import logger

# ── Compiled pattern groups ────────────────────────────────────────────────────
_HARD_DEADLINE_PATTERNS = [
    r"\bwithin\s+\d+\s+(hour|minute|day|hr)s?\b",
    r"\bexpires?\s+(today|tonight|in\s+\d+\s+\w+)\b",
    r"\bdeadline\s+(is\s+)?(today|tonight|now)\b",
    r"\blast\s+(chance|opportunity|warning)\b",
    r"\bfinal\s+(notice|warning|reminder)\b",
    r"\bonly\s+\d+\s+(hour|minute|day)s?\s+(left|remaining)\b",
    r"\b(24|48|72)\s*[-\s]hour\b",
]

_COUNTDOWN_PATTERNS = [
    r"\b(limited\s+time|limited-time)\s*offer\b",
    r"\bcount\s*down\b",
    r"\btime\s+is\s+running\s+out\b",
    r"\bdon'?t\s+wait\b",
    r"\bbefore\s+it'?s?\s+too\s+late\b",
    r"\bact\s+(fast|quick|quickly|now|immediately)\b",
]

_IMMEDIATE_ACTION_PATTERNS = [
    r"\b(call|contact|reply|respond|verify|update|click|tap)\s+(now|immediately|urgently|asap)\b",
    r"\b(do\s+not\s+ignore|do\s+not\s+delay)\b",
    r"\bimmediately\s+(or|else|to\s+avoid)\b",
    r"\bto\s+avoid\s+(closure|suspension|termination|block|penalty|fine)\b",
    r"\bor\s+your\s+(account|access|funds|data)\s+will\s+be\b",
]


def _scan_patterns(text: str, patterns: List[str]) -> List[str]:
    hits = []
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            hits.append(m.group(0).strip())
    return hits


def detect_time_pressure(message: str) -> Dict[str, Any]:
    """
    Detect artificial time-pressure and deadline language in a message.

    Args:
        message: Raw message text

    Returns:
        Dict with time_pressure (bool), triggers (list), severity (0.0-1.0)
    """
    if not message or not message.strip():
        return {"time_pressure": False, "triggers": [], "severity": 0.0,
                "hard_deadline": False, "countdown": False, "immediate_action": False}

    text = message.lower()

    hard = _scan_patterns(text, _HARD_DEADLINE_PATTERNS)
    countdown = _scan_patterns(text, _COUNTDOWN_PATTERNS)
    immediate = _scan_patterns(text, _IMMEDIATE_ACTION_PATTERNS)

    all_triggers = hard + countdown + immediate
    time_pressure = bool(all_triggers)

    # Severity: hard deadlines weigh more
    severity = min(
        len(hard) * 0.35 +
        len(countdown) * 0.25 +
        len(immediate) * 0.25,
        1.0
    )

    logger.info(
        f"Timing analysis: pressure={time_pressure} severity={severity:.2f} "
        f"triggers={len(all_triggers)}"
    )

    return {
        "time_pressure": time_pressure,
        "triggers": list(set(all_triggers))[:8],
        "severity": round(severity, 3),
        "hard_deadline": bool(hard),
        "countdown": bool(countdown),
        "immediate_action": bool(immediate),
    }
