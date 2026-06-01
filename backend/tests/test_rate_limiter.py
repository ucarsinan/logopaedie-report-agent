"""H-1: rate limiter must use a distributed Redis backend in production and
key requests by the real client IP behind the Vercel proxy (X-Forwarded-For).
"""

from __future__ import annotations

from types import SimpleNamespace


def _fake_request(headers: dict[str, str], client_host: str | None = "127.0.0.1"):
    client = SimpleNamespace(host=client_host) if client_host else None
    return SimpleNamespace(headers=headers, client=client)


def test_storage_uri_prefers_explicit_override(monkeypatch):
    from middleware.rate_limiter import _resolve_storage_uri

    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", "rediss://override:6379")
    monkeypatch.setenv("REDIS_URL", "rediss://fallback:6379")
    assert _resolve_storage_uri() == "rediss://override:6379"


def test_storage_uri_uses_redis_url(monkeypatch):
    from middleware.rate_limiter import _resolve_storage_uri

    monkeypatch.delenv("RATE_LIMIT_REDIS_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "rediss://primary:6379")
    assert _resolve_storage_uri() == "rediss://primary:6379"


def test_storage_uri_falls_back_to_kv_url(monkeypatch):
    from middleware.rate_limiter import _resolve_storage_uri

    monkeypatch.delenv("RATE_LIMIT_REDIS_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("KV_URL", "rediss://kv:6379")
    assert _resolve_storage_uri() == "rediss://kv:6379"


def test_storage_uri_defaults_to_memory(monkeypatch):
    from middleware.rate_limiter import _resolve_storage_uri

    for var in ("RATE_LIMIT_REDIS_URL", "REDIS_URL", "KV_URL"):
        monkeypatch.delenv(var, raising=False)
    assert _resolve_storage_uri() == "memory://"


def test_client_key_uses_first_forwarded_ip(monkeypatch):
    """When TRUSTED_PROXY matches the socket IP, the first XFF hop is honored."""
    from middleware.rate_limiter import client_ip_key

    monkeypatch.setenv("TRUSTED_PROXY", "10.0.0.1")
    req = _fake_request({"x-forwarded-for": "203.0.113.7, 10.0.0.1"}, client_host="10.0.0.1")
    assert client_ip_key(req) == "203.0.113.7"


def test_client_key_falls_back_to_remote_address():
    from middleware.rate_limiter import client_ip_key

    req = _fake_request({}, client_host="198.51.100.4")
    assert client_ip_key(req) == "198.51.100.4"


def test_limiter_is_configured_to_degrade_gracefully():
    """The production limiter must tolerate a storage outage, not crash on it.

    `swallow_errors` stops a storage exception from escaping as a 500, and
    `in_memory_fallback_enabled` keeps throttling functional per-instance while
    the backend is down. Both are required to satisfy the regression below.
    """
    from middleware.rate_limiter import _build_limiter

    limiter = _build_limiter("redis://127.0.0.1:6390")
    assert limiter._in_memory_fallback_enabled is True, "in-memory fallback must be enabled"
    assert limiter._swallow_errors is True


def test_trusted_proxy_assertion_fails_boot_in_production(monkeypatch):
    """In production, missing TRUSTED_PROXY must crash the import — bypass-prevention."""
    from middleware.rate_limiter import _assert_trusted_proxy_configured

    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.delenv("TRUSTED_PROXY", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    import pytest

    with pytest.raises(RuntimeError, match="TRUSTED_PROXY"):
        _assert_trusted_proxy_configured()


def test_trusted_proxy_assertion_passes_when_opted_in(monkeypatch):
    from middleware.rate_limiter import _assert_trusted_proxy_configured

    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("TRUSTED_PROXY", "yes")
    _assert_trusted_proxy_configured()  # must not raise


def test_trusted_proxy_assertion_skipped_outside_production(monkeypatch):
    from middleware.rate_limiter import _assert_trusted_proxy_configured

    for var in ("VERCEL_ENV", "ENV"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("TRUSTED_PROXY", raising=False)
    _assert_trusted_proxy_configured()  # must not raise — dev/test mode


def test_client_key_ignores_xff_when_trusted_proxy_unset(monkeypatch):
    """S-6: with TRUSTED_PROXY unset, X-Forwarded-For must be ignored entirely.

    Without an explicit opt-in, a caller can spoof XFF to rotate per-IP rate-limit
    buckets. The key falls back to the direct socket IP regardless of XFF.
    """
    from middleware.rate_limiter import client_ip_key

    monkeypatch.delenv("TRUSTED_PROXY", raising=False)
    req = _fake_request({"x-forwarded-for": "1.2.3.4"}, client_host="127.0.0.1")
    assert client_ip_key(req) == "127.0.0.1"


def test_client_key_honors_xff_when_trusted_proxy_matches_socket(monkeypatch):
    """S-6: with TRUSTED_PROXY matching the socket IP, the first XFF hop is honored."""
    from middleware.rate_limiter import client_ip_key

    monkeypatch.setenv("TRUSTED_PROXY", "127.0.0.1")
    req = _fake_request({"x-forwarded-for": "1.2.3.4, 10.0.0.1"}, client_host="127.0.0.1")
    assert client_ip_key(req) == "1.2.3.4"


def test_client_key_ignores_xff_when_socket_is_not_trusted_proxy(monkeypatch):
    """S-6 negative path: TRUSTED_PROXY set but inbound did not arrive via that proxy.

    The request reaches the app directly (socket=127.0.0.1) instead of via the
    declared proxy (10.0.0.5), so its XFF header is untrusted — fall back to the
    socket IP.
    """
    from middleware.rate_limiter import client_ip_key

    monkeypatch.setenv("TRUSTED_PROXY", "10.0.0.5")
    req = _fake_request({"x-forwarded-for": "1.2.3.4"}, client_host="127.0.0.1")
    assert client_ip_key(req) == "127.0.0.1"


def test_429_response_includes_retry_after_header(client, mock_groq, unique_ip_headers):
    """The custom 429 handler must surface Retry-After so clients can back off.

    Login is throttled at 5/min; the 6th attempt within the same minute 429s.
    """
    mock_groq["chat"].return_value = "irrelevant"

    # Trigger the per-IP login limit (5/minute). 6th call must 429.
    for _ in range(5):
        client.post(
            "/auth/login",
            json={"email": "nope@example.com", "password": "wrong"},
            headers=unique_ip_headers,
        )
    res = client.post(
        "/auth/login",
        json={"email": "nope@example.com", "password": "wrong"},
        headers=unique_ip_headers,
    )
    assert res.status_code == 429, res.text
    retry_after = res.headers.get("retry-after")
    assert retry_after is not None, "429 response must include Retry-After header"
    assert int(retry_after) > 0


def test_chat_does_not_500_when_rate_limit_backend_fails(client, session_id, mock_groq):
    """Regression: a failing rate-limit backend 500'd every limited endpoint.

    REDIS_URL points at Upstash; a TLS/network failure there raised an uncaught
    ConnectionError before the handler ran. With graceful degradation the chat
    request must still succeed (throttling falls back to in-memory).
    """
    from middleware.rate_limiter import limiter

    mock_groq["json"].return_value = {"report_type": "befundbericht", "data": {}}
    mock_groq["chat"].return_value = "Verstanden."

    # Simulate the Upstash backend being unreachable on every limit check.
    def boom(*args, **kwargs):
        raise ConnectionError("simulated Upstash TLS failure")

    original_hit = limiter.limiter.hit
    limiter.limiter.hit = boom
    try:
        res = client.post(f"/sessions/{session_id}/chat", json={"message": "Befundbericht"})
    finally:
        limiter.limiter.hit = original_hit

    assert res.status_code != 500, res.text
    assert res.status_code == 200, res.text
