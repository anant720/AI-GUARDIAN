"""
threat_feed_aggregator.py
──────────────────────────
Runs all 5 threat intelligence checkers concurrently (via asyncio.to_thread)
and aggregates results into a single threat_signals dict with a weighted score.

Weights:
  domain_reputation  → 35 pts max
  ip_reputation      → 20 pts max
  phishing_match     → 30 pts max
  malware_detected   → 25 pts max
  domain_age         → 20 pts max
  Total possible     → 130 pts → normalised to 0-100
"""
import asyncio
from typing import Dict, Any, Optional
from app.logger import logger
from app.services.threat_intelligence.domain_reputation_checker import check_domain_reputation
from app.services.threat_intelligence.ip_reputation_checker import check_ip_reputation
from app.services.threat_intelligence.phishing_database_checker import check_phishing_database
from app.services.threat_intelligence.malware_url_checker import check_malware_url
from app.services.threat_intelligence.domain_age_analyzer import analyze_domain_age


def _compute_threat_score(
    domain_rep: Dict,
    ip_rep: Dict,
    phishing: Dict,
    malware: Dict,
    age: Dict
) -> int:
    """Compute weighted threat intelligence score (0-100)."""
    score = 0

    # Domain reputation (max 35)
    rep = domain_rep.get("reputation", "clean")
    score += {"malicious": 35, "suspicious": 20, "clean": 0}.get(rep, 0)

    # IP reputation (max 20)
    ip_risk = ip_rep.get("risk_score", 0)
    score += int(20 * min(ip_risk, 100) / 100)

    # Phishing match (max 30)
    if phishing.get("phishing_match"):
        score += int(30 * phishing.get("confidence", 0.9))

    # Malware detected (max 25)
    if malware.get("malware_detected"):
        score += 25

    # Domain age (max 20)
    age_days = age.get("domain_age_days")
    risk_flag = age.get("risk_flag", "")
    if age_days is not None:
        if age_days < 7:
            score += 20
        elif age_days < 30:
            score += 15
        elif age_days < 90:
            score += 8
    elif "failed" in risk_flag or "no_date" in risk_flag:
        score += 5  # slight penalty for evasion

    return min(int(score * 100 / 130), 100)  # normalise to 0-100


async def aggregate_threat_intelligence(
    url: str,
    domain: str
) -> Dict[str, Any]:
    """
    Run all TI checks concurrently and aggregate results.

    Returns:
        Combined threat signals dict with threat_score.
    """
    logger.info(f"Running threat intelligence checks for domain: {domain}")

    # Run all blocking IO checks in thread pool concurrently with strict 2.0s timeout
    try:
        (
            domain_rep,
            ip_rep,
            phishing,
            malware,
            age
        ) = await asyncio.wait_for(
            asyncio.gather(
                asyncio.to_thread(check_domain_reputation, domain),
                asyncio.to_thread(check_ip_reputation, domain),
                asyncio.to_thread(check_phishing_database, url, domain),
                asyncio.to_thread(check_malware_url, url),
                asyncio.to_thread(analyze_domain_age, domain),
            ),
            timeout=2.0
        )
    except asyncio.TimeoutError:
        logger.warning(f"Threat intelligence checks timed out for {domain} (limit: 2.0s)")
        # Create a hybrid report with whatever we have (mostly defaults)
        # We can't easily know which one failed, so we use defaults for all if the group timed out
        domain_rep = {"reputation": "unknown"}
        ip_rep = {"risk_score": 0}
        phishing = {"phishing_match": False}
        malware = {"malware_detected": False}
        age = {"risk_flag": "timeout", "domain_age_days": None}
    except Exception as e:
        logger.error(f"Unexpected error in threat intelligence aggregation: {e}")
        # Fallback to defaults
        domain_rep, ip_rep, phishing, malware, age = {}, {}, {}, {}, {}

    threat_score = _compute_threat_score(domain_rep, ip_rep, phishing, malware, age)

    result = {
        # Domain reputation
        "domain_reputation": domain_rep.get("reputation", "unknown"),
        "domain_confidence": domain_rep.get("confidence", 0.0),
        "domain_risk_signals": domain_rep.get("risk_signals", []),
        # IP reputation
        "ip": ip_rep.get("ip"),
        "ip_risk_score": ip_rep.get("risk_score", 0),
        "ip_blacklist_count": ip_rep.get("blacklist_count", 0),
        "ip_country": ip_rep.get("country", "unknown"),
        # Phishing database
        "phishing_match": phishing.get("phishing_match", False),
        "phishing_database": phishing.get("database", "unknown"),
        "phishing_confidence": phishing.get("confidence", 0.0),
        # Malware
        "malware_detected": malware.get("malware_detected", False),
        "malware_type": malware.get("malware_type"),
        "malware_indicators": malware.get("indicators", []),
        # Domain age
        "domain_age_days": age.get("domain_age_days"),
        "domain_age_flag": age.get("risk_flag", "unknown"),
        "registrar": age.get("registrar", "unknown"),
        # Aggregated score
        "threat_score": threat_score
    }

    logger.info(
        f"Threat intelligence complete — score={threat_score} "
        f"rep={domain_rep.get('reputation')} "
        f"phishing={phishing.get('phishing_match')} "
        f"malware={malware.get('malware_detected')}"
    )
    return result
