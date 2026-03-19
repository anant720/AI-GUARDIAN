"""
phase7/utils.py — helpers for Phase 7
"""
import re
from datetime import datetime, timezone


# PII patterns (augments phase6 list with additional Indian ID formats)
_PII = [
    (re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b'),                  '[PAN]'),
    (re.compile(r'\b[2-9]\d{3}\s\d{4}\s\d{4}\b'),               '[AADHAAR]'),
    (re.compile(r'(?<!\d)(?:\+?91[-\s]?)?\d{10}(?!\d)'),         '[PHONE]'),
    (re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'),
                                                                   '[EMAIL]'),
    (re.compile(r'\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b'),    '[CARD]'),
    (re.compile(r'\b\d{9,18}\b'),                                 '[ACCOUNT]'),
]


def mask_message_pii(text: str) -> str:
    """Remove PII from notification message text before DB insert."""
    if not text:
        return text
    for pattern, tag in _PII:
        text = pattern.sub(tag, text)
    return text.strip()


def utcnow_str() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def safe_int(val, default: int = 0) -> int:
    """Safe int cast with default."""
    try:
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default
