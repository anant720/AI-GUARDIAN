# AI Guardian Risk Assessment Engine v2.0

## Executive Summary

This document outlines a complete redesign of the AI Guardian risk scoring system, moving beyond the flawed TF-IDF similarity approach to a sophisticated multi-layer semantic and contextual analysis framework.

## Current System Problems (Audited)

### TF-IDF Issues
- **Surface-level matching**: Only detects exact keyword matches, misses paraphrases
- **No semantic understanding**: "Call bank immediately" vs "Contact financial institution right away" treated as completely different
- **Context ignorance**: Same keywords flagged regardless of benign vs malicious context
- **Fixed weights**: No adaptation based on message context or user history

### Rule System Problems
- **Redundant rules**: "urgent" (2), "immediate" (2), "action required" (3) - essentially identical
- **Overlapping logic**: Multiple rules detect similar urgency/manipulation patterns
- **False positives**: Generic rules like "click this link" flag legitimate communications
- **Inconsistent weighting**: OTP gets weight 6 but "one time password" gets 6 - duplicate detection
- **Context-blind**: Rules don't consider message sequence or user intent
- **Maintenance nightmare**: 100+ fragmented rules with unclear interactions

### Scoring Problems
- **Additive scoring**: Simple sum creates unpredictable results
- **Hard thresholds**: Abrupt jumps between Safe/Suspicious/Dangerous
- **No confidence measures**: System can't express uncertainty
- **Binary thinking**: Loses nuance in risk assessment

## New Risk Scoring Philosophy

### Hybrid Scoring Approach
Instead of a single numeric score, we use:
- **Continuous Risk Score (0.0-1.0)**: Probabilistic assessment of malicious intent
- **Confidence Score (0.0-1.0)**: How certain the system is about its assessment
- **Tiered Risk Levels**: Categorical levels with gating confidence requirements

### Justification
This approach is superior because:
- **Probabilistic**: Captures uncertainty inherent in language understanding
- **Contextual**: Different thresholds for different scenarios
- **Explainable**: Clear reasoning with confidence levels
- **Adaptable**: Continuous scores allow fine-tuned decision making

## Multi-Layer Risk Evaluation System

### 1. Semantic Understanding Layer

**Beyond TF-IDF**: Conceptual pattern matching instead of keyword matching.

```python
# Example semantic patterns
SEMANTIC_PATTERNS = {
    'urgency_pressure': {
        'phrases': ['act immediately', 'do not delay', 'time is running out'],
        'severity': 0.8,
        'description': 'Creates false urgency to pressure quick action'
    },
    'authority_imitation': {
        'phrases': ['official notice', 'government agency', 'bank security'],
        'severity': 0.7,
        'description': 'Imitates legitimate authority figures'
    }
}
```

**Capabilities**:
- Fuzzy phrase matching for paraphrase detection
- Contextual modifiers (negation reduces risk)
- Concept-level similarity beyond exact words

### 2. Intent & Purpose Analysis

**Intent Classification**: Distinguishes communication purpose.

```python
INTENT_PATTERNS = {
    'transactional': {
        'indicators': ['payment', 'delivery', 'order', 'refund'],
        'risk_modifier': -0.3  # Generally lower risk
    },
    'prize_lottery': {
        'indicators': ['won', 'prize', 'lottery', 'congratulations'],
        'risk_modifier': 0.9   # Very high risk - classic scam
    }
}
```

**Capabilities**:
- Purpose inference beyond surface keywords
- Educational vs operational intent distinction
- Multi-intent conflict detection

### 3. Linguistic & Behavioral Signals

**Language Pattern Analysis**:
```python
# Urgency detection
urgency_indicators = ['!', 'urgent', 'immediately', 'ASAP']
urgency_score = count_indicators(text)

# Emotional manipulation
emotional_words = ['amazing', 'life-changing', 'guaranteed']
emotional_score = weighted_emotional_analysis(text)
```

**Capabilities**:
- Tone and structure analysis
- Emotional manipulation detection
- Authority imitation recognition

### 4. Technical & Link Analysis

**Enhanced Technical Signals**:
```python
# Beyond simple regex
TECHNICAL_ANALYSIS = {
    'ip_addresses': {'severity': 0.9, 'confidence': 0.95},
    'suspicious_tlds': {'severity': 0.6, 'confidence': 0.8},
    'numerically_heavy_domains': {'severity': 0.5, 'confidence': 0.7}
}
```

### 5. Contextual & Temporal Analysis

