"""
phase8/event_bus.py
────────────────────
Lightweight event bus using Redis Pub/Sub, falling back to an in-memory
asyncio.Queue if Redis is unavailable or not configured.

Used to decouple Notification Logging from Alerts, Retraining, and Analytics.
"""
import os
import json
import asyncio
from typing import Callable, Awaitable, Dict, Any, List

from app.logger import logger
from app.services.event_system.utils import serialize_payload, deserialize_payload
from app.services.database.db import get_conn, is_connected

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

_REDIS_URL = os.getenv("REDIS_URL", "")
_redis_client = None

# Fallback in-memory queue
_fallback_queue: asyncio.Queue = asyncio.Queue()

# Registry of subscriber callbacks per topic
_subscribers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}

# Background task reference
_consumer_task: asyncio.Task = None


async def init_event_bus():
    """Initialise Redis connection if available."""
    global _redis_client
    if _REDIS_URL and redis:
        try:
            _redis_client = redis.from_url(_REDIS_URL, decode_responses=True)
            await _redis_client.ping()
            logger.info("Real-time Event Orchestrator: Event Bus connected to Redis")
        except Exception as e:
            logger.warning(f"Real-time Event Orchestrator: Redis connection failed ({e}), falling back to Memory Queue")
            _redis_client = None
    else:
        logger.info("Real-time Event Orchestrator: REDIS_URL not set, using Memory Queue for Event Bus")


async def close_event_bus():
    """Cleanup Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


def subscribe(topic: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
    """Register an async callback for a given topic."""
    if topic not in _subscribers:
        _subscribers[topic] = []
    _subscribers[topic].append(callback)


async def publish_event(topic: str, payload: Dict[str, Any]):
    """
    Publish an event to the bus.
    Also logs the event to PostgreSQL `event_log` table asynchronously.
    """
    # 1. Log to PostgreSQL audit trail (fire & forget logic via asyncio)
    asyncio.create_task(_log_to_db(topic, payload))

    raw_payload = serialize_payload(payload)

    # 2. Publish to Bus
    try:
        if _redis_client:
            await _redis_client.publish(topic, raw_payload)
            logger.debug(f"Event published to Redis: {topic}")
        else:
            await _fallback_queue.put((topic, raw_payload))
            logger.debug(f"Event published to Memory Queue: {topic}")
    except Exception as e:
        logger.error(f"Failed to publish event {topic}: {e}")


async def _log_to_db(event_type: str, payload: dict):
    """Internal: Save event to PostgreSQL event_log table."""
    if not is_connected():
        return
    try:
        user_id = payload.get("user_id")
        notification_id = payload.get("notification_id")
        async with get_conn() as conn:
            await conn.execute(
                """INSERT INTO event_log (event_type, user_id, notification_id, payload)
                   VALUES ($1, $2, $3, $4::jsonb)""",
                event_type, user_id, notification_id, json.dumps(payload, default=str)
            )
    except Exception as e:
        logger.error(f"Failed to log event to DB: {e}")


async def _process_payload(topic: str, raw_payload: str):
    """Internal: Route payload to registered subscribers."""
    if topic not in _subscribers:
        return

    payload = deserialize_payload(raw_payload)
    for callback in _subscribers[topic]:
        try:
            await callback(payload)
        except Exception as e:
            logger.error(f"Subscriber {callback.__name__} failed on {topic}: {e}")


async def _redis_consumer_loop():
    """Background loop listening to Redis Pub/Sub."""
    if not _redis_client:
        return
    
    pubsub = _redis_client.pubsub()
    # Subscribe to all registered topics
    topics = list(_subscribers.keys())
    if not topics:
        return
        
    await pubsub.subscribe(*topics)
    logger.info(f"Real-time Event Orchestrator: Redis consumer listening on {topics}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                topic = message["channel"]
                raw = message["data"]
                # Process concurrently
                asyncio.create_task(_process_payload(topic, raw))
    except Exception as e:
        logger.error(f"Redis consumer loop failed: {e}")
    finally:
        await pubsub.unsubscribe()
        await pubsub.close()


async def _memory_consumer_loop():
    """Background loop reading from asyncio.Queue."""
    logger.info("Real-time Event Orchestrator: Memory consumer loop started")
    while True:
        try:
            topic, raw_payload = await _fallback_queue.get()
            asyncio.create_task(_process_payload(topic, raw_payload))
            _fallback_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Memory consumer loop error: {e}")


def start_consumer():
    """Start the background consumer task (Redis or Memory)."""
    global _consumer_task
    if _redis_client:
        _consumer_task = asyncio.create_task(_redis_consumer_loop())
    else:
        _consumer_task = asyncio.create_task(_memory_consumer_loop())


async def stop_consumer():
    """Stop the background consumer task."""
    global _consumer_task
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
