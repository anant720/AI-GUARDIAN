from app.services.message_intelligence.urgency_detector import detect_urgency


def test_urgency_detector_flags_urgent_language():
    assert detect_urgency("this is urgent act now!!!") >= 0.9
    assert detect_urgency("hello friend") == 0.0
