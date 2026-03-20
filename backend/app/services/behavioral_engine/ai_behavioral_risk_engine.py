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

    # ── Concurrent Phase 5 sub-engine execution with 10.0s strict timeout ──────
    try:
        behavioral, semantic, domain_behavior = await asyncio.wait_for(
            asyncio.gather(
                analyze_behavior(message, url),
                assess_semantic_risk(message, url, url_signals),
                analyze_domain_behavior(url, cached_html, claimed_brand or None)
            ),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        logger.warning(f"Adaptive Behavioral sub-engines timed out after 10.0s for {url}")
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

    # Prepare extraction variables for summary builder
    timing = behavioral.get("timing_analysis", {})
    seq = behavioral.get("sequence_analysis", {})
    conflict = semantic.get("intent_conflict", {})
    claimed_brand = conflict.get("claimed_brand") or conflict.get("brand") or "a known brand"

    # 0. High-Level "Perfect" Evidence (The Summary)
    # If the risk is high, provide a technical, human-readable summary
    if adaptive_score >= 15:
        summary_parts = []
        
        # Priority 1: High-Confidence AI Insight (Filtered for accuracy)
        is_safe_ai = llm_verdict.get("threat_type") == "safe"
        has_mismatch = conflict.get("conflict_detected")
        
        if llm_verdict.get("confidence", 0) >= 0.75:
            if is_safe_ai and has_mismatch:
                summary_parts.append(f"System detected a brand mismatch despite a professional message tone")
            else:
                threat = llm_verdict.get("threat_type", "scam").replace("_", " ")
                summary_parts.append(f"AI identifies this as a potential {threat}")

        # Priority 2: Message & Tone
        if seq.get("financial_pressure") or seq.get("reward_bait"):
            summary_parts.append("uses financial/reward baiting")
        if seq.get("credential_request"):
            summary_parts.append("requests sensitive credentials or identity verification")
        if timing.get("time_pressure"):
            summary_parts.append("employs high psychological urgency")
        if seq.get("authority_claim"):
            summary_parts.append("claims questionable official authority")
        
        # Priority 3: Infrastructure
        if has_mismatch:
            summary_parts.append(f"contains a deceptive domain mismatch impersonating {claimed_brand}")
        
        if summary_parts:
            # Combine into a perfect sentence
            main_point = summary_parts[0]
            others = summary_parts[1:]
            if others:
                summary = f"{main_point} which {', '.join(others[:-1])}{' and ' if len(others) > 1 else ''}{others[-1]}."
            else:
                summary = f"{main_point}."
            evidence.append(summary)

    # 1. Critical Conflicts & Verified Threats
    if threat_report.get("phishing_match"):
        evidence.append("GLOBAL ALERT: Known phishing signature detected in database")
    
    if conflict.get("conflict_detected"):
        evidence.append(f"BRAND DECEPTION: Claims to be {claimed_brand} but links to a different domain")

    # 2. Specific Attack Vectors
    if seq.get("financial_pressure") or "crypto" in message.lower():
        evidence.append("ASSET DRAINER: Detected patterns common in wallet/crypto-drainer attacks")
    
    if seq.get("credential_request"):
        evidence.append("CREDENTIAL HARVESTING: Detected attempts to solicit login or personal data")

    # 3. Pattern Match (Highly strict)
    template = semantic.get("template_matching", {})
    sim = semantic.get("contextual_similarity", {}).get("max_similarity", 0)
    if template.get("template_matched") and sim >= 0.8:
        evidence.append(f"SIGNATURE MATCH: High-fidelity match to known '{template['matched_template'].get('title')}' pattern")

    # 4. Behavioral Signals (Professional Labels)
    if timing.get("time_pressure"):
        evidence.append(f"PSYCHOLOGICAL TRIGGER: Use of urgency to bypass user critical thinking")
    
    if seq.get("authority_claim") or seq.get("threat_detected"):
        evidence.append("AUTHORITY IMPERSONATION: Claims official power to coerce action")

    # 5. Infrastructure & DNS
    obf = domain_behavior.get("js_obfuscation", {})
    if obf.get("obfuscation_detected"):
        evidence.append(f"Technical obfuscation: JS-layer hiding detected")

    redir = domain_behavior.get("redirect_analysis", {})
    if redir.get("cloaking_detected"):
        evidence.append("Cloaking: Page is hiding from security scanners")
    
    if threat_report.get("phishing_match"):
        evidence.append("Verified threat: Found in global phishing database")
    if threat_report.get("malware_detected"):
        evidence.append("Malware: URL is blacklisted for malicious payloads")

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
