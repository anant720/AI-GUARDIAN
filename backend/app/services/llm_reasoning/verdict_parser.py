"""
verdict_parser.py
─────────────────
Parses raw LLM string output into a validated, typed Python dict.

Guardrails enforced:
  - scam_probability  ∈  [0, 100]  (integer)
  - threat_type       ∈  allowed list
  - confidence        ∈  [0.0, 1.0]  (float)
  - explanation       ≤  500 characters (string)

Falls back to a safe rule-engine default if parsing or validation fails.
"""
import re
import json
from typing import Dict, Any
from app.logger import logger

# All accepted threat types (LLM outputs outside this set are corrected)
ALLOWED_THREAT_TYPES = {
    "phishing", "credential_phishing", "financial_fraud", "banking_fraud",
    "account_takeover", "malware_distribution", "ransomware", "tech_support_scam",
    "delivery_scam", "government_impersonation", "business_email_compromise",
    "invoice_fraud", "smishing", "vishing", "crypto_fraud", "romance_scam",
    "advance_fee_fraud", "identity_theft", "charity_fraud", "supply_chain_attack",
    "quishing", "spear_phishing", "safe"
}


# Default returned when LLM output is unparseable
_FALLBACK_VERDICT: Dict[str, Any] = {
    "scam_probability": 0,
    "threat_type": "safe",
    "confidence": 0.0,
    "explanation": "LLM verdict unavailable — falling back to rule engine score.",
    "llm_used": False
}


def _extract_json(raw: str) -> str:
    """
    Extract the LARGEST { ... } JSON block from the raw LLM response.
    Modern models often include conversational filler or markdown.
    """
    if isinstance(raw, tuple):
        logger.error(f"VERDICT_PARSER: Received TUPLE instead of string: {raw}")
        # Try to recover if it's (text, latency)
        if len(raw) > 0 and isinstance(raw[0], str):
            raw = raw[0]
        else:
            raw = str(raw)

    # Strip markdown code fences
    raw = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE).strip()

    # Find the outermost { and }
    start = raw.find('{')
    end = raw.rfind('}')
    
    if start != -1 and end != -1 and end > start:
        return raw[start:end+1]
        
    return raw


def _validate(verdict: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and coerce field values. Clamps out-of-range values instead of raising."""
    # scam_probability — clamp to [0, 100]
    prob = verdict.get("scam_probability")
    if prob is None:
        raise ValueError("Missing scam_probability")
    prob = max(0, min(100, int(float(prob))))
    verdict["scam_probability"] = prob

    # threat_type — unknown values default to "phishing"
    threat = str(verdict.get("threat_type", "")).lower().strip()
    if threat not in ALLOWED_THREAT_TYPES:
        logger.warning(f"Unknown threat_type '{threat}' — defaulting to 'phishing'")
        threat = "phishing"
    verdict["threat_type"] = threat

    # confidence — clamp to [0.0, 1.0]
    raw_conf = verdict.get("confidence")
    if raw_conf is None:
        conf = 0.5 # Neutral fallback if missing
    else:
        try:
            conf = float(raw_conf)
        except (ValueError, TypeError):
            conf = 0.5
            
    conf = max(0.01, min(1.0, conf)) # Floor at 1% to avoid "0%" confusion
    verdict["confidence"] = round(conf, 4)

    # explanation — truncate to 500 chars
    explanation = str(verdict.get("explanation", ""))[:500].strip()
    verdict["explanation"] = explanation

    return verdict


def parse_verdict(raw: str) -> Dict[str, Any]:
    """
    Parse and validate the raw LLM response into a structured verdict dict.

    Returns a fallback verdict dict (with llm_used=False) if parsing fails.
    """
    try:
        json_str = _extract_json(raw)
        data = json.loads(json_str)
        validated = _validate(data)
        validated["llm_used"] = True
        logger.info(f"LLM verdict parsed: threat={validated['threat_type']} prob={validated['scam_probability']}")
        return validated

    except json.JSONDecodeError as e:
        logger.error(f"Verdict JSON decode error: {e} | raw: {raw[:200]}")
    except ValueError as e:
        logger.error(f"Verdict validation error: {e} | raw: {raw[:200]}")
    except Exception as e:
        logger.error(f"Unexpected verdict parse error: {e}")

    logger.warning("Returning fallback verdict (rule-engine only)")
    return dict(_FALLBACK_VERDICT)
