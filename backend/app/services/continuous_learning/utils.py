"""
utils.py — Phase 6 helper utilities
─────────────────────────────────────
• PII masking
• JSONL validation
• Cost estimation
• Accuracy metrics (precision, recall, F1)
"""
import re
import json
import os
from typing import List, Dict, Any, Tuple

from app.logger import logger

# ── PII masking patterns ───────────────────────────────────────────────────────
_PII_PATTERNS = [
    (r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',             '[PAN_REDACTED]'),     # PAN card
    (r'\b[2-9]{1}[0-9]{3}\s[0-9]{4}\s[0-9]{4}\b', '[AADHAAR_REDACTED]'),# Aadhaar
    (r'\b\d{10}\b',                              '[PHONE_REDACTED]'),   # 10-digit mobile
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]'),
    (r'\b(?:\+91[-\s]?)?\d{10}\b',              '[PHONE_REDACTED]'),   # +91 mobile
    (r'\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b', '[CARD_REDACTED]'),  # card numbers
    (r'\b\d{9,18}\b',                           '[ACCOUNT_REDACTED]'), # bank account
]

_COMPILED_PII = [(re.compile(p, re.IGNORECASE), r) for p, r in _PII_PATTERNS]


def mask_pii(text: str) -> str:
    """Remove PII from free-text fields before storing/training."""
    if not text:
        return text
    for pattern, replacement in _COMPILED_PII:
        text = pattern.sub(replacement, text)
    return text.strip()


# ── JSONL validation ───────────────────────────────────────────────────────────
def validate_jsonl(path: str) -> Tuple[bool, int, List[str]]:
    """
    Validate a JSONL fine-tuning file.

    Returns:
        (valid: bool, entry_count: int, errors: list)
    """
    if not os.path.exists(path):
        return False, 0, [f"File not found: {path}"]

    errors = []
    count = 0
    required_keys = {"messages"}

    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                count += 1
                if not required_keys.issubset(obj.keys()):
                    errors.append(f"Line {i}: missing keys {required_keys - set(obj.keys())}")
                msgs = obj.get("messages", [])
                roles = [m.get("role") for m in msgs]
                if "system" not in roles or "user" not in roles or "assistant" not in roles:
                    errors.append(f"Line {i}: missing system/user/assistant message roles")
            except json.JSONDecodeError as e:
                errors.append(f"Line {i}: JSON parse error — {e}")

    valid = len(errors) == 0 and count > 0
    return valid, count, errors[:10]  # cap error list


# ── Cost estimation ────────────────────────────────────────────────────────────
# Rough cost per 1K tokens for fine-tuning (as of early 2026)
_COST_PER_1K_TOKENS = {
    "openai:gpt-3.5-turbo": 0.008,
    "openai:gpt-4o-mini":   0.012,
    "groq":                 0.0,    # Groq fine-tuning free/beta
    "gemini":               0.005,
}
_AVG_TOKENS_PER_EXAMPLE = 350  # rough estimate for scam detection examples


def estimate_cost(n_examples: int, provider: str, model: str = "") -> Dict[str, Any]:
    """Estimate fine-tuning cost before submitting."""
    key = f"{provider}:{model}" if model else provider
    rate = _COST_PER_1K_TOKENS.get(key, _COST_PER_1K_TOKENS.get(provider, 0.01))
    total_tokens = n_examples * _AVG_TOKENS_PER_EXAMPLE
    cost_usd = (total_tokens / 1000) * rate
    return {
        "n_examples": n_examples,
        "estimated_tokens": total_tokens,
        "estimated_cost_usd": round(cost_usd, 4),
        "provider": provider,
        "model": model,
        "note": "Rough estimate — actual cost depends on token count per example"
    }


# ── Accuracy metrics ───────────────────────────────────────────────────────────
def compute_metrics(
    predictions: List[str],
    ground_truth: List[str],
    positive_label: str = "scam"
) -> Dict[str, float]:
    """
    Compute precision, recall, F1, accuracy for binary classification.

    Args:
        predictions: List of system verdicts ("scam" | "safe")
        ground_truth: List of user-corrected labels
        positive_label: The positive class (default "scam")

    Returns:
        Dict with accuracy, precision, recall, f1, fp_rate, fn_rate
    """
    assert len(predictions) == len(ground_truth), "Length mismatch"

    tp = fp = tn = fn = 0
    for pred, true in zip(predictions, ground_truth):
        p = pred == positive_label
        t = true == positive_label
        if p and t:   tp += 1
        elif p and not t: fp += 1
        elif not p and t: fn += 1
        else:         tn += 1

    total = tp + fp + tn + fn
    accuracy  = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fp_rate   = fp / (fp + tn) if (fp + tn) else 0.0
    fn_rate   = fn / (fn + tp) if (fn + tp) else 0.0

    return {
        "accuracy":  round(accuracy, 4),
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1":        round(f1, 4),
        "fp_rate":   round(fp_rate, 4),
        "fn_rate":   round(fn_rate, 4),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "total": total
    }
