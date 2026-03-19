from app.services.database.utils import mask_message_pii


def test_mask_message_pii_masks_common_patterns():
    text = "Email me at test@example.com or call +919876543210. PAN ABCDE1234F"
    masked = mask_message_pii(text)
    assert "[EMAIL]" in masked
    assert "[PHONE]" in masked
    assert "[PAN]" in masked
