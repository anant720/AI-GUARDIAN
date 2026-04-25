"""
groq_provider.py
────────────────
Groq cloud inference provider.

Model: llama3-8b-8192 (fast, free tier supported)
Strategy: round-robin across GROQ_API_KEY_1 / GROQ_API_KEY_2
          tries each key in order; raises only if all keys fail.
"""
import httpx
import threading
from typing import List
from app.logger import logger
from app.config import settings

_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider:
    """
    Groq inference provider with round-robin key rotation.
    Thread-safe key cycling using a lock + index counter.
    """

    def __init__(self, keys: List[str], model: str, timeout: int):
        self.keys = [k for k in keys if k]   # drop None / empty
        self.model = model
        self.timeout = timeout
        self._lock = threading.Lock()
        self._index = 0

        if self.keys:
            logger.info(f"Groq provider ready — {len(self.keys)} key(s), model: {self.model}")
        else:
            logger.warning("Groq provider: no API keys configured")

    def _next_key(self) -> str:
        """Return next key in round-robin order (thread-safe)."""
        with self._lock:
            key = self.keys[self._index % len(self.keys)]
            self._index += 1
        return key

    def is_available(self) -> bool:
        return len(self.keys) > 0

    async def generate(self, prompt: str) -> str:
        """
        Try each Groq key in round-robin order using async HTTP.
        Raises RuntimeError if all keys fail.
        """
        last_error: Exception = RuntimeError("Groq: no keys configured")

        async with httpx.AsyncClient() as client:
            for attempt, _ in enumerate(self.keys, 1):
                key = _next_key_for(self, attempt)
                try:
                    logger.info(f"Groq inference — attempt {attempt}/{len(self.keys)} (Async)")
                    response = await client.post(
                        _GROQ_API_URL,
                        headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.1,
                            "max_tokens": 512
                        },
                        timeout=self.timeout
                    )
                    response.raise_for_status()
                    text = response.json()["choices"][0]["message"]["content"]
                    logger.info(f"Groq responded (attempt {attempt})")
                    return text.strip()

                except Exception as e:
                    last_error = e
                    logger.warning(f"Groq key {attempt} failed: {type(e).__name__}: {e}")

        raise RuntimeError(f"All Groq keys failed. Last error: {last_error}")


def _next_key_for(provider: GroqProvider, attempt: int) -> str:
    """Extract key by attempt index (avoids mutating internal counter twice)."""
    return provider.keys[(attempt - 1) % len(provider.keys)]


# ── Module-level singleton ────────────────────────────────────────────────────
groq_provider = GroqProvider(
    keys=settings.GROQ_KEYS,
    model=settings.GROQ_MODEL,
    timeout=settings.LLM_TIMEOUT_SECONDS
)


async def call_groq(prompt: str) -> str:
    """Public function: run asynchronous inference on Groq."""
    return await groq_provider.generate(prompt)
