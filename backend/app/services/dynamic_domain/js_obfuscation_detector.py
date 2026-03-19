"""
js_obfuscation_detector.py
───────────────────────────
Detects JavaScript obfuscation techniques commonly used in phishing pages
to evade static scanners and analysts.

Signals detected:
  • eval( calls
  • unescape( calls  
  • atob( Base64 decode
  • String.fromCharCode( character-code arrays
  • document.write( with encoded content
  • Long base64 blobs (> 200 continuous chars without spaces)
  • Hexadecimal string encoding (\x41\x42...)
  • Packed/minified scripts with obfuscation markers
"""
import re
from typing import Dict, Any, List

from app.logger import logger

_OBF_PATTERNS = [
    (r'\beval\s*\(',            "eval_call",           0.35),
    (r'\bunescape\s*\(',        "unescape_call",       0.25),
    (r'\batob\s*\(',            "base64_decode",       0.20),
    (r'String\.fromCharCode\s*\(', "charcode_encoding", 0.25),
    (r'document\.write\s*\(',  "document_write",      0.15),
    (r'\\x[0-9a-fA-F]{2}(?:\\x[0-9a-fA-F]{2}){5,}', "hex_encoding", 0.30),
    (r'[A-Za-z0-9+/]{200,}={0,2}', "long_base64_blob", 0.20),
    (r'\bexec\s*\(',            "exec_call",           0.20),
]

# Packed/uglified code markers
_PACKER_MARKERS = [
    r"\beval\s*\(function\s*\(p,a,c,k,e",  # Dean Edwards packer
    r"_0x[0-9a-f]{4,}",                    # obfuscator.io hex identifiers
    r"\\u[0-9a-fA-F]{4}",                  # unicode escape sequences
]


def detect_js_obfuscation(html: str) -> Dict[str, Any]:
    """
    Scan HTML content for JavaScript obfuscation indicators.

    Args:
        html: Page HTML content (pre-fetched)

    Returns:
        obfuscation_detected (bool), indicators (list), obfuscation_score (0-1)
    """
    if not html or not html.strip():
        return {
            "obfuscation_detected": False,
            "indicators": [],
            "obfuscation_score": 0.0,
            "packer_detected": False
        }

    indicators: List[str] = []
    total_weight = 0.0

    for pattern, label, weight in _OBF_PATTERNS:
        if re.search(pattern, html, re.IGNORECASE):
            indicators.append(label)
            total_weight += weight

    # Check packer markers
    packer_detected = any(re.search(p, html, re.IGNORECASE) for p in _PACKER_MARKERS)
    if packer_detected:
        indicators.append("javascript_packer")
        total_weight += 0.40

    obfuscation_score = round(min(total_weight, 1.0), 3)
    obfuscation_detected = obfuscation_score >= 0.20 or packer_detected

    if obfuscation_detected:
        logger.info(
            f"JS obfuscation detected: score={obfuscation_score:.2f} "
            f"indicators={indicators}"
        )

    return {
        "obfuscation_detected": obfuscation_detected,
        "indicators": indicators,
        "obfuscation_score": obfuscation_score,
        "packer_detected": packer_detected
    }
