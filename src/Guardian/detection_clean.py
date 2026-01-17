"""
AI Guardian Risk Assessment Engine v2.0

Complete redesign of the risk scoring system moving beyond TF-IDF surface matching
to a multi-layer semantic and contextual analysis framework.
"""

import re
import os
import logging
import requests
import joblib
from urllib.parse import urlparse
from . import rules
from . import utils
import socket, ipaddress
import ssl
from datetime import datetime
from .errors import ModelLoadError
import config
import codecs
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import math

# ========================================================================
# NEW RISK ASSESSMENT FRAMEWORK
# ========================================================================

class RiskLevel(Enum):
    """
    Hierarchical risk levels with clear escalation paths.
    Unlike the old Safe/Suspicious/Dangerous, this provides more granularity.
    """
    TRUSTED = "Trusted"          # Explicitly verified legitimate (official senders)
    BENIGN = "Benign"            # Normal, everyday communication
    AMBIGUOUS = "Ambiguous"      # Unclear intent, needs human review
    SUSPICIOUS = "Suspicious"    # Potential risk, monitor closely
    MALICIOUS = "Malicious"      # Clear malicious intent
    CRITICAL = "Critical"        # Immediate danger, block immediately

class SignalType(Enum):
    """Categories of risk signals the system can detect"""
    SEMANTIC = "semantic"        # Meaning-based analysis beyond keywords
    INTENT = "intent"           # Purpose and motivation analysis
    LINGUISTIC = "linguistic"   # Language patterns, tone, structure
    BEHAVIORAL = "behavioral"   # User interaction patterns
    CONTEXTUAL = "contextual"   # Conversation history and sequence
    TECHNICAL = "technical"     # URLs, domains, technical signals

@dataclass
class RiskSignal:
    """
    Represents a single risk signal with confidence and severity metrics.
    Unlike the old additive scoring, this provides probabilistic assessment.
    """
    signal_type: SignalType
    name: str                    # Human-readable signal name
    confidence: float           # How confident we are this signal is present (0.0-1.0)
    severity: float             # How severe this signal is if present (0.0-1.0)
    evidence: List[str]         # Supporting evidence for explainability
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def risk_contribution(self) -> float:
        """Calculate the effective risk contribution of this signal"""
        return self.confidence * self.severity

@dataclass
class RiskAssessment:
    """
    Complete risk assessment result with explainability and recommendations.
    This replaces the old simple {level, score, reasons} structure.
    """
    primary_level: RiskLevel
    confidence_score: float     # Overall confidence in the assessment (0.0-1.0)
    risk_score: float          # Continuous risk score (0.0-1.0)
    signals: List[RiskSignal]
    reasoning: List[str]       # Human-readable explanation chain
    recommendations: List[str] # Actionable recommendations
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_top_signals(self, limit: int = 5) -> List[RiskSignal]:
        """Get the most significant risk signals, sorted by contribution"""
        return sorted(self.signals, key=lambda s: s.risk_contribution, reverse=True)[:limit]

# ========================================================================
# RISK SCORING CONFIGURATION
# ========================================================================

class RiskScorer:
    """
    Configurable risk scoring engine that combines multiple signal types
    with adaptive weighting and explainable decision making.
    """

    def __init__(self):
        # Signal type weights (sum to 1.0)
        self.signal_weights = {
            SignalType.SEMANTIC: 0.30,    # Most important - captures meaning
            SignalType.INTENT: 0.25,      # Purpose analysis
            SignalType.LINGUISTIC: 0.20,  # Language patterns
            SignalType.TECHNICAL: 0.15,   # URLs and technical signals
            SignalType.BEHAVIORAL: 0.07,  # User behavior patterns
            SignalType.CONTEXTUAL: 0.03   # Conversation context
        }

        # Risk level thresholds (continuous scale to categorical)
        self.risk_thresholds = {
            RiskLevel.TRUSTED: (0.0, 0.15),
            RiskLevel.BENIGN: (0.15, 0.35),
            RiskLevel.AMBIGUOUS: (0.35, 0.55),
            RiskLevel.SUSPICIOUS: (0.55, 0.75),
            RiskLevel.MALICIOUS: (0.75, 0.90),
            RiskLevel.CRITICAL: (0.90, 1.0)
        }

        # Confidence thresholds for each risk level
        self.confidence_thresholds = {
            RiskLevel.TRUSTED: 0.8,      # High confidence required for trusted
            RiskLevel.BENIGN: 0.6,
            RiskLevel.AMBIGUOUS: 0.4,    # Lower confidence acceptable for ambiguous
            RiskLevel.SUSPICIOUS: 0.5,
            RiskLevel.MALICIOUS: 0.7,    # Higher confidence for serious accusations
            RiskLevel.CRITICAL: 0.9      # Very high confidence for blocking
        }

    def calculate_risk_score(self, signals: List[RiskSignal]) -> float:
        """
        Calculate overall risk score using weighted signal combination.
        Unlike the old additive scoring, this uses probabilistic combination.
        """
        if not signals:
            return 0.0

        # Group signals by type
        signals_by_type = {}
        for signal in signals:
            if signal.signal_type not in signals_by_type:
                signals_by_type[signal.signal_type] = []
            signals_by_type[signal.signal_type].append(signal)

        # Calculate weighted risk for each signal type
        type_risks = {}
        for signal_type, type_signals in signals_by_type.items():
            # Within each type, combine signals (highest risk dominates)
            max_risk = max((s.risk_contribution for s in type_signals), default=0.0)
            type_risks[signal_type] = max_risk

        # Combine across signal types using configured weights
        total_risk = 0.0
        total_weight = 0.0

        for signal_type, weight in self.signal_weights.items():
            if signal_type in type_risks:
                # Apply diminishing returns to prevent single signal domination
                risk_contribution = min(type_risks[signal_type], 0.8) * weight
                total_risk += risk_contribution
                total_weight += weight

        # Normalize by actual weights used (in case some signal types missing)
        if total_weight > 0:
            total_risk = total_risk / total_weight

        return min(total_risk, 1.0)  # Cap at 1.0

    def determine_risk_level(self, risk_score: float, confidence: float) -> RiskLevel:
        """
        Map continuous risk score to categorical level with confidence gating.
        This prevents low-confidence assessments from reaching high-risk levels.
        """
        # Find the appropriate risk level based on score
        for level in reversed(RiskLevel):  # Check from highest to lowest
            min_score, max_score = self.risk_thresholds[level]
            if min_score <= risk_score <= max_score:
                # Check if we have enough confidence for this level
                if confidence >= self.confidence_thresholds[level]:
                    return level
                else:
                    # Drop down to lower confidence level
                    if level == RiskLevel.CRITICAL:
                        return RiskLevel.MALICIOUS
                    elif level == RiskLevel.MALICIOUS:
                        return RiskLevel.SUSPICIOUS
                    elif level == RiskLevel.SUSPICIOUS:
                        return RiskLevel.AMBIGUOUS
                    else:
                        return level  # Keep lower levels even with low confidence

        return RiskLevel.BENIGN  # Default fallback

    def assess(self, signals: List[RiskSignal]) -> RiskAssessment:
        """
        Main assessment function that combines all signals into a final decision.
        """
        risk_score = self.calculate_risk_score(signals)
        confidence = self._calculate_confidence(signals)

        primary_level = self.determine_risk_level(risk_score, confidence)

        reasoning = self._generate_reasoning(signals, risk_score, confidence)
        recommendations = self._generate_recommendations(primary_level, signals)

        return RiskAssessment(
            primary_level=primary_level,
            confidence_score=confidence,
            risk_score=risk_score,
            signals=signals,
            reasoning=reasoning,
            recommendations=recommendations,
            metadata={
                'signal_count': len(signals),
                'top_signals': [s.name for s in signals[:3]],
                'assessment_timestamp': datetime.now().isoformat()
            }
        )

    def _calculate_confidence(self, signals: List[RiskSignal]) -> float:
        """
        Calculate overall confidence in the assessment.
        Based on signal agreement, strength, and coverage.
        """
        if not signals:
            return 0.0

        # Base confidence on signal strength and agreement
        avg_confidence = sum(s.confidence for s in signals) / len(signals)

        # Bonus for multiple signal types (better coverage)
        signal_types = set(s.signal_type for s in signals)
        type_coverage = len(signal_types) / len(SignalType)
        coverage_bonus = type_coverage * 0.2

        # Penalty for conflicting signals
        risk_signals = [s for s in signals if s.risk_contribution > 0.3]
        benign_signals = [s for s in signals if s.risk_contribution < 0.1]

        conflict_penalty = 0.0
        if risk_signals and benign_signals:
            conflict_penalty = 0.1 * min(len(risk_signals), len(benign_signals))

        confidence = avg_confidence + coverage_bonus - conflict_penalty
        return max(0.0, min(confidence, 1.0))

    def _generate_reasoning(self, signals: List[RiskSignal], risk_score: float,
                          confidence: float) -> List[str]:
        """Generate human-readable reasoning for the assessment"""
        reasoning = []

        if not signals:
            return ["No risk signals detected - appears to be normal communication"]

        # Sort signals by contribution
        top_signals = sorted(signals, key=lambda s: s.risk_contribution, reverse=True)

        # Primary reasoning
        primary_signal = top_signals[0] if top_signals else None
        if primary_signal:
            reasoning.append(f"Primary concern: {primary_signal.name} "
                           f"(confidence: {primary_signal.confidence:.1%}, "
                           f"severity: {primary_signal.severity:.1%})")

        # Signal breakdown
        signal_summary = {}
        for signal in signals:
            signal_type = signal.signal_type.value
            if signal_type not in signal_summary:
                signal_summary[signal_type] = 0
            signal_summary[signal_type] += 1

        if len(signal_summary) > 1:
            type_breakdown = ", ".join(f"{count} {stype}" for stype, count in signal_summary.items())
            reasoning.append(f"Risk signals detected across {len(signal_summary)} categories: {type_breakdown}")

        # Confidence assessment
        if confidence < 0.5:
            reasoning.append("Low confidence assessment - consider human review")
        elif confidence > 0.8:
            reasoning.append("High confidence assessment based on strong signal alignment")

        return reasoning

    def _generate_recommendations(self, risk_level: RiskLevel,
                                signals: List[RiskSignal]) -> List[str]:
        """Generate actionable recommendations based on risk level"""
        recommendations = []

        if risk_level == RiskLevel.CRITICAL:
            recommendations.extend([
                "BLOCK this message immediately",
                "Report to platform administrators",
                "Warn other users about this sender"
            ])
        elif risk_level == RiskLevel.MALICIOUS:
            recommendations.extend([
                "Do not respond or click any links",
                "Report the message as spam/phishing",
                "Verify sender identity through official channels"
            ])
        elif risk_level == RiskLevel.SUSPICIOUS:
            recommendations.extend([
                "Exercise caution",
                "Verify independently before taking action",
                "Check for official contact methods"
            ])
        elif risk_level == RiskLevel.AMBIGUOUS:
            recommendations.extend([
                "Request additional context",
                "Use secondary verification methods",
                "Consider human review if high-value action"
            ])
        elif risk_level in [RiskLevel.BENIGN, RiskLevel.TRUSTED]:
            recommendations.extend([
                "Proceed normally",
                "No special precautions needed"
            ])

        # Add signal-specific recommendations
        for signal in signals[:3]:  # Top 3 signals
            if "password" in signal.name.lower() or "otp" in signal.name.lower():
                recommendations.append("Never share passwords or OTPs via messaging")
            elif "link" in signal.name.lower():
                recommendations.append("Verify URLs independently before clicking")

        return recommendations

