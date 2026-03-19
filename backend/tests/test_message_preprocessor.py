from app.services.message_intelligence.message_preprocessor import preprocess_message


def test_message_preprocessor_extracts_urls_and_normalizes():
    msg = "URGENT!! Visit https://example.com/reset ✅"
    out = preprocess_message(msg)
    assert out["extracted_urls"] == ["https://example.com/reset"]
    assert "urgent" in out["normalized"]
    assert "✅" not in out["normalized"]
