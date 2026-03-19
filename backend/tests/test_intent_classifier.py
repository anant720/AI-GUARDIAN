from app.services.message_intelligence.intent_classifier import IntentClassifier


def test_intent_classifier_empty_text_is_safe():
    clf = IntentClassifier()
    res = clf.classify("")
    assert res["intent"] == "unknown"
    assert res["confidence"] == 0.0
