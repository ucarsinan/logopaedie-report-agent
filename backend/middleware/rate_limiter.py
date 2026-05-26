"""Rate limiting middleware using slowapi with Upstash Redis backend."""

from __future__ import annotations

import logging
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def _resolve_storage_uri() -> str:
    """Resolve a distributed rate-limit storage URI, or in-memory as a last resort.

    Upstash exposes a Redis-protocol TLS endpoint (rediss://...) via REDIS_URL/KV_URL,
    which slowapi's `limits` backend speaks natively. In-memory storage is per-instance
    and ephemeral on serverless (resets on cold start, not shared across instances), so
    it must only ever be the fallback for local/test runs.
    """
    return (
        os.environ.get("RATE_LIMIT_REDIS_URL")
        or os.environ.get("REDIS_URL")
        or os.environ.get("KV_URL")
        or "memory://"
    )


def client_ip_key(request) -> str:  # Starlette Request (duck-typed)
    """Identify the client by its real IP, honoring the Vercel proxy's X-Forwarded-For.

    Behind a proxy, request.client.host is the proxy IP — the same for every visitor —
    which would make a single shared rate-limit bucket. The first hop in X-Forwarded-For
    is the originating client.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return get_remote_address(request)


storage_uri = _resolve_storage_uri()
if storage_uri == "memory://":
    logger.warning("Rate limiter using in-memory storage — not distributed; set REDIS_URL in production.")

limiter = Limiter(
    key_func=client_ip_key,
    storage_uri=storage_uri,
    strategy="fixed-window",
)

# ── Rate limit constants ─────────────────────────────────────────────────────
CHAT_LIMIT = "30/minute"
AUDIO_LIMIT = "30/minute"
GENERATE_LIMIT = "5/minute"
ANALYSIS_LIMIT = "10/minute"
SUGGEST_LIMIT = "20/minute"
