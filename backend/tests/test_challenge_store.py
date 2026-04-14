"""Tests for the Redis-backed 2FA challenge store."""

import fakeredis
import pytest

from services.challenge_store import ChallengeStore


@pytest.fixture
def store():
    client = fakeredis.FakeStrictRedis(decode_responses=True)
    return ChallengeStore(client)


def test_put_then_consume_returns_value(store):
    store.put("abc123", "user-uuid-1", ttl_seconds=300)
    assert store.consume("abc123") == "user-uuid-1"


def test_consume_missing_returns_none(store):
    assert store.consume("nope") is None


def test_challenge_store_getdel_atomic(store):
    store.put("single", "user-uuid-42", ttl_seconds=300)
    first = store.consume("single")
    second = store.consume("single")
    assert first == "user-uuid-42"
    assert second is None