# ========================================================================
# LEGACY COMPATIBILITY
# ========================================================================

# Keep old level names for backward compatibility
LEVEL_SAFE = "Safe"
LEVEL_SUSPICIOUS = "Suspicious"
LEVEL_DANGEROUS = "Dangerous"

# Global scorer instance
risk_scorer = RiskScorer()

# ========================================================================
# SIGNAL DETECTION LAYERS
# ========================================================================

class SemanticAnalyzer:
    """
    Advanced semantic analysis beyond TF-IDF keyword matching.
    Detects meaning, intent, and conceptual similarity.
    """

    def __init__(self):
        # Semantic patterns that indicate risk (beyond simple keywords)
        self.risk_patterns = {
            'urgency_pressure': {
                'phrases': [
                    'act immediately', 'do not delay', 'time is running out',
                    'limited time offer', 'expires soon', 'deadline approaching',
                    'respond quickly', 'urgent response required'
                ],
                'severity': 0.8,
                'description': 'Creates false urgency to pressure quick action'
            },
            'authority_imitation': {
                'phrases': [
                    'official notice', 'government agency', 'bank security',
                    'account services', 'customer support', 'verification team',
                    'security department', 'compliance office'
                ],
                'severity': 0.7,
                'description': 'Imitates legitimate authority figures or organizations'
            },
            'emotional_manipulation': {
                'phrases': [
                    'don\'t miss out', 'once in a lifetime', 'amazing opportunity',
                    'life changing', 'transform your life', 'financial freedom',
                    'easy money', 'guaranteed results', 'risk free'
                ],
                'severity': 0.6,
                'description': 'Uses emotional appeals to manipulate decision making'
            },
            'information_requests': {
                'phrases': [
                    'please provide', 'we need your', 'share your details',
                    'confirm your identity', 'verify your information',
                    'send us your', 'update your records'
                ],
                'severity': 0.9,
                'description': 'Requests sensitive personal or financial information'
            },
            'obligation_creation': {
                'phrases': [
                    'you must', 'required to', 'mandatory', 'compulsory',
                    'you are obligated', 'legal requirement', 'compliance needed',
                    'failure to comply', 'consequences for non-payment'
                ],
                'severity': 0.8,
                'description': 'Creates false sense of legal or contractual obligation'
            }
        }

        # Contextual modifiers that change interpretation
        self.context_modifiers = {
            'negation': ['not', 'don\'t', 'never', 'no', 'avoid', 'don\'t click'],
            'safety_indicators': ['official', 'verified', 'secure', 'legitimate', 'trusted'],
            'educational_context': ['learn', 'tutorial', 'guide', 'how to', 'training']
        }

    def analyze_text(self, text: str) -> List[RiskSignal]:
        """Main semantic analysis function"""
        signals = []
        text_lower = text.lower()

        # Check for semantic risk patterns
        for pattern_name, pattern_data in self.risk_patterns.items():
            confidence = self._calculate_pattern_confidence(text_lower, pattern_data['phrases'])
            if confidence > 0.3:  # Only report significant matches
                evidence = self._find_matching_phrases(text, pattern_data['phrases'])

                signals.append(RiskSignal(
                    signal_type=SignalType.SEMANTIC,
                    name=f"Semantic: {pattern_name.replace('_', ' ').title()}",
                    confidence=confidence,
                    severity=pattern_data['severity'],
                    evidence=evidence,
                    context={
                        'description': pattern_data['description'],
                        'matched_phrases': evidence
                    }
                ))

        # Check for contextual modifiers that might reduce risk
        modifier_signals = self._analyze_context_modifiers(text_lower)
        signals.extend(modifier_signals)

        return signals

    def _calculate_pattern_confidence(self, text: str, phrases: List[str]) -> float:
        """Calculate how strongly a text matches a semantic pattern"""
        total_confidence = 0.0
        matches_found = 0

        for phrase in phrases:
            # Use fuzzy matching to catch variations
            if self._fuzzy_match(text, phrase):
                # Weight by phrase specificity (longer phrases = more specific)
                phrase_weight = min(len(phrase.split()) / 10.0, 1.0)
                total_confidence += phrase_weight
                matches_found += 1

        if matches_found == 0:
            return 0.0

        # Normalize by number of matches and apply diminishing returns
        avg_confidence = total_confidence / len(phrases)
        return min(avg_confidence * math.sqrt(matches_found), 1.0)

    def _fuzzy_match(self, text: str, phrase: str) -> bool:
        """Fuzzy matching that allows for minor variations"""
        # Direct substring match
        if phrase in text:
            return True

        # Word-level matching (allows reordering)
        text_words = set(text.split())
        phrase_words = set(phrase.split())

        # At least 80% of phrase words must be present
        overlap = len(phrase_words.intersection(text_words))
        return overlap >= len(phrase_words) * 0.8

    def _find_matching_phrases(self, text: str, phrases: List[str]) -> List[str]:
        """Find which specific phrases matched in the text"""
        matches = []
        text_lower = text.lower()

        for phrase in phrases:
            if phrase.lower() in text_lower:
                matches.append(phrase)

        return matches[:5]  # Limit to top 5 matches

    def _analyze_context_modifiers(self, text: str) -> List[RiskSignal]:
        """Analyze contextual modifiers that might change risk assessment"""
        signals = []

        # Check for negation that might reduce risk
        negation_words = self.context_modifiers['negation']
        negation_count = sum(1 for word in negation_words if word in text)

        if negation_count > 0:
            # Look for negated risky phrases
            risky_phrases = ['urgent', 'click', 'send password', 'verify now']
            negated_risks = []

            for phrase in risky_phrases:
                if phrase in text:
                    # Check if negation appears within 10 words
                    words = text.split()
                    try:
                        phrase_idx = words.index(phrase.split()[0])
                        nearby_words = words[max(0, phrase_idx-5):phrase_idx+5]
                        if any(neg in nearby_words for neg in negation_words):
                            negated_risks.append(phrase)
                    except (ValueError, IndexError):
                        pass

            if negated_risks:
                signals.append(RiskSignal(
                    signal_type=SignalType.SEMANTIC,
                    name="Semantic: Risk Reduction via Negation",
                    confidence=min(negation_count * 0.3, 0.8),
                    severity=-0.4,  # Negative severity reduces risk
                    evidence=[f"Negated risky phrase: '{risk}'" for risk in negated_risks],
                    context={'negation_words_found': negation_count}
                ))

        return signals

