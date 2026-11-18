"""Upstash Redis REST client singleton for challenge store and similar low-latency needs.

Uses the HTTP/REST-based `upstash_redis` client (same as `services/session_store.py`)
rather than the TCP-protocol `redis` package: Vercel's `experimentalServices` Python
bundler does not include `redis` at runtime even when it's listed in requirements.txt.
"""

from __future__ import annotations

import os
from functools import lru_cache

from upstash_redis import Redis


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    """Return an upstash_redis client from KV_REST_API_URL/KV_REST_API_TOKEN.

    Tests should inject a fakeredis instance directly into ChallengeStore instead
    of relying on this function.
    """
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        raise RuntimeError("KV_REST_API_URL and KV_REST_API_TOKEN (or UPSTASH_REDIS_REST_URL/TOKEN) must be set.")
    return Redis(url=url, token=token)
