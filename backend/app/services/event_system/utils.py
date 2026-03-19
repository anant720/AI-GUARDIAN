"""
phase8/utils.py — Phase 8 helper functions
"""
from datetime import datetime, timezone
import json

def utcnow_str() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()

def serialize_payload(payload: dict) -> str:
    """Safely serialize event payloads to JSON."""
    return json.dumps(payload, default=str)

def deserialize_payload(raw: str) -> dict:
    """Safely deserialize event payloads from JSON."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
