package com.aiguardian.util

object UrlExtractor {
    private val URL_REGEX = Regex(
        """(https?://[^\s<>"{}|\^`\[\]]*|www\.[^\s<>"{}|\^`\[\]]*)""",
        RegexOption.IGNORE_CASE
    )
    
    // Also catch short link patterns that might not have http:// prefix
    private val SHORT_URL_REGEX = Regex(
        """(bit\.ly|t\.co|goo\.gl|tinyurl\.com|ow\.ly|is\.gd|buff\.ly)/[A-Za-z0-9]+"""
    )

    fun extract(text: String): String? {
        URL_REGEX.find(text)?.value?.let { return it }
        SHORT_URL_REGEX.find(text)?.value?.let { return "https://$it" }
        return null
    }
}
