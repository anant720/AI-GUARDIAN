"""
gemini_provider.py
──────────────────
Google Gemini inference provider (fallback).

Model: gemini-1.5-flash
Strategy: cycle through GEMINI_API_KEY_1 / GEMINI_API_KEY_2
          on failure, tries next key before raising.
"""
import httpx
from typing import List
from app.logger import logger
from app.config import settings

_GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)


class GeminiProvider:
    """
    Google Gemini inference provider with key fallback cycling.
    """

    def __init__(self, keys: List[str], model: str, timeout: int):
        self.keys = [k for k in keys if k]
        self.model = model
        self.timeout = timeout

        if self.keys:
            logger.info(f"Gemini provider ready — {len(self.keys)} key(s), model: {self.model}")
        else:
            logger.warning("Gemini provider: no API keys configured")

    def is_available(self) -> bool:
        return len(self.keys) > 0

    async def generate(self, prompt: str) -> str:
        """
        Try each Gemini API key in order using async HTTP.
        Raises RuntimeError if all keys fail.
        """
        last_error: Exception = RuntimeError("Gemini: no keys configured")

        async with httpx.AsyncClient() as client:
            for attempt, key in enumerate(self.keys, 1):
                try:
                    logger.info(f"Gemini inference — attempt {attempt}/{len(self.keys)} (Async)")
                    url = _GEMINI_API_URL.format(model=self.model, key=key)
                    payload = {
                        "contents": [
                            {
                                "parts": [{"text": prompt}]
                            }
                        ],
                        "generationConfig": {
                            "temperature": 0.1,
                            "maxOutputTokens": 512
                        }
                    }
                    response = await client.post(url, json=payload, timeout=self.timeout)
                    response.raise_for_status()

                    data = response.json()
                    text = (
                        data["candidates"][0]["content"]["parts"][0]["text"]
                    )
                    logger.info(f"Gemini responded (attempt {attempt})")
                    return text.strip()

                except Exception as e:
                    last_error = e
                    logger.warning(f"Gemini key {attempt} failed: {type(e).__name__}: {e}")

        raise RuntimeError(f"All Gemini keys failed. Last error: {last_error}")


# ── Module-level singleton ────────────────────────────────────────────────────
gemini_provider = GeminiProvider(
    keys=settings.GEMINI_KEYS,
    model=settings.GEMINI_MODEL,
    timeout=settings.LLM_TIMEOUT_SECONDS
)


async def call_gemini(prompt: str) -> str:
    """Public function: run asynchronous inference on Gemini."""
    return await gemini_provider.generate(prompt)
