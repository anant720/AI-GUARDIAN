"""
scam_probability_calculator.py
────────────────────────────────
Computes the final adaptive weighted scam probability across ALL phases.

Weighting (Phase 5 formula):
  URL Intelligence       30%
  Message Intelligence   25%
  Threat Intelligence    15%
  LLM Verdict            30%

  LLM floor: when LLM confidence >= 0.70, max(base, llm_prob*0.85) is used
  to prevent weighted averaging from diluting high-confidence LLM verdicts.

Phase 5 modifiers (additive — max points each):
  urgency_detected              +5–12  (scaled by severity)
  manipulation_patterns (≥3)   +8
  template_match (sim≥0.75)    +12
  intent_conflict               +5–12
  js_obfuscation               +8
  brand_mismatch               +5–10
  redirect_cloaking            +8
  credential_request           +5
  financial_pressure           +5

Total capped at 100.
"""
from typing import Dict, Any

from app.logger import logger


def calculate_adaptive_score(
    url_report:      Dict[str, Any],
    message_report:  Dict[str, Any],
    threat_report:   Dict[str, Any],
    llm_verdict:     Dict[str, Any],
    behavioral:      Dict[str, Any],
    semantic:        Dict[str, Any],
    domain_behavior: Dict[str, Any]
) -> int:
    """
    Compute the weighted adaptive scam probability (0-100).
    """
    # ── Base weighted scores ──────────────────────────────────────────────────
    url_score = url_report.get("risk_score", 0)

    msg_score = 0
    if message_report:
        msg_score = (
            message_report
            .get("message_analysis", {})
            .get("score_details", {})
            .get("message_risk_score", 0)
        )

    ti_score  = threat_report.get("threat_score", 0)
    llm_prob  = llm_verdict.get("scam_probability") or 0
    llm_conf  = llm_verdict.get("confidence") or 0.0

    # Weighted base (standard formula)
    base = (
        url_score  * 0.30 +
        msg_score  * 0.25 +
        ti_score   * 0.15 +
        llm_prob   * 0.30
    )

    # When LLM has high confidence, use it as a floor
    # Prevents the weighted average from pulling a 95% LLM verdict down to 60%
    if llm_conf >= 0.70:
        base = max(base, llm_prob * 0.85)

    # ── Phase 5 additive modifiers ────────────────────────────────────────────
    modifiers = 0

    timing = behavioral.get("timing_analysis", {})
    if timing.get("time_pressure"):
        sev = timing.get("severity", 0.3)
        modifiers += max(5, int(sev * 12))  # 5-12 pts

    seq = behavioral.get("sequence_analysis", {})
    sep = seq.get("social_engineering_patterns", [])
    if len(sep) >= 3:
        modifiers += 8
    elif len(sep) >= 2:
        modifiers += 4

    template = semantic.get("template_matching", {})
    sim = semantic.get("contextual_similarity", {}).get("max_similarity", 0)
    if template.get("template_matched") and sim >= 0.75:
        modifiers += 12
    elif template.get("template_matched") and sim >= 0.50:
        modifiers += 7
    elif template.get("template_matched"):
        modifiers += 4

    conflict = semantic.get("intent_conflict", {})
    if conflict.get("conflict_detected"):
        modifiers += max(5, int(conflict.get("mismatch_severity", 0) * 12))

    obf = domain_behavior.get("js_obfuscation", {})
    if obf.get("obfuscation_detected"):
        modifiers += 8

    cm = domain_behavior.get("content_mismatch", {})
    if cm.get("brand_mismatch"):
        modifiers += max(5, int(cm.get("mismatch_confidence", 0) * 10))

    redir = domain_behavior.get("redirect_analysis", {})
    if redir.get("cloaking_detected"):
        modifiers += 8
    elif redir.get("domain_changed") and redir.get("redirect_count", 0) > 1:
        modifiers += 3

    # Credential / financial signals from sequence analysis
    if seq.get("credential_request"):
        modifiers += 5
    if seq.get("financial_pressure"):
        modifiers += 5

    adaptive_score = int(min(base + modifiers, 100))

    logger.info(
        f"Adaptive score: base={base:.1f} modifiers={modifiers} "
        f"final={adaptive_score} | llm={llm_prob}% conf={llm_conf:.2f}"
    )
    return adaptive_score
