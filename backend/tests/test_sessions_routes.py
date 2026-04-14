"""Tests for GET /auth/sessions and DELETE /auth/sessions/{id}."""

from __future__ import annotations

import fakeredis
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from services.audit_service import AuditService
from services.challenge_store import ChallengeStore
from services.email_service import FakeEmailService
from services.password_service import PasswordService
from services.token_service import TokenService
from services.totp_service import TOTPService
from tests.helpers import auth_headers, register_and_login


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
    monkeypatch.setenv("SESSION_ENCRYPTION_KEY", Fernet.generate_key().decode())
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)

    fake_email = FakeEmailService()
    fake_redis_client = fakeredis.FakeStrictRedis(decode_responses=True)
    challenge_store = ChallengeStore(fake_redis_client)
    totp_svc = TOTPService()

    from services.auth_service import AuthService

    svc = AuthService(
        password=PasswordService(),
        tokens=TokenService(),
        email=fake_email,
        audit=AuditService(),
        totp=totp_svc,
        challenges=challenge_store,
    )

    from database import get_db
    from dependencies import get_auth_service, get_challenge_store, get_email_service, get_totp_service
    from main import app

    def _db_override():
        with Session(eng) as db:
            yield db

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_auth_service] = lambda: svc
    app.dependency_overrides[get_email_service] = lambda: fake_email
    app.dependency_overrides[get_totp_service] = lambda: totp_svc
    app.dependency_overrides[get_challenge_store] = lambda: challenge_store

    tc = TestClient(app)
    tc.email_svc = fake_email  # type: ignore[attr-defined]
    tc.engine = eng  # type: ignore[attr-defined]
    yield tc
    app.dependency_overrides.clear()


# ── Task 5.1 ──────────────────────────────────────────────────────────────────


def test_sessions_list_excludes_revoked(client):
    tokens = register_and_login(client, "sess1@example.com", "correct horse battery s1")
    second = client.post(
        "/auth/login", json={"email": "sess1@example.com", "password": "correct horse battery s1"}
    ).json()
    client.post("/auth/logout", json={"refresh_token": second["refresh_token"]})
    res = client.get("/auth/sessions", headers=auth_headers(tokens))
    assert res.status_code == 200
    sessions = res.json()
    assert len(sessions) == 1
    assert all(s.get("revoked_at") is None for s in sessions)


# ── Task 5.2 ──────────────────────────────────────────────────────────────────


def test_sessions_list_marks_current_session(client):
    tokens = register_and_login(client, "sess2@example.com", "correct horse battery s2")
    client.post("/auth/login", json={"email": "sess2@example.com", "password": "correct horse battery s2"})
    res = client.get("/auth/sessions", headers=auth_headers(tokens))
    sessions = res.json()
    assert any(s["is_current"] for s in sessions)
    assert sum(1 for s in sessions if s["is_current"]) == 1


# ── Task 5.3 ──────────────────────────────────────────────────────────────────


def test_sessions_list_scoped_to_user(client):
    a = register_and_login(client, "usera@example.com", "correct horse battery s3")
    b = register_and_login(client, "userb@example.com", "correct horse battery s4")
    res_a = client.get("/auth/sessions", headers=auth_headers(a)).json()
    res_b = client.get("/auth/sessions", headers=auth_headers(b)).json()
    assert len(res_a) == 1
    assert len(res_b) == 1
    assert res_a[0]["id"] != res_b[0]["id"]


# ── Task 5.4 ──────────────────────────────────────────────────────────────────


def test_sessions_delete_own_session(client):
    a = register_and_login(client, "del1@example.com", "correct horse battery s5")
    b = client.post("/auth/login", json={"email": "del1@example.com", "password": "correct horse battery s5"}).json()
    sessions = client.get("/auth/sessions", headers=auth_headers(a)).json()
    other = next(s for s in sessions if not s["is_current"])
    res = client.delete(f"/auth/sessions/{other['id']}", headers=auth_headers(a))
    assert res.status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": b["refresh_token"]}).status_code == 401


# ── Task 5.5 ──────────────────────────────────────────────────────────────────


def test_sessions_delete_other_users_session_404(client):
    a = register_and_login(client, "own1@example.com", "correct horse battery s6")
    b = register_and_login(client, "own2@example.com", "correct horse battery s7")
    b_sessions = client.get("/auth/sessions", headers=auth_headers(b)).json()
    b_id = b_sessions[0]["id"]
    res = client.delete(f"/auth/sessions/{b_id}", headers=auth_headers(a))
    assert res.status_code == 404


def test_sessions_delete_nonexistent_session_404(client):
    a = register_and_login(client, "ghost@example.com", "correct horse battery s8")
    res = client.delete("/auth/sessions/00000000-0000-0000-0000-000000000000", headers=auth_headers(a))
    assert res.status_code == 404


# ── Task 5.6 ──────────────────────────────────────────────────────────────────


def test_sessions_delete_current_session_flag_in_response(client):
    a = register_and_login(client, "self@example.com", "correct horse battery s9")
    sessions = client.get("/auth/sessions", headers=auth_headers(a)).json()
    current = next(s for s in sessions if s["is_current"])
    res = client.delete(f"/auth/sessions/{current['id']}", headers=auth_headers(a))
    assert res.status_code == 200
    assert res.json()["current_session_revoked"] is True
