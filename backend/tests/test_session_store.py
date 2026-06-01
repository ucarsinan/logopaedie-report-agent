"""Tests for Redis-backed session store."""

import json
import time
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from exceptions import SessionNotFoundError
from services.session_store import _SESSION_TIMEOUT_SECONDS, Session, SessionStore


class FakeRedis:
    """In-memory fake for Upstash Redis used in session store tests.

    ``set`` captures ``kwargs`` per-key so tests can assert the TTL header
    (``ex=…``) Upstash receives, without depending on real Redis behaviour.
    """

    def __init__(self):
        self._data = {}
        self._set_kwargs: dict[str, dict] = {}

    def set(self, key, value, **kwargs):
        self._data[key] = value
        self._set_kwargs[key] = kwargs

    def get(self, key):
        return self._data.get(key)

    def delete(self, key):
        self._data.pop(key, None)
        self._set_kwargs.pop(key, None)

    def scan(self, cursor, match=None, count=None):
        keys = [k for k in self._data if match is None or k.startswith(match.replace("*", ""))]
        return (0, keys)


def _make_store(fernet=None):
    """Create a SessionStore with a fake Redis backend.

    ``fernet=None`` disables encryption (legacy default for the original
    create/get tests). Pass a real ``Fernet`` instance to exercise the
    encrypted-at-rest path.
    """
    fake = FakeRedis()
    redis_patcher = patch("services.session_store._get_redis", return_value=fake)
    fernet_patcher = patch("services.session_store._fernet", fernet)
    redis_patcher.start()
    fernet_patcher.start()
    return SessionStore(), fake, (redis_patcher, fernet_patcher)


def test_create_and_get():
    store, _fake, patchers = _make_store()
    try:
        session = store.create()
        assert isinstance(session, Session)
        loaded = store.get(session.session_id)
        assert loaded is not None
        assert loaded.session_id == session.session_id
    finally:
        for p in patchers:
            p.stop()


def test_get_nonexistent():
    store, _fake, patchers = _make_store()
    try:
        assert store.get("does-not-exist") is None
    finally:
        for p in patchers:
            p.stop()


def test_expired_session():
    store, fake, patchers = _make_store()
    try:
        session = store.create()
        # Manipulate stored data to simulate expiration
        key = f"session:{session.session_id}"
        data = json.loads(fake.get(key))
        data["created_at"] = time.time() - (25 * 60 * 60)  # 25h ago
        fake.set(key, json.dumps(data))
        assert store.get(session.session_id) is None
    finally:
        for p in patchers:
            p.stop()


def test_session_initial_state():
    session = Session("test-123")
    assert session.session_id == "test-123"
    assert session.status == "anamnesis"
    assert session.report_type is None
    assert session.chat_history == []
    assert session.collected_data == {}
    assert session.materials == []
    assert session.generated_report is None
    assert not session.is_expired


# ── save() ───────────────────────────────────────────────────────────────────


def test_save_round_trips_mutated_state():
    """Mutations on a session must survive a save/get round-trip."""
    store, _fake, patchers = _make_store()
    try:
        session = store.create()
        session.status = "ready_for_generation"
        session.report_type = "befundbericht"
        session.collected_data = {"name": "Anna", "age": 7}
        store.save(session)
        loaded = store.get(session.session_id)
        assert loaded is not None
        assert loaded.status == "ready_for_generation"
        assert loaded.report_type == "befundbericht"
        assert loaded.collected_data == {"name": "Anna", "age": 7}
    finally:
        for p in patchers:
            p.stop()


def test_save_increments_version_and_passes_ttl_to_redis():
    """``save`` bumps ``_version`` and the Redis SET carries the configured TTL.

    The ``ex=`` header is what gives the session its 24h lifetime in Upstash;
    if it ever silently drops we'd lose the auto-expiry contract.
    """
    store, fake, patchers = _make_store()
    try:
        session = store.create()
        # ``create`` -> ``_save`` does NOT bump version (only ``save`` does).
        assert session._version == 0
        key = f"session:{session.session_id}"
        assert fake._set_kwargs[key].get("ex") == _SESSION_TIMEOUT_SECONDS

        store.save(session)
        assert session._version == 1
        # TTL must still be present on the rewritten entry.
        assert fake._set_kwargs[key].get("ex") == _SESSION_TIMEOUT_SECONDS

        store.save(session)
        assert session._version == 2
    finally:
        for p in patchers:
            p.stop()


