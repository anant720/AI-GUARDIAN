from langdetect import detect_langs
from langdetect.lang_detect_exception import LangDetectException
from typing import Dict, Any, Optional
from app.logger import logger

class LanguageDetector:
    def detect(self, text: str) -> Dict[str, Any]:
        """
        Detect the language of the provided text.
        Returns the primary language code and confidence.
        """
        if not text or not text.strip():
            return {"language": None, "confidence": 0.0}
            
        try:
            langs = detect_langs(text)
            if langs:
                # detect_langs returns a list of languages sorted by probability
                primary_lang = langs[0]
                return {
                    "language": primary_lang.lang,
                    "confidence": primary_lang.prob
                }
        except LangDetectException as e:
            logger.warning(f"Language detection failed: {e}")
        except Exception as e:
            logger.error(f"Error during language detection: {e}")
            
        return {"language": None, "confidence": 0.0}

language_detector = LanguageDetector()


def detect_language(text: str) -> Dict[str, Any]:
    """Public module-level function: detect the language of a message."""
    return language_detector.detect(text)
