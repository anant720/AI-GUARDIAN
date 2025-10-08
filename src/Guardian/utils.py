
# Guardian/utils.py

import re
from urlextract import URLExtract

# Fallback regex if urlextract fails
URL_PATTERN = re.compile(
    # This regex is improved to not include trailing punctuation.
    r'(?:https?://)?(?:www\.)?[\w\.-]+\.[\w]{2,}(?:[/\w\.-?=&%#]*)?'
)

def extract_links(text: str) -> list[str]:
    """
    Finds and returns all URLs in a given string using URLExtract for better accuracy.

    Args:
        text: The text to search for links.

    Returns:
        A list of URLs found in the text.
    """
    try:
        extractor = URLExtract()
        return extractor.find_urls(text)
    except Exception:
        # Fallback to regex if URLExtract fails
        return URL_PATTERN.findall(text)
