from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings  # loads .env early (local dev) / validates config
from app.routes.scan import router as scan_router
from app.routes.admin import router as admin_router
from app.routes.users import router as users_router
from app.routes.notifications import router as notifications_router
from app.routes.monitoring import router as monitoring_router
from app.routes.monitoring_tests import router as monitoring_tests_router
from app.routes.alerts import router as alerts_router
from app.routes.events import router as events_router
from app.logger import logger

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Startup:  init feedback DB, Phase 6 registry, Phase 7 PostgreSQL.
    Shutdown: close scheduler and DB pool cleanly.
    """
    logger.info("AI Guardian backend starting up (Signal Discovery Active)...")

    # Adaptive Behavioral Engine — SQLite feedback + history
    from app.services.behavioral_engine.feedback_collector import init_feedback_db
    await init_feedback_db()

    # Continuous Model Learning — init registry & scheduler
    from app.services.continuous_learning.model_registry import init_registry
    await init_registry()

    from app.services.continuous_learning.retrain_scheduler import scheduler
    await scheduler.start()

    # PostgreSQL pool + user/notification tables
    from app.services.database import init_phase7
    db_status = await init_phase7()
    if db_status.get("connected"):
        logger.info("PostgreSQL ready")
    else:
        logger.warning(f"PostgreSQL unavailable — {db_status.get('reason')}")

    # Core — LLM Response Cache (in-memory + Redis)
    from app.core.llm_cache import init_llm_cache
    await init_llm_cache()

    # Event Bus, Alerts & Real-Time Analytics
    from app.services.event_system import init_phase8
    await init_phase8()

    # Self-Healing & System Monitoring — init daemon
    from app.services.monitoring import init_phase9
    await init_phase9()

    logger.info("AI Guardian backend ready")
    yield

    # Shutdown
    logger.info("AI Guardian backend shutting down...")
    
    from app.services.monitoring import shutdown_phase9
    await shutdown_phase9()

    from app.services.event_system import shutdown_phase8
    await shutdown_phase8()
    
    await scheduler.stop()

    from app.services.database import shutdown_phase7
    await shutdown_phase7()


app = FastAPI(
    title="AI Guardian",
    description="AI Guardian Cybersecurity Detection Engine — Real-Time Detection with LLM Gating",
    version="3.0.0",
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(scan_router)
app.include_router(admin_router)
app.include_router(users_router)
app.include_router(notifications_router)
app.include_router(monitoring_router)
app.include_router(monitoring_tests_router)
app.include_router(alerts_router)
app.include_router(events_router)


@app.get("/")
@limiter.limit("10/minute")
def home(request: Request):
    return {
        "status":  "AI Guardian backend active",
        "version": "3.0.0",
        "core_capabilities": [
            "Signal Discovery (URL Infrastructure)",
            "Signal Discovery (Message Semantics)",
            "AI Deep-Reasoning Gating (Groq + Gemini)",
            "Threat Intelligence & RAG Retrieval",
            "Adaptive Behavioral Engine",
            "Continuous Model Learning",
            "Persistent Analytics Suite",
            "Real-Time Event Orchestrator",
            "Self-Healing & System Monitoring",
            "Automated Performance Benchmarking",
            "Core: LLM Cache (Memory+Redis), Pipeline Orchestrator"
        ]
    }


@app.get("/health")
@limiter.limit("30/minute")
def health_check(request: Request):
    from app.services.database.db import is_connected
    return {
        "status":  "ok",
        "service": "AI Guardian",
        "version": "3.0.0",
        "postgresql": "connected" if is_connected() else "not configured"
    }
