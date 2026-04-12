"""Rate limiting middleware using slowapi with Upstash Redis backend."""

from __future__ import annotations

import logging
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def _get_redis_uri() -> str | None:
    """Build a Redis URI from Upstash env vars, or return None for in-memory."""
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if url and token:
        # slowapi expects a redis:// URI; Upstash REST is not directly compatible.
        # For serverless we use the in-memory fallback; production should set RATE_LIMIT_REDIS_URL.
        return os.environ.get("RATE_LIMIT_REDIS_URL")
    return None


redis_uri = _get_redis_uri()
storage_uri = redis_uri or "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    strategy="fixed-window",
)

# ── Rate limit constants ─────────────────────────────────────────────────────
CHAT_LIMIT = "30/minute"
AUDIO_LIMIT = "30/minute"
GENERATE_LIMIT = "5/minute"
ANALYSIS_LIMIT = "10/minute"
SUGGEST_LIMIT = "20/minute"
