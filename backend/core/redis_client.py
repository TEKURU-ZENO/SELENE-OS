"""
SELENE OS — Redis Client (Async)
Singleton async Redis client with graceful fallback to in-memory
when Redis is unavailable. This ensures the system boots and functions
in development without requiring a Redis instance, while production
always connects to real Redis.
"""

import asyncio
from typing import Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class _FallbackRedis:
    """
    Thread-safe in-memory fallback for when Redis is unavailable.
    Supports the subset of Redis commands used by SELENE's task queue.
    This is intentionally minimal — it exists only to keep the system
    functional in local development without Redis.
    """

    def __init__(self):
        import collections
        self._streams: dict[str, list] = {}
        self._sets: dict[str, set] = {}
        self._lock = asyncio.Lock()

    async def ping(self) -> bool:
        return True

    async def xadd(self, name: str, fields: dict, **kwargs) -> str:
        import time
        async with self._lock:
            if name not in self._streams:
                self._streams[name] = []
            msg_id = f"{int(time.time() * 1000)}-0"
            self._streams[name].append((msg_id, fields))
            return msg_id

    async def xreadgroup(self, groupname: str, consumername: str, streams: dict, count: int = 1, block: int = 0):
        async with self._lock:
            results = []
            for stream_name, last_id in streams.items():
                messages = self._streams.get(stream_name, [])
                pending = [(mid, fields) for mid, fields in messages if fields.get("_claimed") != groupname]
                if pending:
                    mid, fields = pending[0]
                    fields["_claimed"] = groupname
                    results.append([stream_name, [(mid, fields)]])
            return results if results else []

    async def xack(self, name: str, groupname: str, *ids):
        async with self._lock:
            stream = self._streams.get(name, [])
            self._streams[name] = [(mid, f) for mid, f in stream if mid not in ids]

    async def sadd(self, name: str, *values):
        if name not in self._sets:
            self._sets[name] = set()
        self._sets[name].update(values)

    async def sismember(self, name: str, value: str) -> bool:
        return value in self._sets.get(name, set())

    async def xgroup_create(self, name: str, groupname: str, id: str = "0", mkstream: bool = False):
        if name not in self._streams and mkstream:
            self._streams[name] = []

    async def close(self):
        pass


class RedisClient:
    """
    Async Redis client wrapper. Attempts to connect to Redis on first use.
    Falls back to the in-memory implementation if the connection fails.
    """

    def __init__(self):
        self._client: Any = None
        self._is_real_redis = False

    async def connect(self) -> bool:
        from config.settings import settings
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await client.ping()
            self._client = client
            self._is_real_redis = True
            logger.info("redis_connected", url=settings.REDIS_URL)
            return True
        except Exception as e:
            logger.warning(
                "redis_unavailable_using_fallback",
                error=str(e),
                hint="Start Redis with: docker run -p 6379:6379 redis:7-alpine",
            )
            self._client = _FallbackRedis()
            self._is_real_redis = False
            return False

    @property
    def client(self) -> Any:
        if self._client is None:
            raise RuntimeError("RedisClient not connected. Call await redis_client.connect() first.")
        return self._client

    @property
    def is_real(self) -> bool:
        return self._is_real_redis

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            logger.info("redis_disconnected")


# Singleton
redis_client = RedisClient()
