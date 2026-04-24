import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "AI_GUARDIAN")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    MAX_URL_LENGTH: int = int(os.getenv("MAX_URL_LENGTH", "2000"))

    # Message Intelligence
    INTENT_MODEL: str = os.getenv("INTENT_MODEL", "distilbert-base-uncased")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    SUPPORTED_LANGUAGES: List[str] = ["en", "hi", "es", "ar", "fr"]

    # ── Phase 3: LLM Reasoning ────────────────────────────────────────────────
    # Primary provider: Groq (fast, free tier)
    # Fallback provider: Gemini (Google)
    # Both use multiple keys with round-robin / cycling rotation

    # Groq — llama3-8b-8192
    GROQ_KEYS: List[str] = [
        k for k in [
            os.getenv("GROQ_API_KEY_1"),
            os.getenv("GROQ_API_KEY_2"),
            os.getenv("GROQ_API_KEY_3"),
        ] if k
    ]
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Gemini — gemini-1.5-flash
    GEMINI_KEYS: List[str] = [
        k for k in [
            os.getenv("GEMINI_API_KEY_1"),
            os.getenv("GEMINI_API_KEY_2"),
            os.getenv("GEMINI_API_KEY_3"),
        ] if k
    ]
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Ollama (optional local inference, lowest priority)
    LLM_MODE: str = os.getenv("LLM_MODE", "auto")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral")

    # OpenAI (legacy optional fallback)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "your_key_here")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    # Shared LLM timeout
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "15"))

    # ── Phase 4: Threat Intelligence ─────────────────────────────────────────
    ABUSEIPDB_API_KEY: str = os.getenv("ABUSEIPDB_API_KEY", "")
    GOOGLE_SAFE_BROWSING_KEY: str = os.getenv("GOOGLE_SAFE_BROWSING_KEY", "")

    # ── Phase 4: RAG Knowledge Layer ──────────────────────────────────────────
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", os.path.join("data", "chroma_db"))
    PHISHING_KNOWLEDGE_PATH: str = os.getenv(
        "PHISHING_KNOWLEDGE_PATH", os.path.join("data", "phishing_knowledge.json")
    )

    # ── Phase 6: Continuous Learning & Fine-Tuning ────────────────────────────
    FINETUNE_PROVIDER:      str  = os.getenv("FINETUNE_PROVIDER",      "openai")
    FINETUNE_BASE_MODEL:    str  = os.getenv("FINETUNE_BASE_MODEL",    "gpt-3.5-turbo")
    FINETUNE_MAX_EXAMPLES:  int  = int(os.getenv("FINETUNE_MAX_EXAMPLES", "500"))
    FINETUNE_DRY_RUN:       bool = os.getenv("FINETUNE_DRY_RUN", "true").lower() != "false"

    RETRAIN_SCHEDULE_CRON:      str  = os.getenv("RETRAIN_SCHEDULE_CRON", "0 2 * * 0")
    RETRAIN_MIN_FEEDBACK:       int  = int(os.getenv("RETRAIN_MIN_FEEDBACK", "20"))
    RETRAIN_SCHEDULER_ENABLED:  bool = os.getenv("RETRAIN_SCHEDULER_ENABLED", "false").lower() == "true"

    # ── Phase 7: User Auth & PostgreSQL Analytics ───────────────────────────
    DATABASE_URL:      str = os.getenv("DATABASE_URL",      "")
    JWT_SECRET_KEY:    str = os.getenv("JWT_SECRET_KEY",    "")
    JWT_EXPIRE_HOURS:  int = int(os.getenv("JWT_EXPIRE_HOURS", "12"))


settings = Settings()
