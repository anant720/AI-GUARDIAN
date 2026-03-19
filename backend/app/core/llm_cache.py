"""
app/core/llm_cache.py
──────────────────────
Two-tier LLM result cache with in-memory LRU (primary) and Redis (secondary).

Cache key: sha256(normalized_domain + truncated_message)[:16]
TTL: 15 minutes (configurable)

Prevents duplicate LLM calls for identical or near-identical scans.
On cache hit: saves 2-4 seconds of LLM latency.
"""
import os
import json
import time
import asyncio
from collections import OrderedDict
from typing import Any, Dict, Optional
from app.logger import logger

_TTL_SECONDS = int(os.getenv("LLM_CACHE_TTL", "900"))   # 15 min default
_MAX_MEMORY_ENTRIES = int(os.getenv("LLM_CACHE_SIZE", "500"))

# ── In-memory LRU cache ───────────────────────────────────────────────────────
_memory_cache: OrderedDict[str, tuple] = OrderedDict()  # key → (value, expires_at)
_cache_lock = asyncio.Lock()

# ── Redis client (optional) ───────────────────────────────────────────────────
_redis = None


async def init_llm_cache() -> None:
    """Try to connect to Redis. Falls back silently to in-memory only."""
    global _redis
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        logger.info("LLM Cache: Redis not configured — using in-memory LRU only")
        return
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(redis_url, decode_responses=True)
        await _redis.ping()
        logger.info("LLM Cache: Redis connected — dual-tier cache active")
    except Exception as e:
        _redis = None
        logger.warning(f"LLM Cache: Redis unavailable ({e}) — in-memory only")


async def get_cached(cache_key: str) -> Optional[Dict[str, Any]]:
    """Return cached LLM result or None if not found / expired."""
    # 1. Check in-memory first (fastest)
    async with _cache_lock:
        if cache_key in _memory_cache:
            value, expires_at = _memory_cache[cache_key]
            if time.monotonic() < expires_at:
                _memory_cache.move_to_end(cache_key)   # LRU refresh
                logger.debug(f"LLM Cache HIT (memory): {cache_key}")
                return value
            else:
                del _memory_cache[cache_key]

    # 2. Check Redis
    if _redis:
        try:
            raw = await _redis.get(f"llm_cache:{cache_key}")
            if raw:
                result = json.loads(raw)
                # Backfill in-memory
                await _store_memory(cache_key, result)
                logger.debug(f"LLM Cache HIT (redis): {cache_key}")
                return result
        except Exception as e:
            logger.warning(f"LLM Cache Redis read error: {e}")

    return None


async def store_cached(cache_key: str, result: Dict[str, Any]) -> None:
    """Store LLM result in both tiers."""
    await _store_memory(cache_key, result)
    if _redis:
        try:
            await _redis.setex(
                f"llm_cache:{cache_key}",
                _TTL_SECONDS,
                json.dumps(result, default=str)
            )
        except Exception as e:
            logger.warning(f"LLM Cache Redis write error: {e}")


async def _store_memory(cache_key: str, result: Dict[str, Any]) -> None:
    """Store in in-memory LRU with TTL + eviction."""
    async with _cache_lock:
        if len(_memory_cache) >= _MAX_MEMORY_ENTRIES:
            _memory_cache.popitem(last=False)   # evict LRU
        _memory_cache[cache_key] = (result, time.monotonic() + _TTL_SECONDS)
        _memory_cache.move_to_end(cache_key)


def get_cache_stats() -> Dict[str, Any]:
    """Return current cache statistics for monitoring."""
    return {
        "memory_entries": len(_memory_cache),
        "max_entries": _MAX_MEMORY_ENTRIES,
        "ttl_seconds": _TTL_SECONDS,
        "redis_connected": _redis is not None,
    }
