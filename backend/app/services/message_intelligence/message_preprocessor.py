import re
import unicodedata
import emoji
from typing import List, Dict, Any
from app.logger import logger

class MessagePreprocessor:
    def __init__(self):
        # Basic URL regex for extraction
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )

    def normalize_text(self, text: str) -> str:
        """
        Normalizes the text by converting to lowercase, removing emojis,
        and applying unicode normalization.
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove emojis
        text = emoji.replace_emoji(text, replace='')
        
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from message text."""
        return self.url_pattern.findall(text)

    def tokenize(self, normalized_text: str) -> List[str]:
        """Split normalized text into alphanumeric tokens."""
        # Only keep alphanumeric tokens
        tokens = re.findall(r'\b\w+\b', normalized_text)
        return tokens

    def process(self, text: str) -> Dict[str, Any]:
        """Process the message and return normalized text, tokens, and URLs."""
        if not text:
            return {
                "original": text,
                "normalized": "",
                "tokens": [],
                "extracted_urls": []
            }
            
        try:
            urls = self.extract_urls(text)
            # Remove URLs from text before further normalization
            text_without_urls = self.url_pattern.sub(' ', text)
            
            normalized = self.normalize_text(text_without_urls)
            tokens = self.tokenize(normalized)
            
            return {
                "original": text,
                "normalized": normalized,
                "tokens": tokens,
                "extracted_urls": urls
            }
        except Exception as e:
            logger.error(f"Error during message preprocessing: {e}")
            return {
                "original": text,
                "normalized": text,
                "tokens": [],
                "extracted_urls": []
            }

preprocessor = MessagePreprocessor()


def preprocess_message(text: str) -> Dict[str, Any]:
    """Public module-level function: preprocess a message."""
    return preprocessor.process(text)
