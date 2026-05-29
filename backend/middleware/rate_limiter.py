"""Rate limiting middleware using slowapi with Upstash Redis backend."""

from __future__ import annotations

import logging
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def _is_production() -> bool:
    """True when the app is running in a production deployment.

    Vercel sets ``VERCEL_ENV`` to ``"production" | "preview" | "development"``
    automatically; ``ENV`` is the locally-overridable fallback.
    """
    return os.environ.get("VERCEL_ENV") == "production" or os.environ.get("ENV") == "production"


def _assert_trusted_proxy_configured() -> None:
    """Fail app boot in production if X-Forwarded-For trust is not opted into.

    ``client_ip_key`` trusts the first hop in X-Forwarded-For — anyone reaching
    the app *directly* could spoof that header and bypass per-IP throttles on
    login / 2FA / password-reset / register. Vercel terminates TLS at its own
    edge and the edge's source-IP set is opaque (no stable CIDR list), so we
    don't validate the peer; instead we require an explicit ``TRUSTED_PROXY``
    opt-in env var. Operator says "yes, this app sits behind a known proxy that
    overwrites X-Forwarded-For" → header trusted. Missing in prod → boot fails
    loudly rather than silently shipping a bypass.
    """
    if _is_production() and not os.environ.get("TRUSTED_PROXY"):
        raise RuntimeError(
            "TRUSTED_PROXY must be set when VERCEL_ENV/ENV=production — "
            "the rate limiter trusts X-Forwarded-For only behind a known proxy."
        )


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
    is the originating client. Trust of that header is gated at module-import time by
    :func:`_assert_trusted_proxy_configured` — outside production we always trust it
    (no front-proxy assumption to violate).
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


_assert_trusted_proxy_configured()

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
