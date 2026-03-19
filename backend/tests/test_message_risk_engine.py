from app.services.message_intelligence.message_risk_engine import calculate_message_risk


def test_message_risk_engine_scores_urgency_and_credentials(monkeypatch):
    # Avoid loading large transformer models in unit tests
    from app.services.message_intelligence import intent_classifier as ic_mod

    monkeypatch.setattr(
        ic_mod.intent_classifier,
        "classify",
        lambda _: {"intent": "account_verification", "confidence": 0.9},
    )

    normalized = "urgent action required verify your account password"
    message_data = {"extracted_urls": ["https://example.com"]}
    out = calculate_message_risk(normalized, message_data)
    assert out["score_details"]["message_risk_score"] >= 40
    assert out["scam_probability"] >= 0.4
