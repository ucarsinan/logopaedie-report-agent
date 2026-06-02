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


def test_challenge_store_setex_ttl_matches_argument():
    """``put`` must SETEX the challenge with exactly the TTL it was called
    with. ``fakeredis`` doesn't expose time-travel, so we verify the contract
    by reading back the remaining TTL Redis recorded for the key. A 5-second
    drift tolerance covers wall-clock jitter between SET and TTL (fakeredis
    rounds to whole seconds)."""
    client = fakeredis.FakeStrictRedis(decode_responses=True)
    store = ChallengeStore(client)
    store.put("ttl-key", "user-uuid-ttl", ttl_seconds=300)
    raw_ttl = client.ttl(f"{ChallengeStore.PREFIX}ttl-key")
    assert 295 <= raw_ttl <= 300, f"expected ~300s TTL, got {raw_ttl}"
    # Non-default TTL must propagate through too.
    store.put("ttl-key-short", "user-uuid-short", ttl_seconds=30)
    short_ttl = client.ttl(f"{ChallengeStore.PREFIX}ttl-key-short")
    assert 25 <= short_ttl <= 30, f"expected ~30s TTL, got {short_ttl}"


def test_challenge_store_two_challenges_same_user_are_independent(store):
    """Two concurrent login attempts by the same user must each get their
    own challenge_id and consume independently. The store is keyed by
    challenge_id, not user_id, so collisions only happen if a caller reuses
    the same challenge_id — which is a caller bug, not a store bug. This
    test pins the no-collision behavior for the legitimate case."""
    store.put("chal-a", "user-uuid-shared", ttl_seconds=300)
    store.put("chal-b", "user-uuid-shared", ttl_seconds=300)
    # Both must be independently retrievable.
    assert store.consume("chal-a") == "user-uuid-shared"
    assert store.consume("chal-b") == "user-uuid-shared"
    # Both must now be gone (GETDEL atomicity holds per challenge_id).
    assert store.consume("chal-a") is None
    assert store.consume("chal-b") is None
