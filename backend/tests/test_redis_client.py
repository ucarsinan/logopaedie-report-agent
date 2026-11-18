"""Tests for the Upstash Redis client singleton.

Regression coverage for a production incident: `redis_client.py` used to do
a module-level `import redis` (the standard TCP-protocol package), which
crashed every `/auth/*` request on Vercel with
`ModuleNotFoundError: No module named 'redis'` — Vercel's `experimentalServices`
Python bundler does not ship that package even though it's in
requirements.txt. The crash happened at *module load*, on the first cold
request that needed `AuthService`, so the regression test below reloads the
module with `redis` simulated as unavailable rather than only calling
`get_redis()` against an already-imported module (which would pass trivially
either way and miss this exact failure mode).
"""

from __future__ import annotations

import importlib
import sys

import pytest
from upstash_redis import Redis as UpstashRedis

import redis_client


@pytest.fixture(autouse=True)
def _clear_cache():
    redis_client.get_redis.cache_clear()
    yield
    redis_client.get_redis.cache_clear()


def test_module_reloads_and_constructs_client_without_redis_package(monkeypatch):
    """redis_client.py must not depend on the `redis` package, even at import time."""
    monkeypatch.setitem(sys.modules, "redis", None)
    monkeypatch.setenv("KV_REST_API_URL", "https://example.upstash.io")
    monkeypatch.setenv("KV_REST_API_TOKEN", "test-token")

    importlib.reload(redis_client)
    try:
        client = redis_client.get_redis()
        assert isinstance(client, UpstashRedis)
    finally:
        redis_client.get_redis.cache_clear()
        importlib.reload(redis_client)  # restore normal state for later tests


def test_get_redis_accepts_legacy_upstash_env_var_names(monkeypatch):
    monkeypatch.delenv("KV_REST_API_URL", raising=False)
    monkeypatch.delenv("KV_REST_API_TOKEN", raising=False)
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://example.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "test-token")

    client = redis_client.get_redis()

    assert isinstance(client, UpstashRedis)


def test_get_redis_raises_when_credentials_missing(monkeypatch):
    monkeypatch.delenv("KV_REST_API_URL", raising=False)
    monkeypatch.delenv("KV_REST_API_TOKEN", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="KV_REST_API_URL"):
        redis_client.get_redis()
