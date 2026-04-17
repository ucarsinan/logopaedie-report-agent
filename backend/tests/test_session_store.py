"""Tests for Redis-backed session store."""

import json
import time
from unittest.mock import patch

from services.session_store import Session, SessionStore


class FakeRedis:
    """In-memory fake for Upstash Redis used in session store tests."""

    def __init__(self):
        self._data = {}

    def set(self, key, value, **kwargs):
        self._data[key] = value

    def get(self, key):
        return self._data.get(key)

    def delete(self, key):
        self._data.pop(key, None)

    def scan(self, cursor, match=None, count=None):
        keys = [k for k in self._data if match is None or k.startswith(match.replace("*", ""))]
        return (0, keys)


def _make_store():
    """Create a SessionStore with a fake Redis backend and encryption disabled."""
    fake = FakeRedis()
    redis_patcher = patch("services.session_store._get_redis", return_value=fake)
    fernet_patcher = patch("services.session_store._fernet", None)
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
