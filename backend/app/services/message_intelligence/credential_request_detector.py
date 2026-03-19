import re
from typing import Dict, Any, List
from app.logger import logger

class CredentialRequestDetector:
    def __init__(self):
        # Soft patterns (feature extraction) for credential harvesting intent.
        # This is not meant to be a blocking ruleset; it feeds downstream AI fusion.
        self._patterns: List[re.Pattern] = [
            # Authentication secrets
            re.compile(r"\b(one[-\s]?time\s+password|otp)\b", re.IGNORECASE),
            re.compile(r"\b(cvv|cvc)\b", re.IGNORECASE),
            re.compile(r"\b(pin|mpin)\b", re.IGNORECASE),
            re.compile(r"\b(password|passcode)\b", re.IGNORECASE),
            # Card/bank details
            re.compile(r"\b(debit|credit)\s+card\b", re.IGNORECASE),
            re.compile(r"\b(card\s+number|16[-\s]?digit)\b", re.IGNORECASE),
            re.compile(r"\b(expiry|expiration)\b", re.IGNORECASE),
            re.compile(r"\b(bank\s+details|account\s+details)\b", re.IGNORECASE),
            # Identity verification flows often abused
            re.compile(r"\b(kyc|verify\s+your\s+identity|confirm\s+your\s+identity)\b", re.IGNORECASE),
            re.compile(r"\b(login\s+details|verify\s+login|reset\s+password)\b", re.IGNORECASE),
            # Crypto secrets
            re.compile(r"\b(seed\s+phrase|recovery\s+phrase|wallet\s+key)\b", re.IGNORECASE),
        ]

    def detect(self, normalized_text: str) -> bool:
        """
        Detect if the message contains requests for credentials.
        Returns True if detected, False otherwise.
        """
        if not normalized_text:
            return False
            
        try:
            for pat in self._patterns:
                if pat.search(normalized_text):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error during credential request detection: {e}")
            return False

credential_request_detector = CredentialRequestDetector()


def detect_credential_requests(text: str) -> bool:
    """Public module-level function: detect if a message contains credential requests."""
    return credential_request_detector.detect(text)
