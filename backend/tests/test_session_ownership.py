"""C-1: Session ownership / Broken Object Level Authorization regression tests.

These verify that authenticated sessions are bound to their owner and cannot be
read, mutated, or generated-from by a different (or anonymous) caller, while
anonymous demo sessions stay reachable via their capability ID.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest


@pytest.fixture()
def owned_client(mock_groq, mock_redis, test_db):
    """TestClient with a controllable optional-user and an in-memory session store."""
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from database import get_db
    from dependencies import get_optional_user
    from main import app
    from models.auth import User

    _stored: dict[str, str] = {}
    mock_redis.set = MagicMock(side_effect=lambda k, v, **kw: _stored.__setitem__(k, v))
    mock_redis.get = MagicMock(side_effect=lambda k: _stored.get(k))
    mock_redis.delete = MagicMock(side_effect=lambda k: _stored.pop(k, None))

    user_a = User(id=uuid4(), email="owner_a@test.example", password_hash="x")
    user_b = User(id=uuid4(), email="other_b@test.example", password_hash="x")
    current: dict[str, User | None] = {"user": None}

    mock_groq["chat"].return_value = "Willkommen! Welchen Berichtstyp möchten Sie erstellen?"
    mock_groq["json"].return_value = {
        "report_type": "befundbericht",
        "anamnese": "x",
        "befund": "y",
        "diagnose_text": "z",
        "therapieindikation": "i",
        "therapieziele": ["t1"],
        "empfehlung": "e",
    }

    def override_optional_user():
        return current["user"]

    def override_db():
        with Session(test_db) as s:
            yield s

    app.dependency_overrides[get_optional_user] = override_optional_user
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        c.user_a = user_a
        c.user_b = user_b
        c.current = current
        yield c
    app.dependency_overrides.pop(get_optional_user, None)
    app.dependency_overrides.pop(get_db, None)


def _create_session_as(client, user) -> str:
    client.current["user"] = user
    res = client.post("/sessions")
    assert res.status_code == 200
    return res.json()["session_id"]


def test_authenticated_session_is_not_demo(owned_client):
    """A session created by an authenticated user must be marked non-demo."""
    owned_client.current["user"] = owned_client.user_a
    create = owned_client.post("/sessions").json()
    assert create["is_demo"] is False


def test_anonymous_session_is_demo(owned_client):
    """A session created without auth must be a demo session."""
    owned_client.current["user"] = None
    create = owned_client.post("/sessions").json()
    assert create["is_demo"] is True


def test_owner_can_read_own_session(owned_client):
    sid = _create_session_as(owned_client, owned_client.user_a)
    owned_client.current["user"] = owned_client.user_a
    res = owned_client.get(f"/sessions/{sid}")
    assert res.status_code == 200


def test_other_user_cannot_read_owned_session(owned_client):
    """BOLA: a different authenticated user must not read someone else's session."""
    sid = _create_session_as(owned_client, owned_client.user_a)
    owned_client.current["user"] = owned_client.user_b
    res = owned_client.get(f"/sessions/{sid}")
    assert res.status_code == 404


def test_anonymous_cannot_read_owned_session(owned_client):
    sid = _create_session_as(owned_client, owned_client.user_a)
    owned_client.current["user"] = None
    res = owned_client.get(f"/sessions/{sid}")
    assert res.status_code == 404


def test_anonymous_demo_session_stays_readable(owned_client):
    """Demo sessions (no owner) remain reachable via their capability ID."""
    sid = _create_session_as(owned_client, None)
    owned_client.current["user"] = None
    res = owned_client.get(f"/sessions/{sid}")
    assert res.status_code == 200
    assert res.json()["session_id"] == sid


def test_other_user_cannot_generate_on_owned_session(owned_client):
    """The exfiltration vector: B must not generate A's report into B's account."""
    sid = _create_session_as(owned_client, owned_client.user_a)
    # User A fills in minimal anamnesis + report type via the store directly is overkill;
    # generate works from collected_data, which is empty but should still be gated by ownership.
    owned_client.current["user"] = owned_client.user_b
    res = owned_client.post(f"/sessions/{sid}/generate", json={})
    assert res.status_code == 404


def test_other_user_cannot_chat_on_owned_session(owned_client):
    sid = _create_session_as(owned_client, owned_client.user_a)
    owned_client.current["user"] = owned_client.user_b
    res = owned_client.post(f"/sessions/{sid}/chat", json={"message": "hi"})
    assert res.status_code == 404


def test_other_user_cannot_soap_on_owned_session(owned_client):
    sid = _create_session_as(owned_client, owned_client.user_a)
    owned_client.current["user"] = owned_client.user_b
    res = owned_client.post(f"/sessions/{sid}/soap", json={})
    assert res.status_code == 404


def test_other_user_cannot_therapy_plan_on_owned_session(owned_client):
    sid = _create_session_as(owned_client, owned_client.user_a)
    owned_client.current["user"] = owned_client.user_b
    res = owned_client.post(f"/sessions/{sid}/therapy-plan", json={})
    assert res.status_code == 404