class IntentAnalyzer:
    """
    Analyzes the underlying intent and purpose of the communication.
    Distinguishes between benign advisory, malicious manipulation, etc.
    """

    def __init__(self):
        self.intent_patterns = {
            'transactional': {
                'indicators': ['payment', 'delivery', 'order', 'shipping', 'refund', 'transaction'],
                'risk_modifier': -0.3,  # Generally lower risk for business communications
                'confidence_boost': 0.8
            },
            'security_alert': {
                'indicators': ['security', 'alert', 'suspicious', 'unusual activity', 'login attempt'],
                'risk_modifier': 0.2,  # Moderate risk - could be legitimate or scam
                'confidence_boost': 0.7
            },
            'account_maintenance': {
                'indicators': ['update', 'verify', 'confirm', 'account', 'profile', 'settings'],
                'risk_modifier': 0.4,  # Higher risk due to common phishing tactics
                'confidence_boost': 0.9
            },
            'prize_lottery': {
                'indicators': ['won', 'prize', 'lottery', 'winner', 'congratulations', 'claim'],
                'risk_modifier': 0.9,  # Very high risk - classic scam pattern
                'confidence_boost': 0.95
            },
            'technical_support': {
                'indicators': ['support', 'help', 'issue', 'problem', 'fix', 'error', 'virus'],
                'risk_modifier': 0.7,  # High risk for tech support scams
                'confidence_boost': 0.85
            },
            'educational': {
                'indicators': ['learn', 'tutorial', 'guide', 'how to', 'training', 'course'],
                'risk_modifier': -0.5,  # Generally safe educational content
                'confidence_boost': 0.6
            }
        }

    def analyze_intent(self, text: str, links: List[str] = None) -> List[RiskSignal]:
        """Analyze the primary intent of the communication"""
        signals = []
        text_lower = text.lower()
        links = links or []

        # Score each intent type
        intent_scores = {}
        for intent_name, intent_data in self.intent_patterns.items():
            score = self._calculate_intent_score(text_lower, links, intent_data['indicators'])
            intent_scores[intent_name] = score

        # Find the strongest intent signal
        if intent_scores:
            primary_intent = max(intent_scores.items(), key=lambda x: x[1])

            if primary_intent[1] > 0.4:  # Only report significant intents
                intent_data = self.intent_patterns[primary_intent[0]]

                signals.append(RiskSignal(
                    signal_type=SignalType.INTENT,
                    name=f"Intent: {primary_intent[0].replace('_', ' ').title()}",
                    confidence=primary_intent[1],
                    severity=intent_data['risk_modifier'],
                    evidence=self._find_intent_evidence(text, intent_data['indicators']),
                    context={
                        'intent_type': primary_intent[0],
                        'all_scores': intent_scores,
                        'risk_modifier': intent_data['risk_modifier']
                    }
                ))

        # Check for intent conflicts (mixed signals)
        high_confidence_intents = [name for name, score in intent_scores.items() if score > 0.6]

        if len(high_confidence_intents) > 1:
            signals.append(RiskSignal(
                signal_type=SignalType.INTENT,
                name="Intent: Conflicting Purpose Signals",
                confidence=0.7,
                severity=0.3,  # Moderate risk for unclear purpose
                evidence=[f"Multiple intents detected: {', '.join(high_confidence_intents)}"],
                context={'conflicting_intents': high_confidence_intents}
            ))

        return signals

    def _calculate_intent_score(self, text: str, links: List[str],
                              indicators: List[str]) -> float:
        """Calculate how strongly text matches an intent pattern"""
        score = 0.0
        matches = 0

        # Text-based matching
        for indicator in indicators:
            if indicator in text:
                # Weight by indicator specificity
                weight = len(indicator.split()) / 5.0  # Longer phrases = more specific
                score += weight
                matches += 1

        # Link-based intent clues
        if links:
            for link in links:
                link_lower = link.lower()
                if any(indicator in link_lower for indicator in ['verify', 'login', 'account']):
                    score += 0.5  # Suspicious link patterns

        if matches == 0:
            return 0.0

        # Normalize and apply confidence scaling
        normalized_score = min(score / len(indicators), 1.0)
        return normalized_score * (1 + matches * 0.1)  # Bonus for multiple matches

    def _find_intent_evidence(self, text: str, indicators: List[str]) -> List[str]:
        """Find specific evidence for intent classification"""
        evidence = []
        text_lower = text.lower()

        for indicator in indicators:
            if indicator.lower() in text_lower:
                evidence.append(f"Contains '{indicator}'")

        return evidence[:5]

# Global analyzer instances
semantic_analyzer = SemanticAnalyzer()
intent_analyzer = IntentAnalyzer()

# ========================================================================
# SIGNAL DETECTION LAYERS
# ========================================================================

class SemanticAnalyzer:
    """
    Advanced semantic analysis beyond TF-IDF keyword matching.
    Detects meaning, intent, and conceptual similarity.
    """

    def __init__(self):
        # Semantic patterns that indicate risk (beyond simple keywords)
        self.risk_patterns = {
            'urgency_pressure': {
                'phrases': [
                    'act immediately', 'do not delay', 'time is running out',
                    'limited time offer', 'expires soon', 'deadline approaching',
                    'respond quickly', 'urgent response required'
                ],
                'severity': 0.8,
                'description': 'Creates false urgency to pressure quick action'
            },
            'authority_imitation': {
                'phrases': [
                    'official notice', 'government agency', 'bank security',
                    'account services', 'customer support', 'verification team',
                    'security department', 'compliance office'
                ],
                'severity': 0.7,
                'description': 'Imitates legitimate authority figures or organizations'
            },
            'emotional_manipulation': {
                'phrases': [
                    'don\'t miss out', 'once in a lifetime', 'amazing opportunity',
                    'life changing', 'transform your life', 'financial freedom',
                    'easy money', 'guaranteed results', 'risk free'
                ],
                'severity': 0.6,
                'description': 'Uses emotional appeals to manipulate decision making'
            },
            'information_requests': {
                'phrases': [
                    'please provide', 'we need your', 'share your details',
                    'confirm your identity', 'verify your information',
                    'send us your', 'update your records'
                ],
                'severity': 0.9,
                'description': 'Requests sensitive personal or financial information'
            },
            'obligation_creation': {
                'phrases': [
                    'you must', 'required to', 'mandatory', 'compulsory',
                    'you are obligated', 'legal requirement', 'compliance needed',
                    'failure to comply', 'consequences for non-payment'
                ],
                'severity': 0.8,
                'description': 'Creates false sense of legal or contractual obligation'
            }
        }

        # Contextual modifiers that change interpretation
        self.context_modifiers = {
            'negation': ['not', 'don\'t', 'never', 'no', 'avoid', 'don\'t click'],
            'safety_indicators': ['official', 'verified', 'secure', 'legitimate', 'trusted'],
            'educational_context': ['learn', 'tutorial', 'guide', 'how to', 'training']
        }

    def analyze_text(self, text: str) -> List[RiskSignal]:
        """Main semantic analysis function"""
        signals = []
        text_lower = text.lower()

        # Check for semantic risk patterns
        for pattern_name, pattern_data in self.risk_patterns.items():
            confidence = self._calculate_pattern_confidence(text_lower, pattern_data['phrases'])
            if confidence > 0.3:  # Only report significant matches
                evidence = self._find_matching_phrases(text, pattern_data['phrases'])

                signals.append(RiskSignal(
                    signal_type=SignalType.SEMANTIC,
                    name=f"Semantic: {pattern_name.replace('_', ' ').title()}",
                    confidence=confidence,
                    severity=pattern_data['severity'],
                    evidence=evidence,
                    context={
                        'description': pattern_data['description'],
                        'matched_phrases': evidence
                    }
                ))

        # Check for contextual modifiers that might reduce risk
        modifier_signals = self._analyze_context_modifiers(text_lower)
        signals.extend(modifier_signals)

        return signals

    def _calculate_pattern_confidence(self, text: str, phrases: List[str]) -> float:
        """Calculate how strongly a text matches a semantic pattern"""
        total_confidence = 0.0
        matches_found = 0

        for phrase in phrases:
            # Use fuzzy matching to catch variations
            if self._fuzzy_match(text, phrase):
                # Weight by phrase specificity (longer phrases = more specific)
                phrase_weight = min(len(phrase.split()) / 10.0, 1.0)
                total_confidence += phrase_weight
                matches_found += 1

        if matches_found == 0:
            return 0.0

        # Normalize by number of matches and apply diminishing returns
        avg_confidence = total_confidence / len(phrases)
        return min(avg_confidence * math.sqrt(matches_found), 1.0)

    def _fuzzy_match(self, text: str, phrase: str) -> bool:
        """Fuzzy matching that allows for minor variations"""
        # Direct substring match
        if phrase in text:
            return True

        # Word-level matching (allows reordering)
        text_words = set(text.split())
        phrase_words = set(phrase.split())

        # At least 80% of phrase words must be present
        overlap = len(phrase_words.intersection(text_words))
        return overlap >= len(phrase_words) * 0.8

    def _find_matching_phrases(self, text: str, phrases: List[str]) -> List[str]:
        """Find which specific phrases matched in the text"""
        matches = []
        text_lower = text.lower()

        for phrase in phrases:
            if phrase.lower() in text_lower:
                matches.append(phrase)

        return matches[:5]  # Limit to top 5 matches

    def _analyze_context_modifiers(self, text: str) -> List[RiskSignal]:
        """Analyze contextual modifiers that might change risk assessment"""
        signals = []

        # Check for negation that might reduce risk
        negation_words = self.context_modifiers['negation']
        negation_count = sum(1 for word in negation_words if word in text)

        if negation_count > 0:
            # Look for negated risky phrases
            risky_phrases = ['urgent', 'click', 'send password', 'verify now']
            negated_risks = []

            for phrase in risky_phrases:
                if phrase in text:
                    # Check if negation appears within 10 words
                    words = text.split()
                    try:
                        phrase_idx = words.index(phrase.split()[0])
                        nearby_words = words[max(0, phrase_idx-5):phrase_idx+5]
                        if any(neg in nearby_words for neg in negation_words):
                            negated_risks.append(phrase)
                    except (ValueError, IndexError):
                        pass

            if negated_risks:
                signals.append(RiskSignal(
                    signal_type=SignalType.SEMANTIC,
                    name="Semantic: Risk Reduction via Negation",
                    confidence=min(negation_count * 0.3, 0.8),
                    severity=-0.4,  # Negative severity reduces risk
                    evidence=[f"Negated risky phrase: '{risk}'" for risk in negated_risks],
                    context={'negation_words_found': negation_count}
                ))

        return signals

