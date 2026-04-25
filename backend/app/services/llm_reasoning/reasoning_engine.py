"""
reasoning_engine.py
────────────────────
Top-level orchestrator for the LLM Fraud Reasoning Engine.

Phase 4 Pipeline:
    build_context(url_report, message_report)
        ↓
    build_prompt(context, threat_report, rag_context)   ← Phase 4 enrichment
        ↓
    run_llm(prompt)           ← Groq primary → Gemini fallback
        ↓
    parse_verdict(raw_response)
        ↓
    format_explanation(verdict["explanation"])
        ↓
    return structured result dict

Accepts optional threat_report and rag_context for Threat Intelligence & RAG enrichment.
"""
import asyncio
from typing import Dict, Any, Optional
from app.logger import logger
from app.services.llm_reasoning.context_builder import build_context
from app.services.llm_reasoning.prompt_builder import build_prompt
from app.services.llm_reasoning.llm_client import run_llm
from app.services.llm_reasoning.verdict_parser import parse_verdict
from app.services.llm_reasoning.explanation_formatter import format_explanation
from app.services.llm_reasoning.groq_provider import groq_provider
from app.services.llm_reasoning.gemini_provider import gemini_provider

# ── Safe fallback returned when LLM is unavailable or fails ──────────────────
_FALLBACK_RESULT: Dict[str, Any] = {
    "llm_verdict": {
        "scam_probability": None,
        "threat_type": None,
        "confidence": None,
        "llm_used": False
    },
    "explanation": "LLM reasoning unavailable — rule-engine scores are used instead."
}


def _is_any_llm_available() -> bool:
    return groq_provider.is_available() or gemini_provider.is_available()


async def _run_reasoning_async(
    url_report: Dict[str, Any],
    message_report: Optional[Dict[str, Any]],
    message_text: Optional[str] = None,
    threat_report: Optional[Dict[str, Any]] = None,
    rag_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Asynchronous reasoning pipeline.
    """
    # 1. Build signal context block
    context = build_context(url_report, message_report, message_text=message_text)

    # 2. Build enriched prompt (with TI + RAG if available)
    prompt = build_prompt(context, threat_context=threat_report, rag_context=rag_context)

    # 3. LLM Inference: Groq (primary) → Gemini (fallback) - NOW ASYNC
    raw_response = await run_llm(prompt)

    # 4. Parse + validate JSON verdict with guardrails
    verdict = parse_verdict(raw_response)

    # 5. Format explanation string
    verdict["explanation"] = format_explanation(verdict.get("explanation", ""))

    return verdict


async def run_reasoning(
    url_report: Dict[str, Any],
    message_report: Optional[Dict[str, Any]] = None,
    message_text: Optional[str] = None,
    threat_report: Optional[Dict[str, Any]] = None,
    rag_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Async entry point for the LLM reasoning engine.
    """
    if not _is_any_llm_available():
        logger.warning("No LLM provider configured — skipping reasoning")
        return dict(_FALLBACK_RESULT)

    try:
        verdict = await _run_reasoning_async(
            url_report,
            message_report,
            message_text,
            threat_report,
            rag_context
        )

        explanation = verdict.pop("explanation", "")
        result = {
            "llm_verdict": verdict,
            "explanation": explanation
        }
        return result

    except Exception as e:
        logger.error(f"LLM reasoning engine error: {e}")
        return dict(_FALLBACK_RESULT)
