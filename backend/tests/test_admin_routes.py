"""Tests for /admin/* endpoints."""

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
from tests.helpers import auth_headers, make_admin, register_and_login


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


# ── Task 5.7 ──────────────────────────────────────────────────────────────────


def test_admin_audit_requires_admin_role(client):
    tokens = register_and_login(client, "reg@example.com", "correct horse battery a1")
    res = client.get("/admin/audit", headers=auth_headers(tokens))
    assert res.status_code == 403


# ── Task 5.8 ──────────────────────────────────────────────────────────────────


def test_admin_audit_returns_log_entries(client):
    admin = make_admin(client, "admin1@example.com", "correct horse battery a2")
    register_and_login(client, "target1@example.com", "correct horse battery a3")
    res = client.get("/admin/audit", headers=auth_headers(admin))
    assert res.status_code == 200
    assert len(res.json()) > 0


def test_admin_audit_filter_by_event(client):
    admin = make_admin(client, "admin2@example.com", "correct horse battery a4")
    register_and_login(client, "target2@example.com", "correct horse battery a5")
    res = client.get("/admin/audit?event=user.register_attempt", headers=auth_headers(admin))
    assert res.status_code == 200
    events = {r["event"] for r in res.json()}
    assert events == {"user.register_attempt"}


def test_admin_audit_filter_by_user_id(client):
    admin = make_admin(client, "admin3@example.com", "correct horse battery a6")
    a = register_and_login(client, "aa@example.com", "correct horse battery a7")
    register_and_login(client, "bb@example.com", "correct horse battery a8")
    uid = client.get("/auth/me", headers=auth_headers(a)).json()["id"]
    res = client.get(f"/admin/audit?user_id={uid}", headers=auth_headers(admin))
    assert res.status_code == 200
    assert all(r["user_id"] == uid for r in res.json())


def test_admin_audit_pagination(client):
    admin = make_admin(client, "admin4@example.com", "correct horse battery a9")
    for i in range(2):
        register_and_login(client, f"pg{i}@example.com", f"correct horse battery a{10 + i}")
    first = client.get("/admin/audit?limit=2&offset=0", headers=auth_headers(admin)).json()
    second = client.get("/admin/audit?limit=2&offset=2", headers=auth_headers(admin)).json()
    assert len(first) == 2 and len(second) == 2
    assert {r["id"] for r in first}.isdisjoint({r["id"] for r in second})


# ── Task 5.9 ──────────────────────────────────────────────────────────────────


def test_admin_lock_user_sets_locked_until(client):
    admin = make_admin(client, "admin5@example.com", "correct horse battery a15")
    target = register_and_login(client, "target3@example.com", "correct horse battery a16")
    uid = client.get("/auth/me", headers=auth_headers(target)).json()["id"]
    res = client.post(f"/admin/users/{uid}/lock", json={"duration_minutes": 30}, headers=auth_headers(admin))
    assert res.status_code == 200
    login = client.post("/auth/login", json={"email": "target3@example.com", "password": "correct horse battery a16"})
    assert login.status_code == 423


def test_admin_unlock_user_clears_lock_and_counter(client):
    admin = make_admin(client, "admin6@example.com", "correct horse battery a17")
    target = register_and_login(client, "target4@example.com", "correct horse battery a18")
    uid = client.get("/auth/me", headers=auth_headers(target)).json()["id"]
    client.post(f"/admin/users/{uid}/lock", json={"duration_minutes": 30}, headers=auth_headers(admin))
    res = client.post(f"/admin/users/{uid}/unlock", headers=auth_headers(admin))
    assert res.status_code == 200
    login = client.post("/auth/login", json={"email": "target4@example.com", "password": "correct horse battery a18"})
    assert login.status_code == 200


# ── Task 5.10 ─────────────────────────────────────────────────────────────────


def test_admin_disable_2fa_flips_flag_and_revokes_sessions(client):
    import pyotp

    admin = make_admin(client, "admin7@example.com", "correct horse battery a20")
    target = register_and_login(client, "target5@example.com", "correct horse battery a21")
    setup = client.post("/auth/2fa/setup", headers=auth_headers(target)).json()
    client.post("/auth/2fa/enable", json={"code": pyotp.TOTP(setup["secret"]).now()}, headers=auth_headers(target))
    uid = client.get("/auth/me", headers=auth_headers(target)).json()["id"]
    res = client.post(f"/admin/users/{uid}/disable-2fa", headers=auth_headers(admin))
    assert res.status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": target["refresh_token"]}).status_code == 401


def test_admin_endpoints_reject_regular_user(client):
    reg = register_and_login(client, "plain@example.com", "correct horse battery a22")
    assert (
        client.post(
            "/admin/users/00000000-0000-0000-0000-000000000000/lock",
            json={"duration_minutes": 10},
            headers=auth_headers(reg),
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/admin/users/00000000-0000-0000-0000-000000000000/unlock",
            headers=auth_headers(reg),
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/admin/users/00000000-0000-0000-0000-000000000000/disable-2fa",
            headers=auth_headers(reg),
        ).status_code
        == 403
    )
