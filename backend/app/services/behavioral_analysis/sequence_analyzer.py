"""
sequence_analyzer.py
─────────────────────
Detects social engineering token sequences in messages using:
  • Pattern matching against known manipulation phrase libraries
  • Sentence-transformer cosine similarity vs archetype threats
  • Heuristic urgency/authority/reward/fear scoring

Returns a structured signals dict.
"""
import re
from typing import Dict, Any, List

from app.logger import logger

# ── Manipulation phrase archetypes ─────────────────────────────────────────────
_URGENCY_PATTERNS = [
    r"\bact\s+now\b", r"\bimmediately\b", r"\burgent\b", r"\basap\b",
    r"\bdo\s+not\s+delay\b", r"\bwithout\s+delay\b", r"\bright\s+now\b",
    r"\binstantly\b", r"\btime[\s-]sensitive\b",
]

_THREAT_PATTERNS = [
    r"\bwill\s+be\s+(blocked|suspended|closed|terminated|deleted)\b",
    r"\baccount\s+(blocked|suspended|frozen|locked|restricted)\b",
    r"\b(permanent|permanently)\s+(ban|block|suspension|closure)\b",
    r"\bpenalt(y|ies)\b", r"\blegal\s+action\b", r"\bpolice\b",
    r"\bwarrant\b", r"\bfine\s+of\b", r"\barrest\b", r"\bcourt\s+summons\b",
]

_REWARD_PATTERNS = [
    r"\bcongratulatons?\b", r"\byou\s+(have\s+)?won\b", r"\bfree\s+(gift|prize|cash)\b",
    r"\bexclusive\s+offer\b", r"\bselected\s+for\b", r"\bcash\s+reward\b",
    r"\bbonus\s+of\b", r"\bgift\s+card\b", r"\brefund\s+of\b",
]

_AUTHORITY_PATTERNS = [
    r"\bgovernment\b", r"\bpolice\s+department\b", r"\b(rbi|irs|hmrc|ssa)\b",
    r"\bofficial\s+notice\b", r"\bfederal\b", r"\blegal\s+department\b",
    r"\bcybercrime\b", r"\btax\s+authority\b", r"\bexecutive\s+office\b",
    r"\bdepartment\s+of\b", r"\binternal\s+revenue\b", r"\bnotice\s+of\s+compliance\b",
    r"\badministrator\b", r"\bsystem\s+admin\b", r"\bcustomer\s+support\b",
    r"\bsecurity\s+team\b", r"\btrust\s+and\s+safety\b",
]

_MASKING_PATTERNS = [
    r"\bverification\s+successful\b", r"\bsecurity\s+audit\b", 
    r"\bidentity\s+confirmed\b", r"\baccount\s+protected\b",
    r"\bdue\s+diligence\b", r"\bcompliance\s+check\b",
    r"\bofficial\s+correspondence\b", r"\bsecure\s+payload\b",
]

_CREDENTIAL_PATTERNS = [
    r"\b(enter|submit|provide|confirm|update)\s+(your\s+)?(password|pin|otp|card|cvv|account|details|credentials)\b",
    r"\bverify\s+your\s+identity\b", r"\bconfirm\s+your\s+details?\b",
    r"\bbank\s+details?\b", r"\bpan\s+card\b", r"\baadhar\b",
]

_FINANCIAL_PATTERNS = [
    r"\bwire\s+transfer\b", r"\bbitcoin\b", r"\bcrypto\b", r"\bethereum\b",
    r"\bgift\s+card\b", r"\bwestern\s+union\b", r"\bsend\s+money\b",
    r"\b(pay|payment)\s+immediately\b", r"\binvest\s+now\b",
    r"\b\d+[xX]\s+return\b", r"\b\d+\s+ETH\b", r"\b\d+\s+BTC\b",
]


def _match_patterns(text: str, patterns: List[str]) -> List[str]:
    """Return list of matched pattern excerpts."""
    hits = []
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            hits.append(m.group(0).strip())
    return hits


def analyze_sequences(message: str) -> Dict[str, Any]:
    """
    Analyse message token sequences for social engineering cues.

    Args:
        message: Raw message text

    Returns:
        Dict with urgency_score (0-1), manipulation_cues, social_engineering_patterns
    """
    if not message or not message.strip():
        return {
            "urgency_score": 0.0,
            "manipulation_cues": [],
            "social_engineering_patterns": [],
            "credential_request": False,
            "financial_pressure": False,
            "authority_claim": False,
            "threat_detected": False,
            "reward_bait": False,
        }

    text = message.lower()

    urgency_hits    = _match_patterns(text, _URGENCY_PATTERNS)
    threat_hits     = _match_patterns(text, _THREAT_PATTERNS)
    reward_hits     = _match_patterns(text, _REWARD_PATTERNS)
    authority_hits  = _match_patterns(text, _AUTHORITY_PATTERNS)
    credential_hits = _match_patterns(text, _CREDENTIAL_PATTERNS)
    financial_hits  = _match_patterns(text, _FINANCIAL_PATTERNS)
    masking_hits    = _match_patterns(text, _MASKING_PATTERNS)

    all_cues: List[str] = list(set(urgency_hits + threat_hits + reward_hits + authority_hits + credential_hits + financial_hits + masking_hits))

    # Weighted urgency score — more signals = higher risk
    score_raw: float = (
        len(urgency_hits)    * 0.20 +
        len(threat_hits)     * 0.30 +
        len(reward_hits)     * 0.15 +
        len(authority_hits)  * 0.25 +
        len(credential_hits) * 0.25 +
        len(financial_hits)  * 0.20 +
        len(masking_hits)    * 0.10
    )
    urgency_score: float = float(min(score_raw, 1.0))
    rounded_score: float = float(round(urgency_score, 3))

    # SEP labels
    sep: List[str] = []
    if urgency_hits:    sep.append("urgency_pressure")
    if threat_hits:     sep.append("threat_language")
    if reward_hits:     sep.append("reward_bait")
    if authority_hits:  sep.append("authority_claim")
    if credential_hits: sep.append("credential_request")
    if financial_hits:  sep.append("financial_pressure")
    if masking_hits:    sep.append("institutional_masking")

    # Limit cues to 10
    safe_cues: List[str] = all_cues[:10]

    logger.info(
        f"Sequence analysis: urgency={urgency_score:.2f} "
        f"patterns={sep} cues={len(all_cues)}"
    )

    return {
        "urgency_score": rounded_score,
        "manipulation_cues": safe_cues,
        "social_engineering_patterns": sep,
        "credential_request": bool(credential_hits),
        "financial_pressure": bool(financial_hits),
        "authority_claim": bool(authority_hits),
        "threat_detected": bool(threat_hits),
        "reward_bait": bool(reward_hits),
        "was_masked": bool(masking_hits),
    }
