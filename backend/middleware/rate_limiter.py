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
        os.environ.get("RATE_LIMIT_REDIS_URL") or os.environ.get("REDIS_URL") or os.environ.get("KV_URL") or "memory://"
    )


def client_ip_key(request) -> str:  # Starlette Request (duck-typed)
    """Identify the client by its real IP, honoring the Vercel proxy's X-Forwarded-For.

    Behind a proxy, request.client.host is the proxy IP — the same for every visitor —
    which would make a single shared rate-limit bucket. The first hop in X-Forwarded-For
    is the originating client.
    """
    forwarded: str = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return str(get_remote_address(request))


def _build_limiter(storage_uri: str) -> Limiter:
    """Construct the limiter with graceful degradation when storage is unreachable.

    `in_memory_fallback_enabled` keeps rate limiting *functional* (per-instance,
    in-memory) if the configured Redis backend errors out, and `swallow_errors`
    guarantees a storage failure never escapes as a 500. Without these, a TLS or
    network blip talking to Upstash would crash every rate-limited endpoint
    (chat, audio, generate) instead of merely degrading the throttle.
    """
    return Limiter(
        key_func=client_ip_key,
        storage_uri=storage_uri,
        strategy="fixed-window",
        in_memory_fallback_enabled=True,
        swallow_errors=True,
    )


storage_uri = _resolve_storage_uri()
if storage_uri == "memory://":
    logger.warning("Rate limiter using in-memory storage — not distributed; set REDIS_URL in production.")

limiter = _build_limiter(storage_uri)

# ── Rate limit constants ─────────────────────────────────────────────────────
CHAT_LIMIT = "30/minute"
AUDIO_LIMIT = "30/minute"
GENERATE_LIMIT = "5/minute"
ANALYSIS_LIMIT = "10/minute"
SUGGEST_LIMIT = "20/minute"
