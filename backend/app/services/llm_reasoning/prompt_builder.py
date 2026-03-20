"""
prompt_builder.py
─────────────────
Builds the full cybersecurity reasoning prompt for the LLM.

Now supports three optional context blocks:
  1. [SCAN SIGNALS]     - App signals (Phase 1 & 2)
    - Threat Intelligence & RAG Retrieval
    - Adaptive Behavioral Index (Unified Score)
  2. [THREAT INTELLIGENCE]   — real-world TI from Phase 4
  3. [KNOWLEDGE BASE]        — RAG-retrieved phishing patterns
"""
from typing import Optional


_SYSTEM_PERSONA = """You are an elite cybersecurity fraud detection AI with expertise in:
- Phishing and social engineering attack patterns
- URL and domain analysis
- Financial scam and credential theft detection
- Brand impersonation identification
- Real-world threat intelligence

Your task: Analyse the provided signals and return a structured JSON verdict.

RULES:
1. ALWAYS respond with ONLY valid JSON — no markdown, no prose outside the JSON.
2. ALL fields are mandatory.
3. scam_probability: integer 0-100 (100 = certain scam)
4. threat_type: one of [phishing, credential_phishing, financial_fraud, banking_fraud,
   account_takeover, malware_distribution, ransomware, tech_support_scam,
   delivery_scam, government_impersonation, business_email_compromise, safe]
5. confidence: float 0.0-1.0 (even for "safe" verdicts, provide your degree of certainty)
6. explanation: one clear sentence explaining the primary threat or why it is safe

INTERPRETATION GUIDANCE:
- If the message asks for OTP, CVV, debit/credit card details, password, PIN, or "verify KYC/login" under urgency,
  treat it as credential phishing/account takeover even if threat intel looks clean/unknown.
- **PRIORITIZE URL OVER TONE**: A professional, helpful, or boring tone is a common "Soft Phish" tactic. If the URL impersonates a major brand (e.g., Adobe, Microsoft, HDFC) but is on a different root domain, it is ALMOST ALWAYS phishing, regardless of how safe the text sounds.
- A "clean" reputation is NOT proof of safety for newly registered or unreachable domains.

EXAMPLE RESPONSE:
{
  "scam_probability": 94,
  "threat_type": "credential_phishing",
  "confidence": 0.91,
  "explanation": "The URL impersonates PayPal and the message creates urgency to steal login credentials.",
  "llm_used": true
}"""


def _format_threat_context(threat_report: Optional[dict]) -> str:
    """Format threat intelligence data for prompt injection."""
    if not threat_report:
        return ""

    lines = ["\n[THREAT INTELLIGENCE — Real-World Data]"]
    lines.append(f"- Domain reputation   : {threat_report.get('domain_reputation', 'unknown').upper()}")
    lines.append(f"- IP risk score       : {threat_report.get('ip_risk_score', 0)}/100")
    lines.append(f"- Blacklist hits      : {threat_report.get('ip_blacklist_count', 0)}")
    lines.append(f"- Phishing DB match   : {'YES ✓' if threat_report.get('phishing_match') else 'No'}")
    if threat_report.get('phishing_confidence', 0) > 0:
        lines.append(f"  Confidence          : {threat_report.get('phishing_confidence', 0):.0%}")
    lines.append(f"- Malware detected    : {'YES ✓' if threat_report.get('malware_detected') else 'No'}")
    if threat_report.get('malware_type'):
        lines.append(f"  Malware type        : {threat_report.get('malware_type')}")
    lines.append(f"- Domain age          : {threat_report.get('domain_age_days', 'unknown')} days "
                 f"({threat_report.get('domain_age_flag', '')})")
    ti_score = threat_report.get('threat_score', 0)
    lines.append(f"- TI threat score     : {ti_score}/100")

    signals = threat_report.get('domain_risk_signals', [])
    if signals:
        lines.append(f"- Risk signals        : {', '.join(signals[:5])}")

    return "\n".join(lines)


def _format_rag_context(rag_context: Optional[str]) -> str:
    """Add RAG context section to prompt if available."""
    if not rag_context or rag_context.strip() == "No relevant historical knowledge found for this scan.":
        return ""
    return f"\n[KNOWLEDGE BASE — Historical Phishing Patterns]\n{rag_context}"


def build_prompt(
    context: str,
    threat_context: Optional[dict] = None,
    rag_context: Optional[str] = None
) -> str:
    """
    Construct the full LLM reasoning prompt.

    Args:
        context: URL + message signals block (from context_builder)
        threat_context: ThreatIntelligenceReport dict (from Phase 4 TI engine)
        rag_context: RAG context string (from Phase 4 RAG engine)

    Returns:
        Complete prompt string ready for LLM inference.
    """
    prompt_parts = [
        _SYSTEM_PERSONA,
        "\n\n[SCAN SIGNALS]",
        context
    ]

    ti_block = _format_threat_context(threat_context)
    if ti_block:
        prompt_parts.append(ti_block)

    rag_block = _format_rag_context(rag_context)
    if rag_block:
        prompt_parts.append(rag_block)

    prompt_parts.append(
        "\n\nBased on ALL the signals above, respond ONLY with a JSON verdict:"
    )

    return "\n".join(prompt_parts)