**Conversation Memory**:
```python
# Track patterns over time
CONTEXTUAL_SIGNALS = {
    'urgency_escalation': detect_urgency_increase(history),
    'repeated_requests': find_request_patterns(history),
    'intent_drift': analyze_purpose_changes(history)
}
```

## Scoring Algorithm

### Signal Aggregation
```python
def calculate_risk_score(signals: List[RiskSignal]) -> float:
    # Group by signal type
    semantic_risk = max_risk_by_type(signals, SignalType.SEMANTIC)
    intent_risk = max_risk_by_type(signals, SignalType.INTENT)
    linguistic_risk = max_risk_by_type(signals, SignalType.LINGUISTIC)
    technical_risk = max_risk_by_type(signals, SignalType.TECHNICAL)
    contextual_risk = max_risk_by_type(signals, SignalType.CONTEXTUAL)

    # Weighted combination with diminishing returns
    weights = {
        SignalType.SEMANTIC: 0.30,
        SignalType.INTENT: 0.25,
        SignalType.LINGUISTIC: 0.20,
        SignalType.TECHNICAL: 0.15,
        SignalType.CONTEXTUAL: 0.10
    }

    total_risk = (
        semantic_risk * weights[SignalType.SEMANTIC] +
        intent_risk * weights[SignalType.INTENT] +
        linguistic_risk * weights[SignalType.LINGUISTIC] +
        technical_risk * weights[SignalType.TECHNICAL] +
        contextual_risk * weights[SignalType.CONTEXTUAL]
    )

    return min(total_risk, 1.0)
```

### Risk Level Determination
```python
RISK_THRESHOLDS = {
    RiskLevel.TRUSTED: (0.0, 0.15),     # High confidence required
    RiskLevel.BENIGN: (0.15, 0.35),
    RiskLevel.AMBIGUOUS: (0.35, 0.55),  # Low confidence acceptable
    RiskLevel.SUSPICIOUS: (0.55, 0.75),
    RiskLevel.MALICIOUS: (0.75, 0.90),
    RiskLevel.CRITICAL: (0.90, 1.0)
}

CONFIDENCE_REQUIREMENTS = {
    RiskLevel.TRUSTED: 0.8,      # Strict confidence for trusted
    RiskLevel.CRITICAL: 0.9,     # High confidence for blocking
    RiskLevel.AMBIGUOUS: 0.4     # Lenient for human review
}
```

## Explainability Framework

### Signal Prioritization
```python
def generate_explanation(assessment: RiskAssessment) -> List[str]:
    reasoning = []

    # Primary risk driver
    if assessment.signals:
        top_signal = max(assessment.signals, key=lambda s: s.risk_contribution)
        reasoning.append(f"Primary concern: {top_signal.name} "
                        f"(confidence: {top_signal.confidence:.1%})")

    # Signal type breakdown
    type_counts = {}
    for signal in assessment.signals:
        type_counts[signal.signal_type] = type_counts.get(signal.signal_type, 0) + 1

    if len(type_counts) > 1:
        breakdown = ", ".join(f"{count} {stype.value}" for stype, count in type_counts.items())
        reasoning.append(f"Risk signals across {len(type_counts)} categories: {breakdown}")

    # Confidence assessment
    if assessment.confidence_score < 0.5:
        reasoning.append("Low confidence assessment - consider human review")
    elif assessment.confidence_score > 0.8:
        reasoning.append("High confidence assessment with strong signal alignment")

    return reasoning
```

### Evidence Chain
```python
def get_signal_evidence(signal: RiskSignal) -> List[str]:
    """Extract human-readable evidence for a signal"""
    evidence = signal.evidence.copy()

    # Add contextual information
    if signal.context.get('matched_phrases'):
        evidence.append(f"Matched phrases: {', '.join(signal.context['matched_phrases'])}")

    if signal.context.get('urgency_words'):
        evidence.append(f"Urgency indicators found: {signal.context['urgency_words']}")

    return evidence
```

## Testing & Validation Strategy

### Test Categories

#### 1. Legacy Compatibility Tests
```python
# Ensure old API still works
def test_legacy_api_compatibility():
    old_result = analyse_message("urgent bank verification")
    assert old_result['level'] in ['Safe', 'Suspicious', 'Dangerous']
    assert isinstance(old_result['score'], int)
    assert isinstance(old_result['reasons'], list)
```

