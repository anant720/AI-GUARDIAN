from typing import Dict, Any

def calculate_risk_score(signals: Dict[str, Any]) -> int:
    """Aggregate signals into a risk score (0-100)."""
    score = 0
    
    # 1. Structural Signals
    if signals.get("url_structural", {}).get("is_suspicious_tld"):
        score += 10
    if signals.get("url_structural", {}).get("subdomain_count", 0) > 2:
        score += 10
    if signals.get("url_structural", {}).get("hyphen_count", 0) > 3:
        score += 5
        
    # 2. Domain Signals
    age = signals.get("domain_intel", {}).get("domain_age_days")
    if age is not None:
        if age < 7:
            score += 30
        elif age < 30:
            score += 15
    else:
        # If WHOIS failed, we might assume some risk if other signals are present
        score += 10
        
    # 3. Network Signals
    if not signals.get("ssl_intel", {}).get("ssl_valid"):
        score += 15
    elif signals.get("ssl_intel", {}).get("is_self_signed"):
        score += 20
        
    # 4. Behavioral Signals
    if signals.get("form_intel", {}).get("credential_form_detected"):
        score += 25
    if signals.get("brand_intel", {}).get("brand_impersonation_detected"):
        score += 25
    if signals.get("keyword_intel", {}).get("is_high_keyword_risk"):
        score += 15
    elif signals.get("keyword_intel", {}).get("keyword_count", 0) > 0:
        score += 5
        
    # 5. Content Signals
    if signals.get("script_intel", {}).get("suspicious_scripts_detected"):
        score += 10
        
    # Cap at 100
    return min(score, 100)
