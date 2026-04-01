"""Redis client for caching and session memory."""
import json
from typing import Optional, Any
import redis.asyncio as redis
from core.config import settings

_redis_client: Optional[redis.Redis] = None


async def init_redis():
    global _redis_client
    try:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await _redis_client.ping()
    except Exception:
        # Fall back to in-memory dict if Redis not available
        _redis_client = None


async def get_redis() -> Optional[redis.Redis]:
    return _redis_client


# In-memory fallback when Redis unavailable
_memory_store: dict = {}


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    serialized = json.dumps(value)
    if _redis_client:
        await _redis_client.setex(key, ttl, serialized)
    else:
        _memory_store[key] = serialized


async def cache_get(key: str) -> Optional[Any]:
    if _redis_client:
        val = await _redis_client.get(key)
    else:
        val = _memory_store.get(key)
    return json.loads(val) if val else None


async def cache_delete(key: str) -> None:
    if _redis_client:
        await _redis_client.delete(key)
    else:
        _memory_store.pop(key, None)


async def session_set(session_id: str, data: dict, ttl: int = 3600) -> None:
    await cache_set(f"session:{session_id}", data, ttl)


async def session_get(session_id: str) -> dict:
    return await cache_get(f"session:{session_id}") or {}
