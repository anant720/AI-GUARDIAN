"""
ai_behavioral_risk_engine.py
──────────────────────────────
Adaptive Behavioral Engine master orchestrator. Runs all 3 sub-engines concurrently
alongside the signal map and produces a unified BehavioralReport.

Concurrent execution:
  asyncio.gather(
    behavioral_analysis,   ← Sub-Engine 1
    semantic_risk,         ← Sub-Engine 2
    dynamic_domain         ← Sub-Engine 3
  )
"""
import asyncio
from typing import Dict, Any, Optional

from app.logger import logger
from app.services.behavioral_analysis import analyze_behavior
from app.services.semantic_risk import assess_semantic_risk
from app.services.dynamic_domain import analyze_domain_behavior
from app.services.behavioral_engine.scam_probability_calculator import calculate_adaptive_score
from app.services.behavioral_engine.explanation_generator import generate_explanation


async def run_behavioral_analysis(
    url: str,
    message: str = "",
    url_report: Optional[Dict[str, Any]] = None,
    message_report: Optional[Dict[str, Any]] = None,
    threat_report: Optional[Dict[str, Any]] = None,
    llm_verdict: Optional[Dict[str, Any]] = None,
    rag_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Full Adaptive Behavioral analysis pipeline.

    Args:
        url: Scanned URL
        message: User-submitted message text
        url_report: URL Signal output
        message_report: Message Signal output
        threat_report: Threat Intel output
        llm_verdict: AI Reasoning verdict dict
        rag_context: RAG context string

    Returns:
        BehavioralReport with adaptive scam_probability, evidence, explanation.
    """
    url_report     = url_report     or {}
    message_report = message_report or {}
    threat_report  = threat_report  or {}
    llm_verdict    = llm_verdict    or {}

    # Extract signals for sub-engines
    url_signals = url_report.get("signals", {})
    cached_html = url_report.get("detailed_report", {}).get("page_intel", {}).get("html_content", "")
    claimed_brand = (
        url_signals.get("brand_impersonation")
        or llm_verdict.get("threat_type", "")
    )

    logger.info(f"Adaptive Behavioral analysis starting for: {url}")

    # ── Concurrent Phase 5 sub-engine execution with 2.0s strict timeout ──────
    try:
        behavioral, semantic, domain_behavior = await asyncio.wait_for(
            asyncio.gather(
                analyze_behavior(message, url),
                assess_semantic_risk(message, url, url_signals),
                analyze_domain_behavior(url, cached_html, claimed_brand or None)
            ),
            timeout=2.0
        )
    except asyncio.TimeoutError:
        logger.warning(f"Adaptive Behavioral sub-engines timed out after 2.0s for {url}")
        # Fallback to neutral results
        behavioral, semantic, domain_behavior = {}, {}, {}
    except Exception as e:
        logger.error(f"Error in Behavioral Engine concurrent execution: {e}")
        behavioral, semantic, domain_behavior = {}, {}, {}

    # ── Adaptive combined score ───────────────────────────────────────────────
    adaptive_score = calculate_adaptive_score(
        url_report=url_report,
        message_report=message_report,
        threat_report=threat_report,
        llm_verdict=llm_verdict,
        behavioral=behavioral,
        semantic=semantic,
        domain_behavior=domain_behavior
    )

    # ── Human-readable explanation ────────────────────────────────────────────
    explanation = generate_explanation(
        url=url,
        behavioral=behavioral,
        semantic=semantic,
        domain_behavior=domain_behavior,
        threat_report=threat_report,
        llm_verdict=llm_verdict,
        adaptive_score=adaptive_score
    )

    # ── Evidence list (ranked by strength) ───────────────────────────────────
    evidence: list = []

    conflict = semantic.get("intent_conflict", {})
    if conflict.get("conflict_detected"):
        evidence.append(f"Brand conflict: {conflict.get('conflict_reason', 'domain mismatch')}")

    timing = behavioral.get("timing_analysis", {})
    if timing.get("time_pressure"):
        triggers = ", ".join(timing.get("triggers", [])[:2])
        evidence.append(f"Urgency: {triggers}")

    template = semantic.get("template_matching", {})
    if template.get("template_matched"):
        sim = semantic.get("contextual_similarity", {}).get("max_similarity", 0)
        evidence.append(
            f"Template match: '{template['matched_template'].get('title')}' "
            f"(similarity {sim:.2f})"
        )

    obf = domain_behavior.get("js_obfuscation", {})
    if obf.get("obfuscation_detected"):
        evidence.append(f"JS obfuscation: {', '.join(obf.get('indicators', [])[:2])}")

    redir = domain_behavior.get("redirect_analysis", {})
    if redir.get("cloaking_detected"):
        evidence.append("Redirect cloaking detected")
    elif redir.get("domain_changed"):
        evidence.append(f"Domain redirect: → {redir.get('final_domain')}")

    seq = behavioral.get("sequence_analysis", {})
    sep = seq.get("social_engineering_patterns", [])
    if sep:
        evidence.append(f"Social engineering: {', '.join(sep[:3])}")

    if threat_report.get("phishing_match"):
        evidence.append("Phishing database match")
    if threat_report.get("malware_detected"):
        evidence.append("Malware detected in URL")

    logger.info(
        f"Behavioral Engine complete — adaptive_score={adaptive_score} "
        f"behavioral={behavioral.get('behavioral_risk_score')} "
        f"semantic={semantic.get('semantic_risk_score')} "
        f"domain={domain_behavior.get('domain_behavior_risk_score')} "
        f"evidence_count={len(evidence)}"
    )

    return {
        "scam_probability": adaptive_score,
        "behavioral_analysis": {
            "risk_score": behavioral.get("behavioral_risk_score"),
            "urgency":    timing.get("time_pressure"),
            "manipulation_cues": seq.get("social_engineering_patterns", []),
        },
        "semantic_risk": {
            "risk_score": semantic.get("semantic_risk_score"),
            "max_similarity": semantic.get("contextual_similarity", {}).get("max_similarity"),
            "template_matched": template.get("template_matched"),
            "intent_conflict": conflict.get("conflict_detected"),
        },
        "domain_behavior": {
            "risk_score": domain_behavior.get("domain_behavior_risk_score"),
            "cloaking": redir.get("cloaking_detected"),
            "js_obfuscation": obf.get("obfuscation_detected"),
            "brand_mismatch": domain_behavior.get("content_mismatch", {}).get("brand_mismatch"),
        },
        "evidence": evidence,
        "explanation": explanation
    }
