"""Shared fixtures for backend tests."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend/ is on sys.path so imports resolve the same way as at runtime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset in-memory rate limiter storage before each test."""
    from middleware.rate_limiter import limiter

    limiter._storage.reset()
    yield
    limiter._storage.reset()


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """Set required env vars for testing."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    monkeypatch.delenv("API_KEY", raising=False)
    # Fake Redis credentials so session_store doesn't crash on import
    monkeypatch.setenv("KV_REST_API_URL", "https://fake-redis.test")
    monkeypatch.setenv("KV_REST_API_TOKEN", "fake-token")


@pytest.fixture()
def mock_redis():
    """Mock the Redis client used by session_store."""
    mock = MagicMock()
    mock.set = MagicMock(return_value=None)
    mock.get = MagicMock(return_value=None)
    mock.delete = MagicMock(return_value=None)
    mock.scan = MagicMock(return_value=(0, []))
    with patch("services.session_store._get_redis", return_value=mock):
        yield mock


@pytest.fixture()
def mock_groq():
    """Patch GroqService methods on the singleton instances in dependencies."""
    # Patch at the module path used at runtime (without backend. prefix)
    with (
        patch("services.groq_client.GroqService.chat_completion", new_callable=AsyncMock) as chat_mock,
        patch("services.groq_client.GroqService.json_completion", new_callable=AsyncMock) as json_mock,
        patch("services.groq_client.GroqService.transcribe_audio", new_callable=AsyncMock) as transcribe_mock,
    ):
        yield {
            "chat": chat_mock,
            "json": json_mock,
            "transcribe": transcribe_mock,
        }


@pytest.fixture()
def client(mock_groq, mock_redis):
    """Create a TestClient with mocked Groq service and Redis."""
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def session_id(client, mock_groq, mock_redis):
    """Create a session and return its ID."""
    mock_groq["chat"].return_value = "Willkommen! Welchen Berichtstyp möchten Sie erstellen?"
    # Mock Redis.get to return the session data after creation
    _stored = {}

    def fake_set(key, value, **kwargs):
        _stored[key] = value

    def fake_get(key):
        return _stored.get(key)

    mock_redis.set = MagicMock(side_effect=fake_set)
    mock_redis.get = MagicMock(side_effect=fake_get)

    res = client.post("/sessions")
    assert res.status_code == 200
    return res.json()["session_id"]
