
def _map_legacy_to_new_level(legacy_level: str) -> str:
    """Map legacy levels to enhanced level names"""
    mapping = {
        LEVEL_SAFE: "Benign",
        LEVEL_SUSPICIOUS: "Suspicious",
        LEVEL_DANGEROUS: "Malicious"
    }
    return mapping.get(legacy_level, "Ambiguous")


def _calculate_confidence(risk_score: int, reasons: List[str]) -> float:
    """Calculate confidence based on signal strength and agreement"""
    base_confidence = min(0.9, max(0.1, len(reasons) * 0.15 + risk_score * 0.02))
    return round(base_confidence, 2)


def _generate_recommendations(risk_level: str, reasons: List[str]) -> List[str]:
    """Generate actionable recommendations based on risk level"""
    if risk_level == LEVEL_DANGEROUS:
        return [
            "BLOCK this message immediately",
            "Do not click any links or provide personal information",
            "Report to your email/service provider as spam/phishing",
            "Verify sender identity through official channels"
        ]
    elif risk_level == LEVEL_SUSPICIOUS:
        return [
            "Exercise caution with this message",
            "Do not respond or click links without verification",
            "Contact sender through known official channels",
            "Consider human review if high-value action is involved"
        ]
    else:
        return [
            "Message appears safe",
            "Proceed normally",
            "No special precautions needed"
        ]


def _analyze_keywords_with_context(text: str, keyword_dict: Dict[str, int]) -> List[Dict]:
    """Enhanced keyword analysis with context awareness"""
    signals = []

    for keyword, base_weight in keyword_dict.items():
        if keyword in text:
            # Context-aware weight adjustment
            weight = base_weight

            # Check for negation (reduces risk)
            words = text.split()
            try:
                keyword_idx = words.index(keyword.split()[0])
                nearby_words = words[max(0, keyword_idx-3):keyword_idx+3]
                if any(neg in nearby_words for neg in ['not', 'don\'t', 'never', 'no', 'avoid']):
                    weight = -abs(weight) * 0.5  # Reduce risk for negated keywords
            except (ValueError, IndexError):
                pass

            # Check for emphasis (increases risk)
            emphasis_words = ['urgent', 'important', 'critical', 'immediately']
            emphasis_boost = sum(1 for emph in emphasis_words if emph in nearby_words) * 0.5
            weight += emphasis_boost

            signals.append({
                'keyword': keyword,
                'weight': weight,
                'reason': f"Detected keyword '{keyword}' with context-adjusted weight"
            })

    return signals


def _analyze_semantic_patterns(text: str, text_without_links: str) -> List[Dict]:
    """Analyze semantic patterns beyond simple keywords"""
    signals = []

    # Urgency patterns
    urgency_phrases = ['act now', 'immediate action', 'time sensitive', 'deadline', 'expires soon']
    urgency_count = sum(1 for phrase in urgency_phrases if phrase in text.lower())
    if urgency_count > 0:
        signals.append({
            'weight': urgency_count * 2,
            'reason': f"Semantic: Urgency pressure detected ({urgency_count} indicators)"
        })

    # Authority imitation
    authority_phrases = ['official notice', 'security alert', 'account services', 'verification required']
    authority_count = sum(1 for phrase in authority_phrases if phrase in text.lower())
    if authority_count > 0:
        signals.append({
            'weight': authority_count * 3,
            'reason': f"Semantic: Authority imitation detected ({authority_count} indicators)"
        })

    # Information requests
    info_request_phrases = ['send your', 'provide your', 'share your', 'enter your', 'confirm your']
    info_request_count = sum(1 for phrase in info_request_phrases if phrase in text.lower())
    if info_request_count > 0:
        signals.append({
            'weight': info_request_count * 4,
            'reason': f"Semantic: Personal information request detected ({info_request_count} indicators)"
        })

    return signals


def _analyze_behavioral_patterns(text: str, text_without_links: str) -> List[Dict]:
    """Analyze behavioral and structural patterns"""
    signals = []

    # Excessive punctuation
    exclamation_count = text.count('!')
    question_count = text.count('?')

    if exclamation_count > 3:
        signals.append({
            'weight': 1,
            'reason': f"Behavioral: Excessive punctuation ({exclamation_count} exclamation marks)"
        })

    # ALL CAPS analysis
    caps_ratio = sum(1 for c in text if c.isupper()) / len(text) if text else 0
    if caps_ratio > 0.3:
        signals.append({
            'weight': 2,
            'reason': f"Behavioral: Excessive capitalization ({caps_ratio:.1%} of text)"
        })

    # Money amounts
    money_pattern = r'[$₹£€]\s*\d+'
    money_matches = len(re.findall(money_pattern, text))
    if money_matches > 0:
        signals.append({
            'weight': money_matches * 2,
            'reason': f"Behavioral: Money amounts mentioned ({money_matches} instances)"
        })

    return signals