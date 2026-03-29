"""Tests for in-memory session store."""

import time
from unittest.mock import patch

from backend.services.session_store import Session, SessionStore


def test_create_and_get():
    store = SessionStore()
    session = store.create()
    assert isinstance(session, Session)
    assert store.get(session.session_id) is session


def test_get_nonexistent():
    store = SessionStore()
    assert store.get("does-not-exist") is None


def test_expired_session():
    store = SessionStore()
    session = store.create()
    # Simulate expiration
    session.created_at = time.time() - (3 * 60 * 60)  # 3h ago
    assert store.get(session.session_id) is None


def test_cleanup_expired():
    store = SessionStore()
    s1 = store.create()
    s2 = store.create()
    # Expire s1
    s1.created_at = time.time() - (3 * 60 * 60)
    # Creating a new session triggers cleanup
    s3 = store.create()
    assert store.get(s1.session_id) is None
    assert store.get(s2.session_id) is s2
    assert store.get(s3.session_id) is s3


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
