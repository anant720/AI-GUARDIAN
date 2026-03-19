"""
explanation_generator.py
─────────────────────────
Generates a structured, human-readable explanation for every verdict,
citing specific evidence from all intelligence signal layers.

Output format:
  "Brand conflict: message claims 'SBI' but domain 'sbi-kyc-update.co.in'
  is not an official SBI domain. Urgency detected: 'avoid account closure'.
  Template similarity: 0.74 with 'Bank of America Account Alert'.
  TI score: 47 (domain flagged malicious). LLM: banking_fraud (85%)."
"""
from typing import Dict, Any, Optional, List

from app.logger import logger


def generate_explanation(
    url: str,
    behavioral: Dict[str, Any],
    semantic: Dict[str, Any],
    domain_behavior: Dict[str, Any],
    threat_report: Dict[str, Any],
    llm_verdict: Dict[str, Any],
    adaptive_score: int
) -> str:
    """
    Build human-readable explanation from all signal layers.

    Returns:
        Single multi-sentence explanation string (max ~500 chars)
    """
    sentences: List[str] = []

    # ── Intent Conflict ───────────────────────────────────────────────────────
    conflict = semantic.get("intent_conflict", {})
    if conflict.get("conflict_detected"):
        sentences.append(conflict.get("conflict_reason", "Brand-domain mismatch detected"))

    # ── Urgency / timing ─────────────────────────────────────────────────────
    timing = behavioral.get("timing_analysis", {})
    if timing.get("time_pressure"):
        triggers = timing.get("triggers", [])
        if triggers:
            sentences.append(f"Urgency tactic detected: '{triggers[0]}'")
        else:
            sentences.append("Artificial time-pressure detected in message")

    # ── Sequence / manipulation ───────────────────────────────────────────────
    seq = behavioral.get("sequence_analysis", {})
    sep = seq.get("social_engineering_patterns", [])
    if sep:
        sentences.append(f"Social engineering signals: {', '.join(sep[:3])}")

    # ── Template match ────────────────────────────────────────────────────────
    template = semantic.get("template_matching", {})
    sim_data = semantic.get("contextual_similarity", {})
    if template.get("template_matched") and template.get("matched_template"):
        title = template["matched_template"].get("title", "unknown")
        sim   = sim_data.get("max_similarity", 0)
        sentences.append(
            f"Template similarity {sim:.2f} with '{title}'"
        )

    # ── Domain behavior ───────────────────────────────────────────────────────
    redir = domain_behavior.get("redirect_analysis", {})
    if redir.get("cloaking_detected"):
        sentences.append("Redirect cloaking detected (meta-refresh / JS redirect)")
    elif redir.get("domain_changed"):
        sentences.append(f"Domain redirect to '{redir.get('final_domain')}'")

    obf = domain_behavior.get("js_obfuscation", {})
    if obf.get("obfuscation_detected"):
        indicators = obf.get("indicators", [])
        sentences.append(f"JS obfuscation ({', '.join(indicators[:2])})")

    cm = domain_behavior.get("content_mismatch", {})
    if cm.get("brand_mismatch"):
        sentences.append(
            f"Page content does not match claimed brand '{cm.get('claimed_brand')}'"
        )

    # ── Threat intelligence ───────────────────────────────────────────────────
    ti_score = threat_report.get("threat_score", 0)
    ti_rep   = threat_report.get("domain_reputation", "unknown")
    if ti_score >= 20 or ti_rep in ("suspicious", "malicious"):
        sentences.append(
            f"TI: domain {ti_rep}, score {ti_score}/100"
        )
    if threat_report.get("phishing_match"):
        sentences.append("Matches phishing database records")
    if threat_report.get("malware_detected"):
        sentences.append("Malware indicator detected in URL path")

    # ── LLM verdict ───────────────────────────────────────────────────────────
    if llm_verdict.get("llm_used"):
        prob  = llm_verdict.get("scam_probability", 0)
        ttype = llm_verdict.get("threat_type", "unknown")
        conf  = llm_verdict.get("confidence", 0)
        sentences.append(
            f"LLM classified: {ttype} (probability {prob}%, confidence {conf:.0%})"
        )

    # ── Construct final explanation ────────────────────────────────────────────
    if not sentences:
        if adaptive_score >= 60:
            explanation = "Multiple low-confidence risk signals combined to flag this scan."
        else:
            explanation = "No significant threat signals detected across all analysis layers."
    else:
        explanation = ". ".join(sentences) + "."

    # Cap length
    if len(explanation) > 500:
        explanation = explanation[:497] + "..."

    logger.debug(f"Generated explanation ({len(explanation)} chars)")
    return explanation
