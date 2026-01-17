"""
Simplified AI Guardian Detection Module
Enhanced version that provides meaningful risk scores
"""

import re
import os
import logging
from urllib.parse import urlparse
from . import rules
from . import utils
from datetime import datetime
import config
from typing import List, Tuple

# Optional imports with fallbacks
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests not available, link analysis will be limited")

try:
    import joblib
    import sklearn
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("Warning: ML libraries not available, using rule-based analysis only")

try:
    import socket, ipaddress, ssl
    NETWORK_AVAILABLE = True
except ImportError:
    NETWORK_AVAILABLE = False
    print("Warning: Network libraries not available, link analysis disabled")

LEVEL_SAFE = "Safe"
LEVEL_SUSPICIOUS = "Suspicious"
LEVEL_DANGEROUS = "Dangerous"

# Load ML models if available
VECTORIZER_PATH = config.MODEL_CONFIG['VECTORIZER_PATH']
MODEL_PATH = config.MODEL_CONFIG['MODEL_PATH']

ML_MODEL = None
VECTORIZER = None

if ML_AVAILABLE:
    try:
        if os.path.exists(MODEL_PATH) and os.path.exists(VECTORIZER_PATH):
            ML_MODEL = joblib.load(MODEL_PATH)
            VECTORIZER = joblib.load(VECTORIZER_PATH)
            logging.info("Successfully loaded ML model and vectorizer.")
        else:
            logging.warning("ML model or vectorizer not found. Detection will proceed with rule-based analysis only.")
    except Exception as e:
        logging.error(f"Error loading ML model: {e}. Detection will proceed without ML analysis.")
        ML_MODEL, VECTORIZER = None, None
else:
    logging.info("ML libraries not available, using rule-based analysis only.")