class IntentAnalyzer:
    """
    Analyzes the underlying intent and purpose of the communication.
    Distinguishes between benign advisory, malicious manipulation, etc.
    """

    def __init__(self):
        self.intent_patterns = {
            'transactional': {
                'indicators': ['payment', 'delivery', 'order', 'shipping', 'refund', 'transaction'],
                'risk_modifier': -0.3,  # Generally lower risk for business communications
                'confidence_boost': 0.8
            },
            'security_alert': {
                'indicators': ['security', 'alert', 'suspicious', 'unusual activity', 'login attempt'],
                'risk_modifier': 0.2,  # Moderate risk - could be legitimate or scam
                'confidence_boost': 0.7
            },
            'account_maintenance': {
                'indicators': ['update', 'verify', 'confirm', 'account', 'profile', 'settings'],
                'risk_modifier': 0.4,  # Higher risk due to common phishing tactics
                'confidence_boost': 0.9
            },
            'prize_lottery': {
                'indicators': ['won', 'prize', 'lottery', 'winner', 'congratulations', 'claim'],
                'risk_modifier': 0.9,  # Very high risk - classic scam pattern
                'confidence_boost': 0.95
            },
            'technical_support': {
                'indicators': ['support', 'help', 'issue', 'problem', 'fix', 'error', 'virus'],
                'risk_modifier': 0.7,  # High risk for tech support scams
                'confidence_boost': 0.85
            },
            'educational': {
                'indicators': ['learn', 'tutorial', 'guide', 'how to', 'training', 'course'],
                'risk_modifier': -0.5,  # Generally safe educational content
                'confidence_boost': 0.6
            }
        }

    def analyze_intent(self, text: str, links: List[str] = None) -> List[RiskSignal]:
        """Analyze the primary intent of the communication"""
        signals = []
        text_lower = text.lower()
        links = links or []

        # Score each intent type
        intent_scores = {}
        for intent_name, intent_data in self.intent_patterns.items():
            score = self._calculate_intent_score(text_lower, links, intent_data['indicators'])
            intent_scores[intent_name] = score

        # Find the strongest intent signal
        if intent_scores:
            primary_intent = max(intent_scores.items(), key=lambda x: x[1])

            if primary_intent[1] > 0.4:  # Only report significant intents
                intent_data = self.intent_patterns[primary_intent[0]]

                signals.append(RiskSignal(
                    signal_type=SignalType.INTENT,
                    name=f"Intent: {primary_intent[0].replace('_', ' ').title()}",
                    confidence=primary_intent[1],
                    severity=intent_data['risk_modifier'],
                    evidence=self._find_intent_evidence(text, intent_data['indicators']),
                    context={
                        'intent_type': primary_intent[0],
                        'all_scores': intent_scores,
                        'risk_modifier': intent_data['risk_modifier']
                    }
                ))

        # Check for intent conflicts (mixed signals)
        high_confidence_intents = [name for name, score in intent_scores.items() if score > 0.6]

        if len(high_confidence_intents) > 1:
            signals.append(RiskSignal(
                signal_type=SignalType.INTENT,
                name="Intent: Conflicting Purpose Signals",
                confidence=0.7,
                severity=0.3,  # Moderate risk for unclear purpose
                evidence=[f"Multiple intents detected: {', '.join(high_confidence_intents)}"],
                context={'conflicting_intents': high_confidence_intents}
            ))

        return signals

    def _calculate_intent_score(self, text: str, links: List[str],
                              indicators: List[str]) -> float:
        """Calculate how strongly text matches an intent pattern"""
        score = 0.0
        matches = 0

        # Text-based matching
        for indicator in indicators:
            if indicator in text:
                # Weight by indicator specificity
                weight = len(indicator.split()) / 5.0  # Longer phrases = more specific
                score += weight
                matches += 1

        # Link-based intent clues
        if links:
            for link in links:
                link_lower = link.lower()
                if any(indicator in link_lower for indicator in ['verify', 'login', 'account']):
                    score += 0.5  # Suspicious link patterns

        if matches == 0:
            return 0.0

        # Normalize and apply confidence scaling
        normalized_score = min(score / len(indicators), 1.0)
        return normalized_score * (1 + matches * 0.1)  # Bonus for multiple matches

    def _find_intent_evidence(self, text: str, indicators: List[str]) -> List[str]:
        """Find specific evidence for intent classification"""
        evidence = []
        text_lower = text.lower()

        for indicator in indicators:
            if indicator.lower() in text_lower:
                evidence.append(f"Contains '{indicator}'")

        return evidence[:5]

# Global analyzer instances
semantic_analyzer = SemanticAnalyzer()
intent_analyzer = IntentAnalyzer()

# Configuration for the new risk assessment system
RISK_CONFIG = {
    'signal_weights': {
        SignalType.SEMANTIC: 0.25,
        SignalType.INTENT: 0.30,
        SignalType.LINGUISTIC: 0.20,
        SignalType.BEHAVIORAL: 0.15,
        SignalType.CONTEXTUAL: 0.05,
        SignalType.TECHNICAL: 0.05
    },
    'confidence_thresholds': {
        RiskLevel.TRUSTED: 0.9,
        RiskLevel.BENIGN: 0.7,
        RiskLevel.AMBIGUOUS: 0.5,
        RiskLevel.SUSPICIOUS: 0.3,
        RiskLevel.MALICIOUS: 0.1,
        RiskLevel.CRITICAL: 0.0
    },
    'risk_thresholds': {
        RiskLevel.TRUSTED: (0.0, 0.1),
        RiskLevel.BENIGN: (0.1, 0.3),
        RiskLevel.AMBIGUOUS: (0.3, 0.5),
        RiskLevel.SUSPICIOUS: (0.5, 0.7),
        RiskLevel.MALICIOUS: (0.7, 0.9),
        RiskLevel.CRITICAL: (0.9, 1.0)
    }
}

VECTORIZER_PATH = config.MODEL_CONFIG['VECTORIZER_PATH']
MODEL_PATH = config.MODEL_CONFIG['MODEL_PATH']

ML_MODEL = None
VECTORIZER = None

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

MALICIOUS_DOMAINS_PATH = os.path.join(os.path.dirname(__file__), "model", "malicious_domains.txt")

def decode_punycode(domain):
    """Decode punycode parts in a domain."""
    parts = domain.split('.')
    decoded_parts = []
    for part in parts:
        if part.startswith('xn--'):
            try:
                decoded = codecs.decode(part[4:], 'punycode')
                decoded_parts.append(decoded)
            except:
                decoded_parts.append(part)
        else:
            decoded_parts.append(part)
    return '.'.join(decoded_parts)

