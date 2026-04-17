"""Standard Redis client singleton for challenge store and similar low-latency needs."""

from __future__ import annotations

import os
from functools import lru_cache

import redis


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    """Return a redis-py client from REDIS_URL env var.

    Falls back to localhost:6379 when REDIS_URL is not set (local dev / tests).
    Tests should inject a fakeredis instance directly into ChallengeStore instead
    of relying on this function.
    """
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis.Redis.from_url(url, decode_responses=True)
