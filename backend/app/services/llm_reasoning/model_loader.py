"""
model_loader.py
───────────────
Singleton LLM backend loader.

Priority:
  1. Ollama  (local, no API key needed)  — tried first
  2. OpenAI  (cloud fallback)            — used when Ollama is unreachable

Both backends expose the same interface:  generate(prompt) -> str
"""
import os
import httpx
from typing import Optional
from app.logger import logger
from app.config import settings


class OllamaBackend:
    """Calls a locally-running Ollama server via its REST API."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS
        self.available = self._probe()

    def _probe(self) -> bool:
        """Check whether Ollama is reachable at startup."""
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=3)
            if r.status_code == 200:
                logger.info(f"Ollama reachable at {self.base_url} — model: {self.model}")
                return True
        except Exception:
            pass
        logger.warning("Ollama not reachable — will use cloud fallback if configured")
        return False

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 512}
        }
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json().get("response", "")


class OpenAIBackend:
    """Calls OpenAI's chat completion API as a cloud fallback."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS
        self.available = bool(self.api_key and self.api_key != "your_key_here")
        if self.available:
            logger.info(f"OpenAI backend configured — model: {self.model}")
        else:
            logger.info("OpenAI API key not set — cloud fallback disabled")

    def generate(self, prompt: str) -> str:
        import openai  # lazy import — not required if unused
        client = openai.OpenAI(api_key=self.api_key, timeout=self.timeout)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=512
        )
        return response.choices[0].message.content or ""


class LLMModel:
    """
    Singleton LLM model.
    Selects backend at startup based on LLM_MODE config and availability.
    """

    def __init__(self):
        self._ollama = OllamaBackend()
        self._openai = OpenAIBackend()
        self._active = self._select_backend()

    def _select_backend(self) -> Optional[object]:
        mode = settings.LLM_MODE.lower()
        if mode == "ollama":
            return self._ollama if self._ollama.available else None
        if mode == "openai":
            return self._openai if self._openai.available else None
        # "auto" — prefer Ollama, fall back to OpenAI
        if self._ollama.available:
            return self._ollama
        if self._openai.available:
            return self._openai
        return None

    def is_available(self) -> bool:
        return self._active is not None

    def generate(self, prompt: str) -> str:
        if not self._active:
            raise RuntimeError("No LLM backend available (Ollama unreachable and OpenAI not configured)")
        return self._active.generate(prompt)


# ── Singleton instance (loaded once at startup) ──────────────────────────────
llm_model = LLMModel()
