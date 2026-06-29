"""Tests for the per-user access-token revocation blocklist (S-7)."""

from __future__ import annotations

import time

import fakeredis
import pytest

from services.access_token_blocklist import AccessTokenBlocklist


@pytest.fixture
def redis_client() -> fakeredis.FakeStrictRedis:
    return fakeredis.FakeStrictRedis(decode_responses=True)


@pytest.fixture
def blocklist(redis_client: fakeredis.FakeStrictRedis) -> AccessTokenBlocklist:
    return AccessTokenBlocklist(redis_client, ttl_seconds=900)


def test_revoke_all_for_user_writes_setex_with_now_value(
    blocklist: AccessTokenBlocklist, redis_client: fakeredis.FakeStrictRedis
) -> None:
    """revoke_all_for_user writes SETEX with value == now (within 2s) and the configured TTL."""
    before = int(time.time())
    blocklist.revoke_all_for_user("user-1")
    after = int(time.time())

    stored = redis_client.get(AccessTokenBlocklist._key("user-1"))
    assert stored is not None
    assert before - 2 <= int(stored) <= after + 2

    # TTL must match the configured access-token lifetime
    ttl = redis_client.ttl(AccessTokenBlocklist._key("user-1"))
    assert 0 < ttl <= 900


def test_is_token_revoked_returns_false_when_key_absent(
    blocklist: AccessTokenBlocklist,
) -> None:
    """Common path: no cutoff is set → token is not revoked."""
    assert blocklist.is_token_revoked("user-1", token_iat=int(time.time())) is False


def test_is_token_revoked_true_when_iat_below_cutoff(
    blocklist: AccessTokenBlocklist,
) -> None:
    """An access token with `iat < cutoff` must be considered revoked."""
    blocklist.revoke_all_for_user("user-1")
    # Token issued 60s before the cutoff
    old_iat = int(time.time()) - 60
    assert blocklist.is_token_revoked("user-1", token_iat=old_iat) is True


def test_is_token_revoked_true_when_iat_equals_cutoff(
    blocklist: AccessTokenBlocklist, redis_client: fakeredis.FakeStrictRedis
) -> None:
    """Same-second tokens must be revoked at the inclusive cutoff boundary."""
    cutoff = int(time.time())
    redis_client.setex(AccessTokenBlocklist._key("user-1"), 900, str(cutoff))
    assert blocklist.is_token_revoked("user-1", token_iat=cutoff) is True


def test_is_token_revoked_false_when_iat_after_cutoff(
    blocklist: AccessTokenBlocklist,
) -> None:
    """A fresh access token (iat > cutoff) must still be accepted."""
    blocklist.revoke_all_for_user("user-1")
    future_iat = int(time.time()) + 60
    assert blocklist.is_token_revoked("user-1", token_iat=future_iat) is False


def test_garbled_redis_value_fails_open(
    blocklist: AccessTokenBlocklist, redis_client: fakeredis.FakeStrictRedis
) -> None:
    """A non-integer cutoff value (corruption / wrong key collision) must
    not 500 every authenticated request; fail open instead."""
    redis_client.setex(AccessTokenBlocklist._key("user-1"), 900, "not-a-number")
    assert blocklist.is_token_revoked("user-1", token_iat=int(time.time())) is False


def test_isolation_between_users(blocklist: AccessTokenBlocklist) -> None:
    """Revoking user A must not affect user B."""
    blocklist.revoke_all_for_user("user-a")
    old_iat = int(time.time()) - 60
    assert blocklist.is_token_revoked("user-a", token_iat=old_iat) is True
    assert blocklist.is_token_revoked("user-b", token_iat=old_iat) is False
