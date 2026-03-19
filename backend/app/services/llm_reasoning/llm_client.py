"""
llm_client.py
─────────────
LLM Orchestrator: Groq (primary) → Gemini (fallback)

Pipeline:
  1. Try Groq with round-robin key rotation
  2. On any Groq failure, try Gemini with key cycling
  3. Raise only if both providers fail

Logs provider used, fallback events, and latency metrics.
"""
import time
from app.logger import logger
from app.services.llm_reasoning.groq_provider import groq_provider, call_groq
from app.services.llm_reasoning.gemini_provider import gemini_provider, call_gemini


def run_llm(prompt: str) -> str:
    """
    Run LLM inference with Groq as primary and Gemini as fallback.

    Args:
        prompt: Full formatted prompt string

    Returns:
        Raw LLM response text (JSON string expected)

    Raises:
        RuntimeError: If both Groq and Gemini fail
    """
    # ── Groq (primary) ────────────────────────────────────────────────────────
    if groq_provider.is_available():
        try:
            logger.info("LLM inference started — provider: Groq")
            t_start = time.monotonic()
            response = call_groq(prompt)
            if not isinstance(response, str):
                logger.error(f"LLM_CLIENT: Groq returned {type(response)} instead of string!")
            latency = time.monotonic() - t_start
            logger.info(f"Groq inference complete — latency: {latency:.2f}s")
            return response
        except Exception as e:
            logger.warning(f"Groq failed, triggering Gemini fallback: {e}")
    else:
        logger.info("Groq not configured — skipping to Gemini fallback")

    # ── Gemini (fallback) ─────────────────────────────────────────────────────
    if gemini_provider.is_available():
        try:
            logger.info("LLM inference fallback — provider: Gemini")
            t_start = time.monotonic()
            response = call_gemini(prompt)
            latency = time.monotonic() - t_start
            logger.info(f"Gemini inference complete — latency: {latency:.2f}s")
            return response
        except Exception as e:
            logger.error(f"Gemini also failed: {e}")
            raise RuntimeError(f"Both Groq and Gemini failed. Gemini error: {e}")
    else:
        logger.warning("Gemini not configured — no fallback available")

    raise RuntimeError("No LLM provider available (Groq and Gemini both unconfigured)")
