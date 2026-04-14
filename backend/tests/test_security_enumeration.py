import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from services.audit_service import AuditService
from services.auth_service import AuthService
from services.email_service import FakeEmailService
from services.password_service import PasswordService
from services.token_service import TokenService


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    fake_email = FakeEmailService()
    svc = AuthService(password=PasswordService(), tokens=TokenService(), email=fake_email, audit=AuditService())

    from database import get_db
    from dependencies import get_auth_service, get_email_service
    from main import app

    def _db_override():
        with Session(eng) as db:
            yield db

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_auth_service] = lambda: svc
    app.dependency_overrides[get_email_service] = lambda: fake_email
    yield TestClient(app), fake_email
    app.dependency_overrides.clear()


def test_register_and_duplicate_return_same_shape(client):
    c, _ = client
    r1 = c.post("/auth/register", json={"email": "a@example.com", "password": "longpassword12"})
    r2 = c.post("/auth/register", json={"email": "a@example.com", "password": "longpassword12"})
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()


def test_reset_request_and_unknown_return_same_shape(client):
    c, email = client
    c.post("/auth/register", json={"email": "x@example.com", "password": "longpassword12"})
    c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
    r_known = c.post("/auth/password/reset/request", json={"email": "x@example.com"})
    r_unknown = c.post("/auth/password/reset/request", json={"email": "ghost@example.com"})
    assert r_known.status_code == r_unknown.status_code == 200
    assert r_known.json() == r_unknown.json()


def test_login_wrong_email_vs_wrong_password_same_shape(client):
    c, email = client
    c.post("/auth/register", json={"email": "t@example.com", "password": "longpassword12"})
    c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
    r_wrong_email = c.post("/auth/login", json={"email": "no@example.com", "password": "longpassword12"})
    r_wrong_pw = c.post("/auth/login", json={"email": "t@example.com", "password": "wrongpassword12"})
    assert r_wrong_email.status_code == r_wrong_pw.status_code == 401
    assert r_wrong_email.json() == r_wrong_pw.json()


def test_no_user_enumeration_timing(client):
    """Mean timing gap between unknown-email and wrong-password must be < 50ms.

    Runs + warmup must stay below LOCKOUT_THRESHOLD (10) to avoid the lockout
    fast-path (which bypasses argon2 and would widen the gap artificially).
    """
    c, email = client
    c.post("/auth/register", json={"email": "tim@example.com", "password": "longpassword12"})
    c.post("/auth/verify-email", json={"token": email.sent[-1][2]})

    # 1 warmup pair (1 fail for tim → total stays well below lockout=10)
    c.post("/auth/login", json={"email": "tim@example.com", "password": "wrongwrongwrong12"})
    c.post("/auth/login", json={"email": "ghost@example.com", "password": "wrongwrongwrong12"})

    # 6 measurement runs → 7 total fails for tim, still under lockout threshold
    runs = 6
    t_known = 0.0
    t_unknown = 0.0
    for _ in range(runs):
        start = time.perf_counter()
        c.post("/auth/login", json={"email": "tim@example.com", "password": "wrongwrongwrong12"})
        t_known += time.perf_counter() - start
        start = time.perf_counter()
        c.post("/auth/login", json={"email": "ghost@example.com", "password": "wrongwrongwrong12"})
        t_unknown += time.perf_counter() - start

    avg_known = t_known / runs
    avg_unknown = t_unknown / runs
    assert abs(avg_known - avg_unknown) < 0.050, f"timing gap too large: {avg_known=} {avg_unknown=}"
