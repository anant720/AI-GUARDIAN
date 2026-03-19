"""
context_builder.py
──────────────────
Converts structured url_report + message_report dicts into a
plain-English context block that the LLM can reason over.
"""
from typing import Dict, Any, Optional
from app.logger import logger


def build_context(
    url_report: Dict[str, Any],
    message_report: Optional[Dict[str, Any]] = None,
    message_text: Optional[str] = None,
) -> str:
    """
    Build a human-readable LLM context string from intelligence reports.

    Args:
        url_report:     Output of build_intelligence_report()
        message_report: Output of analyze_message() — optional

    Returns:
        Multi-line plain-English context string
    """
    try:
        lines = ["=== SCAN SIGNALS ===\n"]

        # ── URL Section ───────────────────────────────────────────────────────
        lines.append("[ URL Intelligence ]")
        lines.append(f"- Scanned URL      : {url_report.get('url', 'N/A')}")
        lines.append(f"- Final URL        : {url_report.get('final_url', 'N/A')}")
        lines.append(f"- Rule Risk Score  : {url_report.get('risk_score', 'N/A')} / 100")

        signals = url_report.get("signals", {})
        lines.append(f"- SSL Valid        : {signals.get('ssl_valid', 'Unknown')}")
        lines.append(f"- Redirect Count   : {signals.get('redirect_count', 0)}")
        lines.append(f"- Credential Form  : {signals.get('credential_form_detected', False)}")
        lines.append(f"- Brand Impersonated: {signals.get('brand_impersonation') or 'None detected'}")

        keywords = signals.get("suspicious_keywords", [])
        if keywords:
            lines.append(f"- Suspicious Keywords: {', '.join(keywords)}")

        domain_age = signals.get("domain_age_days")
        if domain_age is not None:
            lines.append(f"- Domain Age (days) : {domain_age}")
        else:
            lines.append("- Domain Age        : Unknown (WHOIS unavailable)")

        # ── Message Section ───────────────────────────────────────────────────
        if message_report and "message_analysis" in message_report:
            lines.append("\n[ Message Intelligence ]")
            analysis = message_report["message_analysis"]
            lines.append(f"- Intent           : {analysis.get('intent', 'unknown')}")
            lines.append(f"- Urgency Score    : {analysis.get('urgency_score', 0.0):.2f}")
            lines.append(f"- Credential Request: {analysis.get('credential_request_detected', False)}")
            lines.append(f"- Brand Impersonated: {analysis.get('impersonated_brand') or 'None'}")
            lines.append(f"- Language         : {analysis.get('language') or 'Unknown'}")
            lines.append(f"- Scam Probability : {analysis.get('scam_probability', 0.0):.2f}")

            score_details = analysis.get("score_details", {})
            if score_details:
                lines.append(f"- Message Risk Score: {score_details.get('message_risk_score', 0)} / 100")
                lines.append(f"- Template Similarity: {score_details.get('template_similarity', 0.0):.2f}")
                lines.append(f"- URL/Brand Mismatch: {score_details.get('mismatch_detected', False)}")
        else:
            lines.append("\n[ Message Intelligence ]\n- No message provided")

        # ── Raw Message Excerpt (for reasoning) ───────────────────────────────
        # The LLM should reason over the actual text (not only derived signals),
        # especially for credential-harvesting cues (OTP/CVV/SSN, etc).
        if message_text:
            excerpt = " ".join(str(message_text).split())
            if len(excerpt) > 700:
                excerpt = excerpt[:700] + "…"
            lines.append("\n[ Message Body Excerpt ]")
            lines.append(excerpt)

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Context builder error: {e}")
        return "=== SCAN SIGNALS ===\n[Error building context]"
