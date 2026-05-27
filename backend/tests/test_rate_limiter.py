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


def test_client_key_uses_first_forwarded_ip():
    from middleware.rate_limiter import client_ip_key

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