def edit_distance(s1, s2):
    """Calculate the Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def detect_typosquatting(domain, brand_domains):
    """
    Enhanced typosquatting detection with multiple techniques.
    Returns (risk_score, reason) tuple.
    """
    domain_lower = domain.lower()
    risk_score = 0
    reasons = []
    
    for brand_domain in brand_domains:
        brand = brand_domain.split('.')[0].lower()
        
        # 1. Direct character substitution detection
        char_substitutions = {
            '0': 'o', '1': 'i', '1': 'l', '3': 'e', '4': 'a', 
            '5': 's', '7': 't', '8': 'b', '9': 'g', '6': 'g',
            '2': 'z', '5': 's', '8': 'b'
        }
        
        # Check for number-to-letter substitutions
        normalized_domain = domain_lower
        for num, letter in char_substitutions.items():
            normalized_domain = normalized_domain.replace(num, letter)
        
        if brand in normalized_domain and brand not in domain_lower:
            risk_score += 12
            reasons.append(f"Domain '{domain}' uses number substitution to impersonate '{brand}'")
            continue
            
        # 2. Common typosquatting patterns
        typosquatting_patterns = [
            (f"{brand}0", f"{brand} with 0 instead of o"),
            (f"{brand}1", f"{brand} with 1 instead of i"),
            (f"{brand}3", f"{brand} with 3 instead of e"),
            (f"{brand}4", f"{brand} with 4 instead of a"),
            (f"{brand}5", f"{brand} with 5 instead of s"),
            (f"{brand}7", f"{brand} with 7 instead of t"),
            (f"{brand}8", f"{brand} with 8 instead of b"),
            (f"{brand}9", f"{brand} with 9 instead of g"),
            (f"0{brand}", f"0 instead of o in {brand}"),
            (f"1{brand}", f"1 instead of i in {brand}"),
            (f"3{brand}", f"3 instead of e in {brand}"),
            (f"4{brand}", f"4 instead of a in {brand}"),
            (f"5{brand}", f"5 instead of s in {brand}"),
            (f"7{brand}", f"7 instead of t in {brand}"),
            (f"8{brand}", f"8 instead of b in {brand}"),
            (f"9{brand}", f"9 instead of g in {brand}"),
            # Additional common typosquatting patterns
            (f"{brand[0]}0{brand[1:]}", f"{brand} with 0 instead of o"),
            (f"{brand[0]}1{brand[1:]}", f"{brand} with 1 instead of i"),
            (f"{brand[0]}3{brand[1:]}", f"{brand} with 3 instead of e"),
            (f"{brand[0]}4{brand[1:]}", f"{brand} with 4 instead of a"),
            (f"{brand[0]}5{brand[1:]}", f"{brand} with 5 instead of s"),
            (f"{brand[0]}7{brand[1:]}", f"{brand} with 7 instead of t"),
            (f"{brand[0]}8{brand[1:]}", f"{brand} with 8 instead of b"),
            (f"{brand[0]}9{brand[1:]}", f"{brand} with 9 instead of g"),
        ]
        
        for pattern, description in typosquatting_patterns:
            if pattern in domain_lower:
                risk_score += 10
                reasons.append(f"Domain '{domain}' appears to be typosquatting: {description}")
                break
                
        # 3. Edit distance check (existing logic)
        if edit_distance(brand, domain_lower) <= 2 and brand not in domain_lower:
            risk_score += 8
            reasons.append(f"Domain '{domain}' is very similar to '{brand}' (typosquatting)")
            continue
            
        # 4. Check for missing/extra characters and character substitutions
        if len(domain_lower) >= len(brand) - 1 and len(domain_lower) <= len(brand) + 2:
            if brand in domain_lower or any(brand[i:i+3] in domain_lower for i in range(len(brand)-2)):
                risk_score += 6
                reasons.append(f"Domain '{domain}' suspiciously similar to '{brand}'")
                continue
                
        # 5. Check for character substitutions within the domain
        for i in range(len(brand)):
            for num, letter in char_substitutions.items():
                # Check if domain has number where brand has letter
                if (i < len(domain_lower) and 
                    brand[i] == letter and 
                    domain_lower[i] == num and
                    domain_lower[:i] + letter + domain_lower[i+1:] == brand):
                    risk_score += 8
                    reasons.append(f"Domain '{domain}' uses '{num}' instead of '{letter}' to impersonate '{brand}'")
                    break
            if risk_score > 0:
                break
                
        # 6. Check for letter-to-number substitutions (reverse of above)
        for i in range(len(domain_lower)):
            for num, letter in char_substitutions.items():
                # Check if domain has letter where brand has number
                if (i < len(brand) and 
                    domain_lower[i] == letter and 
                    brand[i] == num and
                    brand[:i] + letter + brand[i+1:] == domain_lower):
                    risk_score += 8
                    reasons.append(f"Domain '{domain}' uses '{letter}' instead of '{num}' to impersonate '{brand}'")
                    break
            if risk_score > 0:
                break
                
        # 7. Check for partial brand matches with substitutions
        if len(domain_lower) >= 3:  # Minimum length for meaningful comparison
            for i in range(len(brand) - 2):  # Check 3-character substrings
                brand_substring = brand[i:i+3]
                if len(brand_substring) == 3:
                    for j in range(len(domain_lower) - 2):
                        domain_substring = domain_lower[j:j+3]
                        if len(domain_substring) == 3:
                            # Check for single character substitution
                            if sum(a != b for a, b in zip(brand_substring, domain_substring)) == 1:
                                for k, (b_char, d_char) in enumerate(zip(brand_substring, domain_substring)):
                                    if b_char != d_char:
                                        for num, letter in char_substitutions.items():
                                            if (b_char == letter and d_char == num) or (b_char == num and d_char == letter):
                                                risk_score += 6
                                                reasons.append(f"Domain '{domain}' appears to substitute characters to mimic '{brand}'")
                                                break
                                        if risk_score > 0:
                                            break
                                if risk_score > 0:
                                    break
                    if risk_score > 0:
                        break
                        
        # 8. Check for common typosquatting patterns with fuzzy matching
        if len(domain_lower) >= 4 and len(brand) >= 4:
            # Check if domain contains most of the brand name with substitutions
            brand_chars = set(brand)
            domain_chars = set(domain_lower)
            
            # Check for character substitutions
            substitutions_found = 0
            for num, letter in char_substitutions.items():
                if letter in brand and num in domain_lower:
                    substitutions_found += 1
                if num in brand and letter in domain_lower:
                    substitutions_found += 1
            
            # If we find character substitutions and domain is similar length
            if substitutions_found > 0 and abs(len(domain_lower) - len(brand)) <= 2:
                # Check if domain contains significant portion of brand
                brand_in_domain = sum(1 for char in brand if char in domain_lower)
                if brand_in_domain >= len(brand) * 0.6:  # At least 60% of brand characters present
                    risk_score += 7
                    reasons.append(f"Domain '{domain}' appears to be typosquatting '{brand}' with character substitutions")
                    
        # 9. Check for specific common typosquatting patterns
        common_typosquatting = {
            'amazon': ['amzan', 'amaz0n', 'amz0n', 'amaz0n', 'amz0n'],
            'google': ['g00gle', 'g0ogle', 'go0gle', 'g00gle', 'g0ogle'],
            'facebook': ['faceb00k', 'faceb0ok', 'faceb00k', 'faceb0ok'],
            'apple': ['app1e', 'app1e', 'app1e'],
            'microsoft': ['micr0s0ft', 'micr0soft', 'micr0s0ft'],
            'netflix': ['netf1ix', 'netf1x', 'netf1ix'],
            'paypal': ['paypa1', 'payp4l', 'paypa1'],
            'instagram': ['1nstagram', 'inst4gram', '1nstagram'],
            'twitter': ['tw1tter', 'tw1ter', 'tw1tter'],
            'linkedin': ['1inkedin', 'linked1n', '1inkedin']
        }
        
        if brand in common_typosquatting:
            for typo in common_typosquatting[brand]:
                if typo in domain_lower:
                    risk_score += 10
                    reasons.append(f"Domain '{domain}' uses common typosquatting pattern '{typo}' to impersonate '{brand}'")
                    break
    
    return risk_score, reasons

def load_malicious_domains():
    domains = set(rules.MALICIOUS_DOMAINS)
    try:
        if os.path.exists(MALICIOUS_DOMAINS_PATH):
            with open(MALICIOUS_DOMAINS_PATH, 'r', encoding='utf-8') as f:
                external_domains = {line.strip() for line in f if line.strip()}
            domains.update(external_domains)
    except Exception as e:
        logging.error(f"Error loading malicious domains file: {e}")
    return domains

ALL_MALICIOUS_DOMAINS = load_malicious_domains()

def get_contextual_override(text: str, links: list) -> (str, str):
    clean_text = text.lower()
    sender_id_match = re.match(r"^[a-zA-Z]{2}-([a-zA-Z0-9_]+):", text)
    if sender_id_match:
        sender_id = sender_id_match.group(1)
        if any(official_id.lower() == sender_id.lower() for official_id in rules.OFFICIAL_SENDER_IDS):
            return ("Safe", f"Message is from a trusted sender ID: {sender_id}")
    for link in links:
        domain = urlparse(link).netloc
        if domain and any(domain.endswith(safe_ext) for safe_ext in rules.OFFICIAL_DOMAIN_EXTENSIONS):
            return ("Safe", f"Message contains a trusted official domain: {domain}")
    return (None, None)

def check_phishtank(link: str) -> (int, str):
    """
    Checks the URL against PhishTank database for known phishing sites.
    Returns a risk score and reason.
    """
    try:
        api_url = f"http://phishtank.com/checkurl/"
        data = {'url': link, 'format': 'json'}
        response = requests.post(api_url, data=data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('results', {}).get('in_database', False):
                verified = result['results'].get('verified', False)
                if verified:
                    return 20, f"This link is confirmed as a phishing site by PhishTank."
                else:
                    return 10, f"This link is reported as suspicious on PhishTank."
    except Exception as e:
        logging.warning(f"PhishTank check failed for {link}: {e}")
    return 0, ""

def check_link_tls(link: str) -> (int, str):
    try:
        domain = urlparse(link).netloc
        if not domain:
            return 0, ""
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=3) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                protocol_version = ssock.version()
                if protocol_version in ["TLSv1.1", "TLSv1.0", "SSLv3"]:
                    return 5, rules.FRIENDLY_REASONS["INSECURE_PROTOCOL"]
                expiry_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                if expiry_date < datetime.utcnow():
                    return 8, rules.FRIENDLY_REASONS["EXPIRED_CERT"]
    except ssl.SSLCertVerificationError:
        return 8, rules.FRIENDLY_REASONS["INVALID_CERT"]
    except (socket.timeout, socket.gaierror, ConnectionRefusedError):
        return 0, ""
    except Exception:
        return 1, f"Could not perform TLS check on link: {domain}"
    return 0, ""

def analyse_link_advanced(link: str) -> (int, list):
    risk_score = 0
    reasons = []
    final_url = link
    try:
        domain = urlparse(link).netloc
        shortener_pattern = rules.WEIGHTED_SUSPICIOUS_PATTERNS["SHORTENED_URL"][0]
        if re.search(shortener_pattern, domain, re.IGNORECASE):
            try:
                with requests.Session() as session:
                    session.headers.update({'User-Agent': 'Mozilla/5.0'})
                    resp = session.head(link, allow_redirects=True, timeout=5)
                    final_url = resp.url
                    reasons.append(f"URL shortener '{link}' redirects to: {final_url}")
            except requests.RequestException:
                risk_score += 4
                reasons.append(rules.FRIENDLY_REASONS["UNRESOLVED_SHORTENER"].format(detail=link))
                return risk_score, reasons
        final_domain = urlparse(final_url).netloc
        decoded_domain = decode_punycode(final_domain)
        if any(decoded_domain.endswith(safe_ext) for safe_ext in rules.OFFICIAL_DOMAIN_EXTENSIONS):
            return 0, []
        phishtank_score, phishtank_reason = check_phishtank(final_url)
        if phishtank_score > 0:
            risk_score += phishtank_score
            reasons.append(phishtank_reason)
        try:
            ipaddress.ip_address(final_domain)
            risk_score += 8
            reasons.append(rules.FRIENDLY_REASONS["IP_AS_DOMAIN"])
        except ValueError:
            pass
        if decoded_domain in ALL_MALICIOUS_DOMAINS or final_domain in ALL_MALICIOUS_DOMAINS:
            risk_score += 15
            reasons.append(rules.FRIENDLY_REASONS["MALICIOUS_DOMAIN"].format(detail=final_domain))
        if final_domain != decoded_domain:
            for brand_domain in rules.TARGET_BRAND_DOMAINS:
                if brand_domain in decoded_domain:
                    risk_score += 15
                    reasons.append(f"Domain uses punycode to impersonate '{brand_domain}': {final_domain}")
                    break
        # Enhanced typosquatting detection
        typosquatting_score, typosquatting_reasons = detect_typosquatting(final_domain, rules.TARGET_BRAND_DOMAINS)
        if typosquatting_score > 0:
            risk_score += typosquatting_score
            reasons.extend(typosquatting_reasons)
        if final_url.startswith("https://"):
            tls_score, tls_reason = check_link_tls(final_url)
            if tls_score > 0:
                risk_score += tls_score
                reasons.append(tls_reason)
    except Exception as e:
        reasons.append(f"An error occurred during advanced link analysis: {e}")
    return risk_score, reasons

def analyse_message(text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Enhanced risk assessment with improved pattern detection and semantic analysis.
    Combines traditional TF-IDF with contextual understanding and behavioral signals.
    """
    logging.info(f"Starting enhanced analysis for message: {text[:100]}...")
    risk_score = 0
    reasons = []
    context = context or {}

    # Extract links
    links = utils.extract_links(text)

    # Check for trusted senders (highest priority)
    override_level, override_reason = get_contextual_override(text, links)
    if override_level == "Safe":
        return {
            "level": LEVEL_SAFE,
            "score": 0,
            "reasons": [override_reason],
            "links": links,
            "risk_assessment": {
                "primary_level": "Trusted",
                "confidence_score": 0.95,
                "continuous_risk_score": 0.0,
                "signal_count": 1,
                "recommendations": ["Proceed normally - verified trusted sender"]
            }
        }

    # Clean and prepare text
    clean_text = text.lower()
    text_without_links = clean_text
    for link in links:
        text_without_links = text_without_links.replace(link.lower(), " ")

    # ========================================================================
    # ENHANCED PATTERN DETECTION (Beyond basic TF-IDF)
    # ========================================================================

    # 1. Enhanced Keyword Analysis with Context
    keyword_signals = _analyze_keywords_with_context(text_without_links, rules.SCAM_KEYWORDS)
    for signal in keyword_signals:
        risk_score += signal['weight']
        reasons.append(signal['reason'])

    # 2. Semantic Pattern Detection
    semantic_signals = _analyze_semantic_patterns(text, text_without_links)
    for signal in semantic_signals:
        risk_score += signal['weight']
        reasons.append(signal['reason'])

    # 3. Behavioral Pattern Analysis
    behavioral_signals = _analyze_behavioral_patterns(text, text_without_links)
    for signal in behavioral_signals:
        risk_score += signal['weight']
        reasons.append(signal['reason'])

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
        reasons.append(f"Message contains {len(links)} link(s): {', '.join(links)}")
        for link in links:
            # Domain pattern checks
            domain_patterns_to_check = ["SUSPICIOUS_DOMAIN_TLD", "SHORTENED_URL"]
            for pattern_name in domain_patterns_to_check:
                regex, weight = rules.WEIGHTED_SUSPICIOUS_PATTERNS[pattern_name]
                if re.search(regex, link, re.IGNORECASE):
                    risk_score += weight
                    reasons.append(rules.FRIENDLY_REASONS.get(pattern_name, f"Link pattern: {pattern_name}"))

            # Advanced link analysis
            link_score, link_reasons = analyse_link_advanced(link)
            if link_score > 0:
                risk_score += link_score
                reasons.extend(link_reasons)

    # ========================================================================
    # SAFE KEYWORD ADJUSTMENT
    # ========================================================================
    if not high_threat_pattern_found and not any('typosquatting' in reason.lower() or 'impersonat' in reason.lower() for reason in reasons):
        for keyword, weight in rules.SAFE_KEYWORDS.items():
            if keyword in text_without_links:
                risk_score += weight
                reasons.append(f"Message contains a known safe keyword: '{keyword}' (Score adjusted)")

    # ========================================================================
    # ML MODEL ANALYSIS
    # ========================================================================
    if ML_MODEL and VECTORIZER:
        try:
            vectorized_text = VECTORIZER.transform([text_without_links])
            scam_probability = ML_MODEL.predict_proba(vectorized_text)[0][1]
            if scam_probability > 0.9:
                risk_score += 8
                reasons.append(rules.FRIENDLY_REASONS["ML_CONFIDENCE"])
            elif scam_probability > 0.5:
                risk_score += 0
                if risk_score > 0:
                    reasons.append(rules.FRIENDLY_REASONS["ML_CONFIDENCE"])
        except Exception as e:
            reasons.append(f"Error during ML model prediction: {e}")

    # ========================================================================
    # RISK LEVEL DETERMINATION
    # ========================================================================
    risk_score = int(risk_score)
    if risk_score >= config.RISK_THRESHOLDS['DANGEROUS']:
        risk_level = LEVEL_DANGEROUS
    elif risk_score >= config.RISK_THRESHOLDS['SUSPICIOUS']:
        risk_level = LEVEL_SUSPICIOUS
    else:
        risk_level = LEVEL_SAFE

    # Calculate confidence based on signal strength and agreement
    confidence = min(0.9, max(0.1, len(reasons) * 0.1 + risk_score * 0.01))

    # Enhanced response with new assessment format
    logging.info(f"Analysis complete. Level: {risk_level}, Score: {risk_score}, Reasons: {len(reasons)}")
    return {
        "level": risk_level,
        "score": risk_score,
        "reasons": reasons,
        "links": links,
        "risk_assessment": {
            "primary_level": _map_legacy_to_new_level(risk_level),
            "confidence_score": confidence,
            "continuous_risk_score": risk_score / 20.0,  # Normalize to 0-1 scale
            "signal_count": len(reasons),
            "recommendations": _generate_recommendations(risk_level, reasons)
        }
    }


