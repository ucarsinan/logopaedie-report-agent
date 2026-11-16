"""Guard: the test suite must never reach the network through ``redis_client``.

``redis_client.get_redis()`` returns an Upstash REST client. In tests it would
POST to the fake ``KV_REST_API_URL`` from ``conftest._set_env``; every failed
call sleeps ``rest_retry_interval`` (3 s) before the auth middleware falls
open, which turned each authenticated request into a 3 s stall and made the
pre-push hook look hung. ``conftest._offline_redis`` swaps in fakeredis; these
tests fail if that wiring regresses.
"""

from __future__ import annotations

import fakeredis


def test_access_token_blocklist_uses_fake_redis(monkeypatch):
    # The blocklist TTL comes from TokenService, which requires a JWT secret.
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-real-0123456789abcdef")
    from dependencies import get_access_token_blocklist

    assert isinstance(get_access_token_blocklist()._r, fakeredis.FakeStrictRedis)


def test_challenge_store_uses_fake_redis():
    from dependencies import get_challenge_store

    assert isinstance(get_challenge_store()._client, fakeredis.FakeStrictRedis)
