"""
app/core/context_builder.py
────────────────────────────
Defines and builds the central ScanContext dataclass.

This is the SINGLE TRUTH OBJECT passed through the entire pipeline.
Every signal is computed ONCE and stored here — no duplicate computation.
"""
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ThreatSignals:
    phishing_match: bool = False
    malware_detected: bool = False
    domain_reputation: str = "unknown"
    ip_risk_score: int = 0
    ip_blacklist_count: int = 0
    phishing_confidence: float = 0.0
    domain_age_days: Optional[int] = None
    domain_age_flag: str = ""
    threat_score: int = 0
    domain_risk_signals: List[str] = field(default_factory=list)


@dataclass
class URLSignals:
    risk_score: int = 0
    suspicious_keywords: List[str] = field(default_factory=list)
    ssl_valid: bool = False
    brand_impersonation: Optional[str] = None
    redirect_count: int = 0
    credential_form_detected: bool = False
    domain: str = ""
    tld: str = ""
    normalized_url: str = ""
    final_url: str = ""


@dataclass
class MessageSignals:
    message_risk_score: int = 0
    urgency_score: int = 0
    financial_request: bool = False
    credential_request: bool = False
    intent: str = "unknown"
    language: str = "en"
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehavioralResult:
    score: int = 0
    evidence: List[str] = field(default_factory=list)
    explanation: str = ""
    behavioral_analysis: Dict[str, Any] = field(default_factory=dict)
    semantic_risk: Dict[str, Any] = field(default_factory=dict)
    domain_behavior: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResult:
    used: bool = False
    scam_probability: Optional[int] = None
    threat_type: Optional[str] = None
    confidence: float = 0.0
    explanation: str = ""
    cached: bool = False
    skipped_reason: str = ""


@dataclass
class ScanContext:
    # Inputs
    url: str = ""
    message: str = ""
    message_id: str = ""

    # Phase results (populated during pipeline)
    url_report: Dict[str, Any] = field(default_factory=dict)
    message_report: Optional[Dict[str, Any]] = None
    threat_report: Dict[str, Any] = field(default_factory=dict)
    rag_context: str = ""
    rag_evidence: List[str] = field(default_factory=list)

    # Extracted signals (clean, typed)
    url_signals: URLSignals = field(default_factory=URLSignals)
    message_signals: MessageSignals = field(default_factory=MessageSignals)
    threat_signals: ThreatSignals = field(default_factory=ThreatSignals)

    # Phase 5 Output
    behavioral: BehavioralResult = field(default_factory=BehavioralResult)

    # LLM Output
    llm: LLMResult = field(default_factory=LLMResult)

    # Final Output
    combined_rule_score: int = 0
    final_score: int = 0
    verdict: str = "SAFE"

    # Profiling: per-phase elapsed times in ms
    timings: Dict[str, float] = field(default_factory=dict)

    # Cached HTML for behavioral analysis
    html: str = ""
    claimed_brand: str = ""

    # Cache key for LLM deduplication
    cache_key: str = ""


def build_context(url: str, message: str, message_id: str) -> ScanContext:
    """
    Initialise a fresh ScanContext for a new scan request.
    Cache key is computed from normalized domain + truncated message.
    """
    # Normalise domain for cache key
    try:
        from urllib.parse import urlparse
        if not url:
            domain = "no-url"
        else:
            domain = urlparse(url).hostname or url
    except Exception:
        domain = url or "unknown"

    domain_str = str(domain or "no-url").lower()
    msg_snippet = (message or "")[:200].strip().lower()
    
    raw = f"{domain_str}|{msg_snippet}"
    cache_key = hashlib.sha256(raw.encode()).hexdigest()[:16]

    return ScanContext(
        url=url,
        message=message or "",
        message_id=message_id,
        cache_key=cache_key,
    )


def extract_url_signals(url_report: Dict[str, Any]) -> URLSignals:
    """Extract typed URL signals from the raw URL report."""
    sigs = url_report.get("signals", {})
    struct = url_report.get("detailed_report", {}).get("url_structural", {})
    return URLSignals(
        risk_score=url_report.get("risk_score", 0),
        suspicious_keywords=sigs.get("suspicious_keywords", []),
        ssl_valid=sigs.get("ssl_valid", False),
        brand_impersonation=sigs.get("brand_impersonation"),
        redirect_count=sigs.get("redirect_count", 0),
        credential_form_detected=sigs.get("credential_form_detected", False),
        domain=struct.get("domain", ""),
        tld=struct.get("tld", ""),
        normalized_url=url_report.get("normalized_url", ""),
        final_url=url_report.get("final_url", ""),
    )


def extract_threat_signals(threat_report: Dict[str, Any]) -> ThreatSignals:
    """Extract typed threat signals from the raw threat report."""
    return ThreatSignals(
        phishing_match=threat_report.get("phishing_match", False),
        malware_detected=threat_report.get("malware_detected", False),
        domain_reputation=threat_report.get("domain_reputation", "unknown"),
        ip_risk_score=threat_report.get("ip_risk_score", 0),
        ip_blacklist_count=threat_report.get("ip_blacklist_count", 0),
        phishing_confidence=threat_report.get("phishing_confidence", 0.0),
        domain_age_days=threat_report.get("domain_age_days"),
        domain_age_flag=threat_report.get("domain_age_flag", ""),
        threat_score=threat_report.get("threat_score", 0),
        domain_risk_signals=threat_report.get("domain_risk_signals", []),
    )


def extract_message_signals(message_report: Optional[Dict[str, Any]]) -> MessageSignals:
    """Extract typed message signals from the raw message report."""
    if not message_report or "error" in message_report:
        return MessageSignals()
    analysis = message_report.get("message_analysis", {})
    score_details = analysis.get("score_details", {})
    intents = analysis.get("intent_analysis", {})
    return MessageSignals(
        message_risk_score=score_details.get("message_risk_score", 0),
        urgency_score=score_details.get("urgency_score", 0),
        financial_request=analysis.get("financial_scam", {}).get("financial_pressure", False),
        credential_request=analysis.get("credential_request", {}).get("credential_request_detected", False),
        intent=intents.get("intent", "unknown"),
        language=analysis.get("language", "en"),
        raw=message_report or {},
    )