def _map_legacy_to_new_level(legacy_level: str) -> str:
    """Map legacy levels to new enhanced level names"""
    mapping = {
        LEVEL_SAFE: "Benign",
        LEVEL_SUSPICIOUS: "Suspicious",
        LEVEL_DANGEROUS: "Malicious"
    }
    return mapping.get(legacy_level, "Ambiguous")


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

 
 d e f   _ c o n v e r t _ t o _ l e g a c y _ f o r m a t ( a s s e s s m e n t ,   l i n k s ) : 
 
         " " " 
 
         C o n v e r t   n e w   R i s k A s s e s s m e n t   f o r m a t   t o   l e g a c y   f o r m a t   f o r   b a c k w a r d   c o m p a t i b i l i t y . 
 
         T h i s   a l l o w s   e x i s t i n g   A P I   c o n s u m e r s   t o   c o n t i n u e   w o r k i n g . 
 
         " " " 
 
         #   M a p   n e w   r i s k   l e v e l s   t o   l e g a c y   l e v e l s 
 
         l e g a c y _ l e v e l _ m a p p i n g   =   { 
 
                 R i s k L e v e l . T R U S T E D :   L E V E L _ S A F E , 
 
                 R i s k L e v e l . B E N I G N :   L E V E L _ S A F E , 
 
                 R i s k L e v e l . A M B I G U O U S :   L E V E L _ S U S P I C I O U S , 
 
                 R i s k L e v e l . S U S P I C I O U S :   L E V E L _ S U S P I C I O U S , 
 
                 R i s k L e v e l . M A L I C I O U S :   L E V E L _ D A N G E R O U S , 
 
                 R i s k L e v e l . C R I T I C A L :   L E V E L _ D A N G E R O U S 
 
         } 
 
 
 
         l e g a c y _ l e v e l   =   l e g a c y _ l e v e l _ m a p p i n g . g e t ( a s s e s s m e n t . p r i m a r y _ l e v e l ,   L E V E L _ S U S P I C I O U S ) 
 
 
 
         #   C o n v e r t   c o n t i n u o u s   r i s k   s c o r e   t o   l e g a c y   i n t e g e r   s c a l e 
 
         l e g a c y _ s c o r e   =   i n t ( a s s e s s m e n t . r i s k _ s c o r e   *   2 0 )     #   S c a l e   0 - 1   t o   r o u g h l y   0 - 2 0 
 
 
 
         #   B u i l d   l e g a c y   r e a s o n s   f r o m   n e w   r e a s o n i n g   +   t o p   s i g n a l s 
 
         l e g a c y _ r e a s o n s   =   a s s e s s m e n t . r e a s o n i n g . c o p y ( ) 
 
 
 
         #   A d d   t o p   3   s i g n a l   e x p l a n a t i o n s 
 
         t o p _ s i g n a l s   =   a s s e s s m e n t . g e t _ t o p _ s i g n a l s ( 3 ) 
 
         f o r   s i g n a l   i n   t o p _ s i g n a l s : 
 
                 i f   s i g n a l . e v i d e n c e : 
 
                         l e g a c y _ r e a s o n s . a p p e n d ( f " { s i g n a l . n a m e } :   { ' ,   ' . j o i n ( s i g n a l . e v i d e n c e [ : 2 ] ) } " ) 
 
 
 
         r e t u r n   { 
 
                 " l e v e l " :   l e g a c y _ l e v e l , 
 
                 " s c o r e " :   l e g a c y _ s c o r e , 
 
                 " r e a s o n s " :   l e g a c y _ r e a s o n s , 
 
                 " l i n k s " :   l i n k s , 
 
                 #   N e w   f i e l d s   f o r   e n h a n c e d   A P I   c o n s u m e r s 
 
                 " r i s k _ a s s e s s m e n t " :   { 
 
                         " p r i m a r y _ l e v e l " :   a s s e s s m e n t . p r i m a r y _ l e v e l . v a l u e , 
 
                         " c o n f i d e n c e _ s c o r e " :   a s s e s s m e n t . c o n f i d e n c e _ s c o r e , 
 
                         " c o n t i n u o u s _ r i s k _ s c o r e " :   a s s e s s m e n t . r i s k _ s c o r e , 
 
                         " s i g n a l _ c o u n t " :   l e n ( a s s e s s m e n t . s i g n a l s ) , 
 
                         " r e c o m m e n d a t i o n s " :   a s s e s s m e n t . r e c o m m e n d a t i o n s 
 
                 } 
 
         } 
 
 
 
 
 
 d e f   _ a n a l y z e _ l i n g u i s t i c _ p a t t e r n s ( t e x t ) : 
 
         " " " A n a l y z e   l i n g u i s t i c   p a t t e r n s   l i k e   u r g e n c y ,   m a n i p u l a t i o n ,   s t r u c t u r e " " " 
 
         s i g n a l s   =   [ ] 
 
         t e x t _ l o w e r   =   t e x t . l o w e r ( ) 
 
 
 
         #   U r g e n c y   a n d   p r e s s u r e   p a t t e r n s 
 
         u r g e n c y _ i n d i c a t o r s   =   [ ' ! ' ,   ' u r g e n t ' ,   ' i m m e d i a t e l y ' ,   ' n o w ' ,   ' a s a p ' ,   ' h u r r y ' ,   ' q u i c k ' ] 
 
         u r g e n c y _ c o u n t   =   s u m ( 1   f o r   w o r d   i n   u r g e n c y _ i n d i c a t o r s   i f   w o r d   i n   t e x t _ l o w e r ) 
 
 
 
         i f   u r g e n c y _ c o u n t   >   0 : 
 
                 s e v e r i t y   =   m i n ( u r g e n c y _ c o u n t   *   0 . 2 ,   0 . 8 ) 
 
                 s i g n a l s . a p p e n d ( R i s k S i g n a l ( 
 
                         s i g n a l _ t y p e = S i g n a l T y p e . L I N G U I S T I C , 
 
                         n a m e = " L i n g u i s t i c :   U r g e n c y   P r e s s u r e " , 
 
                         c o n f i d e n c e = m i n ( u r g e n c y _ c o u n t   *   0 . 3 ,   0 . 9 ) , 
 
                         s e v e r i t y = s e v e r i t y , 
 
                         e v i d e n c e = [ f " F o u n d   { u r g e n c y _ c o u n t }   u r g e n c y   i n d i c a t o r s " ] , 
 
                         c o n t e x t = { ' u r g e n c y _ w o r d s ' :   u r g e n c y _ c o u n t } 
 
                 ) ) 
 
 
 
         #   E m o t i o n a l   m a n i p u l a t i o n   p a t t e r n s 
 
         e m o t i o n a l _ w o r d s   =   [ ' a m a z i n g ' ,   ' i n c r e d i b l e ' ,   ' l i f e - c h a n g i n g ' ,   ' g u a r a n t e e d ' ,   ' f r e e   m o n e y ' ] 
 
         e m o t i o n a l _ c o u n t   =   s u m ( 1   f o r   w o r d   i n   e m o t i o n a l _ w o r d s   i f   w o r d   i n   t e x t _ l o w e r ) 
 
 
 
         i f   e m o t i o n a l _ c o u n t   >   0 : 
 
                 s i g n a l s . a p p e n d ( R i s k S i g n a l ( 
 
                         s i g n a l _ t y p e = S i g n a l T y p e . L I N G U I S T I C , 
 
                         n a m e = " L i n g u i s t i c :   E m o t i o n a l   M a n i p u l a t i o n " , 
 
                         c o n f i d e n c e = m i n ( e m o t i o n a l _ c o u n t   *   0 . 4 ,   0 . 8 ) , 
 
                         s e v e r i t y = 0 . 6 , 
 
                         e v i d e n c e = [ f " E m o t i o n a l   a p p e a l   w o r d s :   { e m o t i o n a l _ c o u n t } " ] , 
 
                         c o n t e x t = { ' e m o t i o n a l _ w o r d s ' :   e m o t i o n a l _ c o u n t } 
 
                 ) ) 
 
 
 
         #   A u t h o r i t y   i m i t a t i o n   p a t t e r n s 
 
         a u t h o r i t y _ p h r a s e s   =   [ ' o f f i c i a l ' ,   ' g o v e r n m e n t ' ,   ' b a n k ' ,   ' s e c u r i t y ' ,   ' v e r i f y ' ] 
 
         a u t h o r i t y _ s c o r e   =   s u m ( 1   f o r   p h r a s e   i n   a u t h o r i t y _ p h r a s e s   i f   p h r a s e   i n   t e x t _ l o w e r ) 
 
 
 
         i f   a u t h o r i t y _ s c o r e   > =   2 :     #   M u l t i p l e   a u t h o r i t y   i n d i c a t o r s 
 
                 s i g n a l s . a p p e n d ( R i s k S i g n a l ( 
 
                         s i g n a l _ t y p e = S i g n a l T y p e . L I N G U I S T I C , 
 
                         n a m e = " L i n g u i s t i c :   A u t h o r i t y   I m i t a t i o n " , 
 
                         c o n f i d e n c e = m i n ( a u t h o r i t y _ s c o r e   *   0 . 2 5 ,   0 . 8 5 ) , 
 
                         s e v e r i t y = 0 . 7 , 
 
                         e v i d e n c e = [ f " A u t h o r i t y   i n d i c a t o r s :   { a u t h o r i t y _ s c o r e } " ] , 
 
                         c o n t e x t = { ' a u t h o r i t y _ i n d i c a t o r s ' :   a u t h o r i t y _ s c o r e } 
 
                 ) ) 
 
 
 
         r e t u r n   s i g n a l s 
 
 
 
 
 
 d e f   _ a n a l y z e _ t e c h n i c a l _ s i g n a l s ( t e x t ,   l i n k s ) : 
 
         " " " A n a l y z e   t e c h n i c a l   s i g n a l s   l i k e   U R L s ,   d o m a i n s ,   e t c . " " " 
 
         s i g n a l s   =   [ ] 
 
 
 
         #   L i n k   a n a l y s i s 
 
         i f   l i n k s : 
 
                 s i g n a l s . a p p e n d ( R i s k S i g n a l ( 
 
                         s i g n a l _ t y p e = S i g n a l T y p e . T E C H N I C A L , 
 
                         n a m e = " T e c h n i c a l :   C o n t a i n s   L i n k s " , 
 
                         c o n f i d e n c e = 0 . 6 , 
 
                         s e v e r i t y = 0 . 3 ,     #   N e u t r a l   -   l i n k s   t h e m s e l v e s   a r e n ' t   r i s k y 
 
                         e v i d e n c e = [ f " F o u n d   { l e n ( l i n k s ) }   l i n k s " ] , 
 
                         c o n t e x t = { ' l i n k _ c o u n t ' :   l e n ( l i n k s ) ,   ' l i n k s ' :   l i n k s } 
 
                 ) ) 
 
 
 
                 #   A n a l y z e   e a c h   l i n k 
 
                 f o r   l i n k   i n   l i n k s : 
 
                         l i n k _ s i g n a l s   =   _ a n a l y z e _ s i n g l e _ l i n k ( l i n k ) 
 
                         s i g n a l s . e x t e n d ( l i n k _ s i g n a l s ) 
 
 
 
         #   C h e c k   f o r   s u s p i c i o u s   n u m b e r   p a t t e r n s   ( p h o n e   n u m b e r s ,   a m o u n t s ) 
 
         n u m b e r _ p a t t e r n s   =   [ 
 
                 ( r ' \ b \ d { 1 0 } \ b ' ,   ' s u s p i c i o u s _ n u m b e r ' ,   ' 1 0 - d i g i t   n u m b e r   ( p o s s i b l e   p h o n e ) ' ,   0 . 4 ) , 
 
                 ( r ' \ $ \ d + ' ,   ' m o n e y _ a m o u n t ' ,   ' M o n e y   a m o u n t   m e n t i o n e d ' ,   0 . 3 ) , 
 
                 ( r ' \ b \ d { 6 } \ b ' ,   ' s i x _ d i g i t ' ,   ' 6 - d i g i t   n u m b e r   ( p o s s i b l e   O T P ) ' ,   0 . 8 ) 
 
         ] 
 
 
 
         f o r   p a t t e r n ,   s i g n a l _ n a m e ,   d e s c r i p t i o n ,   s e v e r i t y   i n   n u m b e r _ p a t t e r n s : 
 
                 i f   r e . s e a r c h ( p a t t e r n ,   t e x t ) : 
 
                         s i g n a l s . a p p e n d ( R i s k S i g n a l ( 
 
                                 s i g n a l _ t y p e = S i g n a l T y p e . T E C H N I C A L , 
 
                                 n a m e = f " T e c h n i c a l :   { s i g n a l _ n a m e . r e p l a c e ( ' _ ' ,   '   ' ) . t i t l e ( ) } " , 
 
                                 c o n f i d e n c e = 0 . 7 , 
 
                                 s e v e r i t y = s e v e r i t y , 
 
                                 e v i d e n c e = [ d e s c r i p t i o n ] , 
 
                                 c o n t e x t = { ' p a t t e r n ' :   p a t t e r n } 
 
                         ) ) 
 
 
 
         r e t u r n   s i g n a l s 
 
 
 
 
 
 d e f   _ a n a l y z e _ s i n g l e _ l i n k ( l i n k ) : 
 
         " " " A n a l y z e   a   s i n g l e   l i n k   f o r   t e c h n i c a l   r i s k   s i g n a l s " " " 
 
         s i g n a l s   =   [ ] 
 
         l i n k _ l o w e r   =   l i n k . l o w e r ( ) 
 
 
 
         #   S h o r t e n e d   U R L   s e r v i c e s 
 
         s h o r t e n e r s   =   [ ' b i t . l y ' ,   ' t . c o ' ,   ' t i n y u r l . c o m ' ,   ' g o o . g l ' ,   ' o w . l y ' ] 
 
         f o r   s h o r t e n e r   i n   s h o r t e n e r s : 
 
                 i f   s h o r t e n e r   i n   l i n k _ l o w e r : 
 
                         s i g n a l s . a p p e n d ( R i s k S i g n a l ( 
 
                                 s i g n a l _ t y p e = S i g n a l T y p e . T E C H N I C A L , 
 
                                 n a m e = " T e c h n i c a l :   S h o r t e n e d   U R L " , 
 
                                 c o n f i d e n c e = 0 . 9 , 
 
                                 s e v e r i t y = 0 . 7 , 
 
                                 e v i d e n c e = [ f " U s e s   U R L   s h o r t e n e r :   { s h o r t e n e r } " ] , 
 
                                 c o n t e x t = { ' s h o r t e n e r ' :   s h o r t e n e r } 
 
                         ) ) 
 
                         b r e a k 
 
 
 
         #   S u s p i c i o u s   T L D s 
 
         s u s p i c i o u s _ t l d s   =   [ ' . t k ' ,   ' . m l ' ,   ' . g a ' ,   ' . c f ' ,   ' . g q ' ,   ' . x y z ' ,   ' . t o p ' ,   ' . b u z z ' ] 
 
         f o r   t l d   i n   s u s p i c i o u s _ t l d s : 
 
                 i f   l i n k _ l o w e r . e n d s w i t h ( t l d ) : 
 
                         s i g n a l s . a p p e n d ( R i s k S i g n a l ( 
 
                                 s i g n a l _ t y p e = S i g n a l T y p e . T E C H N I C A L , 
 
                                 n a m e = " T e c h n i c a l :   S u s p i c i o u s   D o m a i n   T L D " , 
 
                                 c o n f i d e n c e = 0 . 8 , 
 
                                 s e v e r i t y = 0 . 6 , 
 
                                 e v i d e n c e = [ f " U n c o m m o n   T L D :   { t l d } " ] , 
 
                                 c o n t e x t = { ' t l d ' :   t l d } 
 
                         ) ) 
 
                         b r e a k 
 
 
 
         #   D o m a i n   a n a l y s i s 
 
         t r y : 
 
                 d o m a i n   =   u r l p a r s e ( l i n k ) . n e t l o c 
 
                 i f   d o m a i n : 
 
                         #   C h e c k   f o r   I P   a d d r e s s e s   i n   U R L s 
 
                         i f   r e . m a t c h ( r ' \ d + \ . \ d + \ . \ d + \ . \ d + ' ,   d o m a i n ) : 
 
                                 s i g n a l s . a p p e n d ( R i s k S i g n a l ( 
 
                                         s i g n a l _ t y p e = S i g n a l T y p e . T E C H N I C A L , 
 
                                         n a m e = " T e c h n i c a l :   I P   A d d r e s s   i n   U R L " , 
 
                                         c o n f i d e n c e = 0 . 9 5 , 
 
                                         s e v e r i t y = 0 . 9 , 
 
                                         e v i d e n c e = [ " U R L   c o n t a i n s   I P   a d d r e s s   i n s t e a d   o f   d o m a i n   n a m e " ] , 
 
                                         c o n t e x t = { ' i p _ a d d r e s s ' :   d o m a i n } 
 
                                 ) ) 
 
 
 
                         #   C h e c k   f o r   e x c e s s i v e   n u m b e r s   i n   d o m a i n 
 
                         n u m b e r _ c o u n t   =   s u m ( 1   f o r   c h a r   i n   d o m a i n   i f   c h a r . i s d i g i t ( ) ) 
 
                         i f   n u m b e r _ c o u n t   >   4 : 
 
                                 s i g n a l s . a p p e n d ( R i s k S i g n a l ( 
 
                                         s i g n a l _ t y p e = S i g n a l T y p e . T E C H N I C A L , 
 
                                         n a m e = " T e c h n i c a l :   N u m e r i c a l l y   H e a v y   D o m a i n " , 
 
                                         c o n f i d e n c e = 0 . 7 , 
 
                                         s e v e r i t y = 0 . 5 , 
 
                                         e v i d e n c e = [ f " D o m a i n   c o n t a i n s   { n u m b e r _ c o u n t }   n u m b e r s " ] , 
 
                                         c o n t e x t = { ' n u m b e r _ c o u n t ' :   n u m b e r _ c o u n t } 
 
                                 ) ) 
 
 
 
         e x c e p t   E x c e p t i o n   a s   e : 
 
                 l o g g i n g . w a r n i n g ( f " E r r o r   a n a l y z i n g   l i n k   { l i n k } :   { e } " ) 
 
 
 
         r e t u r n   s i g n a l s 
 
 
 
 
 
 d e f   _ a n a l y z e _ c o n v e r s a t i o n _ c o n t e x t ( t e x t ,   c o n v e r s a t i o n _ h i s t o r y ) : 
 
         " " " A n a l y z e   c o n v e r s a t i o n   c o n t e x t   a n d   p a t t e r n s   o v e r   t i m e " " " 
 
         s i g n a l s   =   [ ] 
 
 
 
         i f   n o t   c o n v e r s a t i o n _ h i s t o r y : 
 
                 r e t u r n   s i g n a l s 
 
 
 
         #   C h e c k   f o r   e s c a l a t i o n   p a t t e r n s 
 
         r e c e n t _ m e s s a g e s   =   c o n v e r s a t i o n _ h i s t o r y [ - 5 : ]     #   L a s t   5   m e s s a g e s 
 
         u r g e n c y _ e s c a l a t i o n   =   s u m ( 1   f o r   m s g   i n   r e c e n t _ m e s s a g e s 
 
                                                       i f   a n y ( w o r d   i n   m s g . g e t ( ' t e x t ' ,   ' ' ) . l o w e r ( ) 
 
                                                                 f o r   w o r d   i n   [ ' u r g e n t ' ,   ' i m m e d i a t e l y ' ,   ' n o w ' ,   ' a s a p ' ] ) ) 
 
 
 
         i f   u r g e n c y _ e s c a l a t i o n   > =   3 :     #   M u l t i p l e   u r g e n t   m e s s a g e s   i n   s e q u e n c e 
 
                 s i g n a l s . a p p e n d ( R i s k S i g n a l ( 
 
                         s i g n a l _ t y p e = S i g n a l T y p e . C O N T E X T U A L , 
 
                         n a m e = " C o n t e x t u a l :   U r g e n c y   E s c a l a t i o n " , 
 
                         c o n f i d e n c e = m i n ( u r g e n c y _ e s c a l a t i o n   *   0 . 2 ,   0 . 9 ) , 
 
                         s e v e r i t y = 0 . 7 , 
 
                         e v i d e n c e = [ f " F o u n d   u r g e n c y   i n   { u r g e n c y _ e s c a l a t i o n }   o f   l a s t   5   m e s s a g e s " ] , 
 
                         c o n t e x t = { ' u r g e n c y _ m e s s a g e s ' :   u r g e n c y _ e s c a l a t i o n } 
 
                 ) ) 
 
 
 
         #   C h e c k   f o r   r e p e t i t i v e   r e q u e s t s 
 
         c u r r e n t _ r e q u e s t s   =   _ e x t r a c t _ r e q u e s t s ( t e x t ) 
 
         i f   c u r r e n t _ r e q u e s t s : 
 
                 h i s t o r i c a l _ r e q u e s t s   =   [ ] 
 
                 f o r   m s g   i n   r e c e n t _ m e s s a g e s [ : - 1 ] :     #   E x c l u d e   c u r r e n t   m e s s a g e 
 
                         h i s t o r i c a l _ r e q u e s t s . e x t e n d ( _ e x t r a c t _ r e q u e s t s ( m s g . g e t ( ' t e x t ' ,   ' ' ) ) ) 
 
 
 
                 #   F i n d   r e p e a t e d   r e q u e s t   p a t t e r n s 
 
                 r e p e a t e d _ r e q u e s t s   =   s e t ( c u r r e n t _ r e q u e s t s )   &   s e t ( h i s t o r i c a l _ r e q u e s t s ) 
 
                 i f   r e p e a t e d _ r e q u e s t s : 
 
                         s i g n a l s . a p p e n d ( R i s k S i g n a l ( 
 
                                 s i g n a l _ t y p e = S i g n a l T y p e . C O N T E X T U A L , 
 
                                 n a m e = " C o n t e x t u a l :   R e p e a t e d   R e q u e s t s " , 
 
                                 c o n f i d e n c e = 0 . 8 , 
 
                                 s e v e r i t y = 0 . 6 , 
 
                                 e v i d e n c e = [ f " R e p e a t e d   r e q u e s t s :   { ' ,   ' . j o i n ( r e p e a t e d _ r e q u e s t s ) } " ] , 
 
                                 c o n t e x t = { ' r e p e a t e d _ r e q u e s t s ' :   l i s t ( r e p e a t e d _ r e q u e s t s ) } 
 
                         ) ) 
 
 
 
         r e t u r n   s i g n a l s 
 
 
 
 
 
 d e f   _ e x t r a c t _ r e q u e s t s ( t e x t ) : 
 
         " " " E x t r a c t   r e q u e s t   p a t t e r n s   f r o m   t e x t " " " 
 
         r e q u e s t s   =   [ ] 
 
         t e x t _ l o w e r   =   t e x t . l o w e r ( ) 
 
 
 
         r e q u e s t _ p a t t e r n s   =   [ 
 
                 ' s e n d ' ,   ' p r o v i d e ' ,   ' s h a r e ' ,   ' g i v e   m e ' ,   ' n e e d   y o u r ' , 
 
                 ' c l i c k   h e r e ' ,   ' v e r i f y ' ,   ' c o n f i r m ' ,   ' u p d a t e ' 
 
         ] 
 
 
 
         f o r   p a t t e r n   i n   r e q u e s t _ p a t t e r n s : 
 
                 i f   p a t t e r n   i n   t e x t _ l o w e r : 
 
                         r e q u e s t s . a p p e n d ( p a t t e r n ) 
 
 
 
         r e t u r n   l i s t ( s e t ( r e q u e s t s ) )     #   R e m o v e   d u p l i c a t e s 
 
 