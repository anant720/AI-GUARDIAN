"""
app/core/response_builder.py
─────────────────────────────
Builds the final API response from a completed ScanContext.

Decouples response shaping from pipeline orchestration logic.
All formatting changes happen here — pipeline stays clean.
"""
from typing import Any, Dict
from app.core.context_builder import ScanContext


def build_scan_response(ctx: ScanContext) -> Dict[str, Any]:
    """
    Build the final /scan API response from a completed ScanContext.
    Human-readable verdict and all phase outputs.
    """
    score = ctx.final_score

    # ── Verdict Label ─────────────────────────────────────────────────────────
    # ── Verdict Label ─────────────────────────────────────────────────────────
    if score >= 60:
        verdict = "SCAM DETECTED"
        risk_level = "critical"
    elif score >= 30:
        verdict = "SUSPICIOUS"
        risk_level = "high"
    elif score >= 15:
        verdict = "LOW RISK"
        risk_level = "medium"
    else:
        verdict = "SAFE"
        risk_level = "low"

    # ── Explanation Priority ──────────────────────────────────────────────────
    # If LLM has high confidence, its explanation is usually the best
    if ctx.llm.used and (ctx.llm.confidence or 0) >= 0.7:
        final_explanation = ctx.llm.explanation
    else:
        final_explanation = ctx.behavioral.explanation or ctx.llm.explanation or "No significant threat signals detected."

    # ── Evidence Collection ───────────────────────────────────────────────────
    evidence = list(dict.fromkeys(ctx.behavioral.evidence + ctx.rag_evidence))
    if ctx.llm.used and ctx.llm.scam_probability and ctx.llm.scam_probability >= 50:
        llm_tag = f"AI Analysis: {ctx.llm.threat_type or 'Significant scam patterns'} detected"
        if llm_tag not in evidence:
            evidence.insert(0, llm_tag)

    # ── Core Response ─────────────────────────────────────────────────────────
    response: Dict[str, Any] = {
        "message_id": ctx.message_id,
        "verdict": verdict,
        "risk_level": risk_level,
        "combined_score": score,
        "confidence_score": int((ctx.llm.confidence or 0) * 100) if ctx.llm.used else 0,
        "evidence": evidence,
        "explanation": final_explanation,

        # ── Simplified Metrics ────────────────────────────────────────────────
        "main_metrics": {
            "risk_score": score,
            "confidence": int((ctx.llm.confidence or 0) * 100) if ctx.llm.used else 0
        },

        # ── Simplified Analytics Discovery ─────────────────────────────────────
        "system_discovery": {
            "risk_score": score,
            "confidence": int((ctx.llm.confidence or 0) * 100) if ctx.llm.used else 0
        },

        # ── Threat Intel Summary ──────────────────────────────────────────────
        "threat_intelligence": {
            "domain_reputation": ctx.threat_signals.domain_reputation,
            "ip_risk_score":     ctx.threat_signals.ip_risk_score,
            "phishing_match":    ctx.threat_signals.phishing_match,
            "malware_detected":  ctx.threat_signals.malware_detected,
            "domain_age_days":   ctx.threat_signals.domain_age_days,
            "domain_age_flag":   ctx.threat_signals.domain_age_flag,
            "threat_score":      ctx.threat_signals.threat_score,
        },

        # ── Behavioral Analysis ───────────────────────────────────────────────
        "behavioral_analysis":  ctx.behavioral.behavioral_analysis,
        "semantic_risk":        ctx.behavioral.semantic_risk,
        "domain_behavior":      ctx.behavioral.domain_behavior,

        # ── Profiling ─────────────────────────────────────────────────────────
        "performance": {
            "timings_ms": ctx.timings,
            "total_ms": sum(ctx.timings.values()),
            "llm_used":   ctx.llm.used,
            "llm_cached": ctx.llm.cached,
            "llm_skipped_reason": ctx.llm.skipped_reason,
        }
    }

    # ── URL Report (if available) ─────────────────────────────────────────────
    if ctx.url_report and "error" not in ctx.url_report:
        response["url_report"] = ctx.url_report

    # ── Message Report (if available) ─────────────────────────────────────────
    if ctx.message_report and "error" not in ctx.message_report:
        response["message_report"] = ctx.message_report

    # ── LLM Verdict (if used) ─────────────────────────────────────────────────
    if ctx.llm.used:
        response["llm_verdict"] = {
            "scam_probability": ctx.llm.scam_probability,
            "threat_type":      ctx.llm.threat_type,
            "confidence":       ctx.llm.confidence,
            "llm_used":         True
        }

    return response
