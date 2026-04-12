"""Shared fixtures for backend tests."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _set_groq_key(monkeypatch):
    """Ensure GROQ_API_KEY is set so GroqService can be instantiated."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    # Ensure API_KEY auth is disabled in tests
    monkeypatch.delenv("API_KEY", raising=False)


@pytest.fixture()
def mock_groq():
    """Patch GroqService methods to avoid real API calls."""
    with (
        patch("backend.services.groq_client.GroqService.chat_completion", new_callable=AsyncMock) as chat_mock,
        patch("backend.services.groq_client.GroqService.json_completion", new_callable=AsyncMock) as json_mock,
        patch("backend.services.groq_client.GroqService.transcribe_audio", new_callable=AsyncMock) as transcribe_mock,
    ):
        yield {
            "chat": chat_mock,
            "json": json_mock,
            "transcribe": transcribe_mock,
        }


@pytest.fixture()
def client(mock_groq):
    """Create a TestClient with mocked Groq service."""
    from fastapi.testclient import TestClient

    from backend.main import app

    return TestClient(app)


@pytest.fixture()
def session_id(client, mock_groq):
    """Create a session and return its ID."""
    mock_groq["chat"].return_value = "Willkommen! Welchen Berichtstyp möchten Sie erstellen?"
    res = client.post("/sessions")
    assert res.status_code == 200
    return res.json()["session_id"]