def test_save_encrypts_payload_when_fernet_configured():
    """With Fernet active, the value stored in Redis must NOT be plaintext JSON.

    We assert two properties:
    1. The raw stored value does not start with ``{`` (the JSON sentinel) and
       does not contain the unique session-id substring in cleartext.
    2. Decrypting the stored value yields the original JSON document, so the
       ``get`` path can still hydrate the session.
    """
    fernet = Fernet(Fernet.generate_key())
    store, fake, patchers = _make_store(fernet=fernet)
    try:
        session = store.create()
        key = f"session:{session.session_id}"
        raw = fake.get(key)
        # Fernet tokens are URL-safe base64; they never start with '{'.
        assert isinstance(raw, str)
        assert not raw.startswith("{"), "stored payload looks like plaintext JSON"
        assert session.session_id not in raw, "session_id leaked into ciphertext as plaintext"
        # Round-trip via the store's own get path (uses the same _fernet patch).
        loaded = store.get(session.session_id)
        assert loaded is not None
        assert loaded.session_id == session.session_id
        # And the ciphertext does decrypt to the JSON we expect.
        decrypted = fernet.decrypt(raw.encode()).decode()
        assert decrypted.startswith("{")
        assert json.loads(decrypted)["session_id"] == session.session_id
    finally:
        for p in patchers:
            p.stop()


# ── get_or_raise() ───────────────────────────────────────────────────────────


def test_get_or_raise_returns_session_for_known_id():
    store, _fake, patchers = _make_store()
    try:
        session = store.create()
        loaded = store.get_or_raise(session.session_id)
        assert loaded.session_id == session.session_id
    finally:
        for p in patchers:
            p.stop()


def test_get_or_raise_raises_for_unknown_id():
    store, _fake, patchers = _make_store()
    try:
        with pytest.raises(SessionNotFoundError):
            store.get_or_raise("does-not-exist")
    finally:
        for p in patchers:
            p.stop()


def test_get_or_raise_raises_for_expired_session():
    """Expired sessions surface as ``SessionNotFoundError``, not silently None."""
    store, fake, patchers = _make_store()
    try:
        session = store.create()
        key = f"session:{session.session_id}"
        data = json.loads(fake.get(key))
        data["created_at"] = time.time() - (25 * 60 * 60)
        fake.set(key, json.dumps(data))
        with pytest.raises(SessionNotFoundError):
            store.get_or_raise(session.session_id)
    finally:
        for p in patchers:
            p.stop()


# ── get_authorized() ─────────────────────────────────────────────────────────


def test_get_authorized_returns_session_for_owner():
    store, _fake, patchers = _make_store()
    try:
        session = store.create()
        session.user_id = "owner-uuid"
        store.save(session)
        loaded = store.get_authorized(session.session_id, "owner-uuid")
        assert loaded.session_id == session.session_id
    finally:
        for p in patchers:
            p.stop()


def test_get_authorized_raises_for_non_owner():
    """A different user must see the same error as a missing session.

    The error type is ``SessionNotFoundError`` by design — never leak the
    existence of someone else's session to a non-owner.
    """
    store, _fake, patchers = _make_store()
    try:
        session = store.create()
        session.user_id = "owner-uuid"
        store.save(session)
        with pytest.raises(SessionNotFoundError):
            store.get_authorized(session.session_id, "different-user-uuid")
        # Anonymous (None) also blocked for an owned session.
        with pytest.raises(SessionNotFoundError):
            store.get_authorized(session.session_id, None)
    finally:
        for p in patchers:
            p.stop()


def test_get_authorized_allows_anonymous_demo_session():
    """A demo session has ``user_id is None`` and is reachable by anyone holding the id."""
    store, _fake, patchers = _make_store()
    try:
        session = store.create()
        # session.user_id stays None (default) — anonymous demo session.
        assert session.user_id is None
        loaded = store.get_authorized(session.session_id, None)
        assert loaded.session_id == session.session_id
        # Even a caller with a user_id can grab an unowned demo session.
        loaded2 = store.get_authorized(session.session_id, "some-user-uuid")
        assert loaded2.session_id == session.session_id
    finally:
        for p in patchers:
            p.stop()