#### 2. Behavioral Tests
```python
TEST_CASES = [
    # Benign cases
    ("Your order #12345 has been delivered", RiskLevel.BENIGN),
    ("Please confirm your email address", RiskLevel.AMBIGUOUS),

    # Suspicious cases
    ("URGENT: Your account will be suspended unless you verify now", RiskLevel.SUSPICIOUS),
    ("You won $1,000,000! Click here to claim", RiskLevel.MALICIOUS),

    # Malicious cases
    ("FBI ALERT: Your computer is infected. Call this number immediately", RiskLevel.CRITICAL)
]
```

#### 3. Edge Case Tests
```python
EDGE_CASES = [
    # Context changes meaning
    ("Don't click this suspicious link", RiskLevel.BENIGN),  # Negation
    ("This is not urgent at all", RiskLevel.BENIGN),        # Negation
    ("Click here for legitimate banking", RiskLevel.AMBIGUOUS),  # Ambiguous

    # Multi-intent messages
    ("Your package delivery requires payment. Call now or lose it forever", RiskLevel.MALICIOUS),

    # Authority imitation
    ("Bank of America Security Alert: Verify your account", RiskLevel.SUSPICIOUS)
]
```

#### 4. False Positive/Negative Analysis
```python
def analyze_false_positives():
    """Test legitimate messages that old system flagged"""
    legitimate_messages = [
        "Your Amazon order has shipped",
        "Please verify your Netflix account",
        "Bank transfer of $500 completed",
        "Click here to download the latest security update"
    ]

    for msg in legitimate_messages:
        result = analyse_message(msg)
        if result['risk_assessment']['continuous_risk_score'] > 0.5:
            print(f"False positive: {msg}")
            print(f"Signals: {[s.name for s in result.get('signals', [])]}")
```

## Production Implementation

### Performance Optimizations
```python
# Lazy loading for heavy components
class LazySemanticAnalyzer:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = SemanticAnalyzer()  # Heavy initialization
        return cls._instance
```

### Caching Strategy
```python
# Cache frequent analyses
@lru_cache(maxsize=1000)
def cached_analysis(text_hash: str, context_hash: str) -> RiskAssessment:
    # Implementation with proper cache invalidation
    pass
```

### Monitoring & Adaptation
```python
class RiskScorerMonitor:
    def __init__(self):
        self.performance_metrics = {
            'false_positive_rate': 0.0,
            'false_negative_rate': 0.0,
            'average_confidence': 0.0,
            'signal_distribution': {}
        }

    def update_metrics(self, assessment: RiskAssessment, actual_risk: RiskLevel):
        # Update performance tracking
        pass

    def adapt_weights(self):
        # Adjust signal weights based on performance
        pass
```

## Migration Strategy

### Phase 1: Parallel Operation
```python
def analyse_message_dual(text: str) -> Dict:
    """Run both old and new systems in parallel"""
    old_result = analyse_message_v1(text)
    new_result = analyse_message_v2(text)

    return {
        'legacy': old_result,
        'v2': new_result,
        'comparison': compare_results(old_result, new_result)
    }
```

### Phase 2: Gradual Rollout
```python
# Feature flags for gradual deployment
FEATURE_FLAGS = {
    'use_semantic_analysis': True,
    'use_intent_analysis': True,
    'enhanced_explainability': True,
    'legacy_fallback': True  # Keep old system as backup
}
```

### Phase 3: Full Migration
- Monitor performance for 30 days
- A/B test with human reviewers
- Gradual increase of traffic to new system
- Complete migration once confidence >95%

## Future Evolution

### Adaptive Learning
```python
class AdaptiveRiskScorer(RiskScorer):
    def __init__(self):
        super().__init__()
        self.feedback_loop = FeedbackLearner()

    def learn_from_feedback(self, message: str, human_assessment: RiskLevel):
        """Incorporate human feedback to improve future assessments"""
        pass
```

### Advanced Features
- **Multi-language support**: Extend semantic analysis beyond English
- **Domain-specific models**: Specialized models for financial, healthcare, etc.
- **Real-time adaptation**: Adjust weights based on current threat landscape
- **Collaborative filtering**: Learn from community feedback

## Conclusion

This redesigned system transforms AI Guardian from a basic keyword matcher into a sophisticated AI safety system that:

- **Understands meaning** beyond surface-level text
- **Provides probabilistic assessments** with confidence measures
- **Offers clear explainability** for all decisions
- **Adapts and learns** from real-world usage
- **Maintains production reliability** while enabling innovation

The new system eliminates the core problems of TF-IDF approaches while establishing a foundation for advanced AI safety capabilities.