def analyse_message(text: str) -> dict:
    """
    Enhanced risk assessment that provides meaningful scores.
    Combines keyword analysis, semantic patterns, and behavioral signals.
    """
    logging.info(f"Starting enhanced analysis for message: {text[:100]}...")
    risk_score = 0
    reasons = []

    # Extract links first
    links = utils.extract_links(text)

    # Check for trusted senders (highest priority override)
    override_level, override_reason = get_contextual_override(text, links)
    if override_level == "Safe":
        return {
            "level": LEVEL_SAFE,
            "score": 0,
            "reasons": [override_reason],
            "links": links
        }

    # Clean text for analysis
    clean_text = text.lower()
    text_without_links = clean_text
    for link in links:
        text_without_links = text_without_links.replace(link.lower(), " ")

    # ========================================================================
    # BASIC KEYWORD ANALYSIS (Enhanced)
    # ========================================================================
    for keyword, weight in rules.SCAM_KEYWORDS.items():
        if keyword in text_without_links:
            risk_score += weight
            reasons.append(f"Detected suspicious keyword: '{keyword}'")

    # ========================================================================
    # SEMANTIC PATTERN ANALYSIS (New)
    # ========================================================================
    # Urgency patterns
    urgency_words = ['urgent', 'immediate', 'immediately', 'asap', 'now', 'hurry', 'quick', 'fast']
    urgency_count = sum(1 for word in urgency_words if word in text_without_links)
    if urgency_count > 0:
        risk_score += urgency_count * 2
        reasons.append(f"Urgency pressure detected ({urgency_count} indicators)")

    # Authority imitation
    authority_phrases = ['official', 'government', 'bank', 'security', 'verify', 'account suspended']
    authority_count = sum(1 for phrase in authority_phrases if phrase in text_without_links)
    if authority_count > 0:
        risk_score += authority_count * 3
        reasons.append(f"Authority imitation detected ({authority_count} indicators)")

    # Information requests (high risk)
    info_request_words = ['send your', 'provide your', 'share your', 'enter your', 'confirm your']
    info_request_count = sum(1 for phrase in info_request_words if phrase in text_without_links)
    if info_request_count > 0:
        risk_score += info_request_count * 4
        reasons.append(f"Personal information request detected ({info_request_count} indicators)")

    # ========================================================================
    # BEHAVIORAL PATTERN ANALYSIS (New)
    # ========================================================================
    # Excessive punctuation
    exclamation_count = text.count('!')
    if exclamation_count > 3:
        risk_score += 1
        reasons.append(f"Excessive punctuation ({exclamation_count} exclamation marks)")

    # Money amounts
    money_pattern = r'[$₹£€]\s*\d+'
    money_matches = len(re.findall(money_pattern, text))
    if money_matches > 0:
        risk_score += money_matches * 2
        reasons.append(f"Money amounts mentioned ({money_matches} instances)")

    # ========================================================================
    # REGEX PATTERN ANALYSIS
    # ========================================================================
    high_threat_pattern_found = False
    for pattern_name, (regex, weight) in rules.WEIGHTED_SUSPICIOUS_PATTERNS.items():
        if "URL" not in pattern_name and "DOMAIN" not in pattern_name:
            if re.search(regex, text_without_links, re.IGNORECASE):
                risk_score += weight
                reasons.append(rules.FRIENDLY_REASONS.get(pattern_name, f"Detected pattern: {pattern_name}"))
                if pattern_name == "PERSONAL_INFO_REQUEST":
                    high_threat_pattern_found = True

    # ========================================================================
    # LINK ANALYSIS
    # ========================================================================
    if links:
        reasons.append(f"Message contains {len(links)} link(s)")
        for link in links:
            # Domain pattern checks
            domain_patterns_to_check = ["SUSPICIOUS_DOMAIN_TLD", "SHORTENED_URL"]
            for pattern_name in domain_patterns_to_check:
                regex, weight = rules.WEIGHTED_SUSPICIOUS_PATTERNS[pattern_name]
                if re.search(regex, link, re.IGNORECASE):
                    risk_score += weight
                    reasons.append(rules.FRIENDLY_REASONS.get(pattern_name, f"Link pattern: {pattern_name}"))

            # Advanced link analysis (if network libraries available)
            if NETWORK_AVAILABLE:
                link_score, link_reasons = analyse_link_advanced(link)
                if link_score > 0:
                    risk_score += link_score
                    reasons.extend(link_reasons)

    # ========================================================================
    # SAFE KEYWORD ADJUSTMENT
    # ========================================================================
    if not high_threat_pattern_found:
        for keyword, weight in rules.SAFE_KEYWORDS.items():
            if keyword in text_without_links:
                risk_score += weight
                reasons.append(f"Safe keyword detected: '{keyword}'")

    # ========================================================================
    # ML MODEL ANALYSIS (if available)
    # ========================================================================
    if ML_AVAILABLE and ML_MODEL and VECTORIZER and risk_score > 0:  # Only run ML if there are already signals
        try:
            vectorized_text = VECTORIZER.transform([text_without_links])
            scam_probability = ML_MODEL.predict_proba(vectorized_text)[0][1]
            if scam_probability > 0.8:
                risk_score += 6
                reasons.append("ML model confirms high scam probability")
            elif scam_probability > 0.6:
                risk_score += 3
                reasons.append("ML model suggests suspicious content")
        except Exception as e:
            logging.warning(f"ML model prediction failed: {e}")

    # ========================================================================
    # RISK LEVEL DETERMINATION
    # ========================================================================
    risk_score = max(0, int(risk_score))  # Ensure non-negative

    if risk_score >= config.RISK_THRESHOLDS['DANGEROUS']:
        risk_level = LEVEL_DANGEROUS
    elif risk_score >= config.RISK_THRESHOLDS['SUSPICIOUS']:
        risk_level = LEVEL_SUSPICIOUS
    else:
        risk_level = LEVEL_SAFE

    logging.info(f"Analysis complete. Level: {risk_level}, Score: {risk_score}, Reasons: {len(reasons)}")

    # Ensure we always have at least one reason
    if not reasons:
        if risk_score > 0:
            reasons.append("Multiple risk factors detected")
        else:
            reasons.append("No significant risk factors detected")

    return {
        "level": risk_level,
        "score": risk_score,
        "reasons": reasons,
        "links": links
    }


def get_contextual_override(text: str, links: List[str]) -> tuple:
    """
    Check for trusted sender patterns that override risk analysis.
    Returns (override_level, reason) or (None, None)
    """
    # Check for official sender IDs
    clean_text = text.lower()
    for sender_id in rules.OFFICIAL_SENDER_IDS:
        if sender_id.lower() in clean_text:
            return "Safe", f"Message from verified official sender: {sender_id}"

    # Check for official domain extensions
    for link in links:
        domain = urlparse(link).netloc
        for official_ext in rules.OFFICIAL_DOMAIN_EXTENSIONS:
            if domain.endswith(official_ext):
                return "Safe", f"Contains official domain: {domain}"

    return None, None


def analyse_link_advanced(link: str) -> tuple:
    """
    Advanced link analysis for security threats.
    Returns (risk_score, reasons_list)
    """
    risk_score = 0
    reasons = []

    if not NETWORK_AVAILABLE:
        return 0, ["Link analysis unavailable - network libraries not loaded"]

    try:
        domain = urlparse(link).netloc

        # Check against malicious domains
        if domain in rules.MALICIOUS_DOMAINS:
            risk_score += 15
            reasons.append(f"Domain '{domain}' is in known malicious list")

        # Check for IP addresses
        try:
            ipaddress.ip_address(domain)
            risk_score += 8
            reasons.append("URL contains IP address instead of domain name")
        except ValueError:
            pass

        # Check for suspicious TLDs
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.gq']
        for tld in suspicious_tlds:
            if domain.endswith(tld):
                risk_score += 4
                reasons.append(f"Suspicious top-level domain: {tld}")
                break

    except Exception as e:
        reasons.append(f"Error analyzing link: {e}")

    return risk_score, reasons