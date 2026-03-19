"""
explanation_formatter.py
────────────────────────
Cleans and formats the raw explanation string from the LLM verdict
into a polished, API-ready sentence.
"""
import re
from app.logger import logger

_MAX_LENGTH = 400


def format_explanation(raw_explanation: str) -> str:
    """
    Clean, validate, and format a raw LLM explanation string.

    Processing steps:
      1. Strip leading/trailing whitespace
      2. Remove markdown artifacts (**bold**, _italic_, `code`)
      3. Collapse multiple spaces/newlines into a single space
      4. Ensure sentence ends with punctuation
      5. Truncate to _MAX_LENGTH characters

    Args:
        raw_explanation: Raw explanation string from LLM verdict

    Returns:
        Clean, formatted explanation string
    """
    try:
        if not raw_explanation:
            return "No explanation provided."

        text = raw_explanation.strip()

        # Remove markdown formatting
        text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)   # **bold** / *italic*
        text = re.sub(r"_{1,2}(.+?)_{1,2}", r"\1", text)      # __bold__ / _italic_
        text = re.sub(r"`(.+?)`", r"\1", text)                  # `code`
        text = re.sub(r"#+\s*", "", text)                        # ## headings

        # Collapse whitespace
        text = re.sub(r"[\r\n]+", " ", text)
        text = re.sub(r"\s{2,}", " ", text).strip()

        # Ensure ends with sentence-ending punctuation
        if text and text[-1] not in ".!?":
            text += "."

        # Truncate with ellipsis if needed
        if len(text) > _MAX_LENGTH:
            text = text[:_MAX_LENGTH - 3].rstrip() + "..."

        return text

    except Exception as e:
        logger.error(f"Explanation formatter error: {e}")
        return "Unable to generate explanation."
