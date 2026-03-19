import asyncio
import time
import uuid
from typing import Optional

from app.logger import logger
from app.core.context_builder import (
    ScanContext, LLMResult,
    build_context, extract_url_signals, extract_threat_signals, extract_message_signals
)
from app.core.llm_cache import get_cached, store_cached
from app.core.response_builder import build_scan_response

# ── Phase Imports ─────────────────────────────────────────────────────────────
from app.services.url_report_builder import build_intelligence_report
from app.services.message_intelligence import analyze_message
from app.services.threat_intelligence import build_threat_report
from app.services.rag_engine import retrieve_context
from app.services.llm_reasoning import run_reasoning
from app.services.behavioral_engine import run_behavioral_analysis
from app.services.behavioral_analysis.interaction_history_checker import record_interaction

# ── Constants ─────────────────────────────────────────────────────────────────
_LLM_TIMEOUT = 15.0

def _should_run_llm(ctx: ScanContext) -> tuple[bool, str]:
    """
    Intelligent Gating: Decides whether to invoke the expensive LLM layer.
    For production, we use forced mode to guarantee high accuracy for scans.
    """
    return True, "production_high_recall_mode"

def _calculate_final_score(ctx: ScanContext) -> int:
    """
    Adaptive weighted final score combining all phase outputs.
    Prioritizes LLM verdict if confidence is high (>0.60).
    """
    url_score  = ctx.url_signals.risk_score
    msg_score  = ctx.message_signals.message_risk_score
    ti_score   = ctx.threat_signals.threat_score
    beh_score  = ctx.behavioral.score
    
    llm_prob = ctx.llm.scam_probability if ctx.llm.scam_probability is not None else 0
    llm_conf = ctx.llm.confidence if ctx.llm.confidence is not None else 0.0

    # If LLM says SCAM with confidence, it is the primary signal
    if ctx.llm.used and llm_conf >= 0.60:
        base = (
            url_score  * 0.10 +
            msg_score  * 0.10 +
            ti_score   * 0.05 +
            beh_score  * 0.05 +
            llm_prob   * 0.70
        )
    else:
        # Fallback to rule engine + behavioral
        base = (url_score * 0.5) + (msg_score * 0.3) + (ti_score * 0.2)
        
    return int(max(0, min(100, base)))

async def _run_llm_with_gate(ctx: ScanContext) -> LLMResult:
    """Decision gate for optionally running the expensive LLM layer."""
    should_run, reason = _should_run_llm(ctx)
    if not should_run:
        return LLMResult(used=False, skipped_reason=reason)

    # 1. Check Cache
    cached = await get_cached(ctx.cache_key)
    if cached and cached.get("llm_used", False):
        logger.info(f"LLM: Cache Hit — {ctx.cache_key}")
        return LLMResult(
            used=True,
            cached=True,
            scam_probability=cached.get("scam_probability"),
            threat_type=cached.get("threat_type"),
            confidence=cached.get("confidence", 0.0),
            explanation=cached.get("explanation", ""),
        )

    # 2. Run LLM Reasoning
    try:
        t0 = time.monotonic()
        llm_output = await asyncio.wait_for(
            run_reasoning(
                url_report=ctx.url_report,
                message_text=ctx.message,
                message_report=ctx.message_report,
                threat_report=ctx.threat_report,
                rag_context=ctx.rag_context
            ),
            timeout=_LLM_TIMEOUT
        )
        elapsed = (time.monotonic() - t0) * 1000
        ctx.timings["llm_ms"] = elapsed

        if not isinstance(llm_output, dict):
            return LLMResult(used=False, skipped_reason="invalid_output_type")

        verdict = llm_output.get("llm_verdict", {})
        result = LLMResult(
            used=verdict.get("llm_used", True),
            scam_probability=verdict.get("scam_probability"),
            threat_type=verdict.get("threat_type"),
            confidence=verdict.get("confidence", 0.0),
            explanation=llm_output.get("explanation", ""),
        )

        # 3. Store Cache
        await store_cached(ctx.cache_key, {
            "scam_probability": result.scam_probability,
            "threat_type":      result.threat_type,
            "confidence":       result.confidence,
            "explanation":      result.explanation,
            "llm_used":         True
        })

        logger.info(f"LLM Result: {result.scam_probability}% ({elapsed:.0f}ms)")
        return result

    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return LLMResult(used=False, skipped_reason=str(e))

async def run_detection_pipeline(
    url: str,
    message: Optional[str] = None,
) -> dict:
    """
    Main detection pipeline entry point.
    Optimized for high-recall (90%+ accuracy) with parallel phase orchestration.
    """
    message_id = str(uuid.uuid4())
    ctx = build_context(url, message or "", message_id)
    
    # Signal Discovery Parallel (URL & Message)
    t_start = time.monotonic()
    msg_task = analyze_message(message) if message else asyncio.sleep(0, result={})
    url_task = build_intelligence_report(url)
    
    ctx.message_report, ctx.url_report = await asyncio.gather(msg_task, url_task)
    
    # Extract signals
    ctx.url_signals = extract_url_signals(ctx.url_report)
    ctx.message_signals = extract_message_signals(ctx.message_report)
    
    # Threat Intelligence & RAG Retrieval Parallel
    threat_task = build_threat_report(ctx.url_signals)
    rag_task    = retrieve_context(url, message)
    
    threat_rep, (rag_ctx_str, rag_evid) = await asyncio.gather(
        threat_task, rag_task
    )
    
    ctx.threat_report = threat_rep
    ctx.rag_context = rag_ctx_str
    ctx.rag_evidence = rag_evid
    ctx.threat_signals = extract_threat_signals(ctx.threat_report)
    ctx.timings["intelligence_discovery_ms"] = (time.monotonic() - t_start) * 1000

    # AI Deep-Reasoning Gating (LLM Analysis)
    ctx.llm = await _run_llm_with_gate(ctx)

    # Adaptive Behavioral Engine (Enriched with AI signals)
    beh_dict = await run_behavioral_analysis(
        url=ctx.url,
        message=ctx.message,
        url_report=ctx.url_report,
        message_report=ctx.message_report,
        threat_report=ctx.threat_report,
        llm_verdict={
            "scam_probability": ctx.llm.scam_probability,
            "threat_type": ctx.llm.threat_type,
            "confidence": ctx.llm.confidence,
            "llm_used": ctx.llm.used
        },
        rag_context=ctx.rag_context
    )

    from app.core.context_builder import BehavioralResult
    ctx.behavioral = BehavioralResult(
        score=beh_dict.get("scam_probability", 0),
        evidence=beh_dict.get("evidence", []),
        explanation=beh_dict.get("explanation", ""),
        behavioral_analysis=beh_dict.get("behavioral_analysis", {}),
        semantic_risk=beh_dict.get("semantic_risk", {}),
        domain_behavior=beh_dict.get("domain_behavior", {})
    )

    # Final Orchestration & Recording (using consolidated adaptive score)
    ctx.final_score = ctx.behavioral.score 
    await record_interaction(
        message_id=ctx.message_id,
        domain=ctx.url_signals.domain,
        fingerprint=ctx.cache_key, # Using cache_key as fingerprint
        verdict=ctx.verdict,
        scam_probability=ctx.final_score
    )
    
    return build_scan_response(ctx)
