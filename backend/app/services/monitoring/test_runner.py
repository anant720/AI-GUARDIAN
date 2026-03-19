"""
phase9/test_runner.py
──────────────────────
Executes lightweight isolated tests dynamically against the backend stack
WITHOUT hitting real GPT/Groq APIs (using internal mocks or DB-only paths).
Aggregates the responses to the Report Manager.
"""
import time
import asyncio
from typing import Dict, Any, List

from app.logger import logger
from app.services.monitoring.report_manager import generate_test_report
from app.services.monitoring.error_logger import log_system_error

from app.services.database.utils import mask_message_pii
from app.services.database.db import is_connected as pg_connected
from app.services.event_system.event_bus import publish_event


async def run_full_suite() -> Dict[str, Any]:
    """Execute all test phases and generates a report."""
    logger.info("Phase 9 Test Runner: Execution Started")
    start_ts = time.time()
    results = []

    # 1. UNIT TEST
    results.append(await _test_pii_masking())
    
    # 2. INTEGRATION TEST
    results.append(await _test_db_connection())
    results.append(await _test_event_bus())
    
    # 3. Compile Report
    overall_pass = all(t["status"] == "PASS" for t in results)
    
    try:
        html_path = generate_test_report(results, overall_pass)
        logger.info(f"Phase 9 Test Runner: Completed. Report: {html_path}")
    except Exception as e:
        log_system_error("test_runner", f"Failed to generate report: {e}")

    return {
        "status": "success",
        "duration_ms": int((time.time() - start_ts) * 1000),
        "overall_status": "PASS" if overall_pass else "FAIL",
        "tests": results
    }

async def _test_pii_masking() -> dict:
    t0 = time.time()
    try:
        masked = mask_message_pii("Contact me at test@example.com")
        assert "test@example.com" not in masked
        assert "[EMAIL]" in masked
        return {
            "name": "Unit: PII Masking",
            "type": "unit",
            "status": "PASS",
            "message": "Email masked correctly",
            "duration_ms": int((time.time() - t0)*1000)
        }
    except AssertionError:
        return {
            "name": "Unit: PII Masking",
            "type": "unit",
            "status": "FAIL",
            "message": "Masking failed to redact email",
            "duration_ms": int((time.time() - t0)*1000)
        }
    except Exception as e:
        return {
            "name": "Unit: PII Masking",
            "type": "unit",
            "status": "FAIL",
            "message": str(e),
            "duration_ms": int((time.time() - t0)*1000)
        }

async def _test_db_connection() -> dict:
    t0 = time.time()
    try:
        if pg_connected():
            return {
                "name": "Integration: DB Pool",
                "type": "integration",
                "status": "PASS",
                "message": "PostgreSQL pool active",
                "duration_ms": int((time.time() - t0)*1000)
            }
        else:
            return {
                "name": "Integration: DB Pool",
                "type": "integration",
                "status": "FAIL",
                "message": "DB pool not connected",
                "duration_ms": int((time.time() - t0)*1000)
            }
    except Exception as e:
        return {
            "name": "Integration: DB Pool",
            "type": "integration",
            "status": "FAIL",
            "message": str(e),
            "duration_ms": int((time.time() - t0)*1000)
        }

async def _test_event_bus() -> dict:
    t0 = time.time()
    try:
        # Pushing a standard test event to validly test queue ingestion 
        await publish_event("system_test_ping", {"ts": time.time()})
        return {
            "name": "Integration: Event Bus",
            "type": "integration",
            "status": "PASS",
            "message": "Event pushed to pub/sub",
            "duration_ms": int((time.time() - t0)*1000)
        }
    except Exception as e:
        return {
            "name": "Integration: Event Bus",
            "type": "integration",
            "status": "FAIL",
            "message": f"Publish failed: {str(e)}",
            "duration_ms": int((time.time() - t0)*1000)
        }
