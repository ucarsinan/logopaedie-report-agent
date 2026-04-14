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

    # Lazy imports so GROQ_API_KEY autouse fixture in conftest runs first
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


def test_register_returns_generic_200(client):
    c, _ = client
    res = c.post("/auth/register", json={"email": "r1@example.com", "password": "longpassword12"})
    assert res.status_code == 200
    assert "inbox" in res.json()["message"].lower()


def test_register_duplicate_email_returns_generic_200_no_second_mail(client):
    c, email = client
    c.post("/auth/register", json={"email": "dup@example.com", "password": "longpassword12"})
    email.sent.clear()
    res = c.post("/auth/register", json={"email": "dup@example.com", "password": "otherlongpass12"})
    assert res.status_code == 200
    assert email.sent == []


def test_verify_email_then_login(client):
    c, email = client
    c.post("/auth/register", json={"email": "ok@example.com", "password": "longpassword12"})
    token = email.sent[-1][2]
    assert c.post("/auth/verify-email", json={"token": token}).status_code == 200
    res = c.post("/auth/login", json={"email": "ok@example.com", "password": "longpassword12"})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body and "refresh_token" in body


def test_login_wrong_password_401_generic(client):
    c, email = client
    c.post("/auth/register", json={"email": "w@example.com", "password": "longpassword12"})
    token = email.sent[-1][2]
    c.post("/auth/verify-email", json={"token": token})
    res = c.post("/auth/login", json={"email": "w@example.com", "password": "badbadbadbad12"})
    assert res.status_code == 401
    assert res.json()["error"] == "invalid_credentials"


def test_login_unknown_email_401_generic(client):
    c, _ = client
    res = c.post("/auth/login", json={"email": "nobody@example.com", "password": "longpassword12"})
    assert res.status_code == 401
    assert res.json()["error"] == "invalid_credentials"


def test_login_unverified_returns_403(client):
    c, _ = client
    c.post("/auth/register", json={"email": "nv@example.com", "password": "longpassword12"})
    res = c.post("/auth/login", json={"email": "nv@example.com", "password": "longpassword12"})
    assert res.status_code == 403
    assert res.json()["error"] == "email_not_verified"


def test_refresh_rotates_and_old_invalid(client):
    c, email = client
    c.post("/auth/register", json={"email": "rf@example.com", "password": "longpassword12"})
    c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
    tokens = c.post("/auth/login", json={"email": "rf@example.com", "password": "longpassword12"}).json()
    res = c.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert res.status_code == 200
    new_tokens = res.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    again = c.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert again.status_code == 401


def test_logout_revokes_current_session(client):
    c, email = client
    c.post("/auth/register", json={"email": "lo@example.com", "password": "longpassword12"})
    c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
    tokens = c.post("/auth/login", json={"email": "lo@example.com", "password": "longpassword12"}).json()
    assert c.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 200
    again = c.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert again.status_code == 401


def test_me_returns_profile_when_authenticated(client):
    c, email = client
    c.post("/auth/register", json={"email": "me@example.com", "password": "longpassword12"})
    c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
    tokens = c.post("/auth/login", json={"email": "me@example.com", "password": "longpassword12"}).json()
    res = c.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert res.status_code == 200
    assert res.json()["email"] == "me@example.com"


def test_me_returns_401_when_no_token(client):
    c, _ = client
    res = c.get("/auth/me")
    assert res.status_code == 401


def test_password_reset_request_unknown_email_returns_200(client):
    c, email = client
    res = c.post("/auth/password/reset/request", json={"email": "ghost@example.com"})
    assert res.status_code == 200
    assert email.sent == []


def test_password_reset_confirm_revokes_all_sessions(client):
    c, email = client
    c.post("/auth/register", json={"email": "rs@example.com", "password": "longpassword12"})
    c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
    t1 = c.post("/auth/login", json={"email": "rs@example.com", "password": "longpassword12"}).json()
    t2 = c.post("/auth/login", json={"email": "rs@example.com", "password": "longpassword12"}).json()
    email.sent.clear()
    c.post("/auth/password/reset/request", json={"email": "rs@example.com"})
    reset_token = email.sent[-1][2]
    res = c.post("/auth/password/reset/confirm", json={"token": reset_token, "new_password": "newlongpassword34"})
    assert res.status_code == 200
    assert c.post("/auth/refresh", json={"refresh_token": t1["refresh_token"]}).status_code == 401
    assert c.post("/auth/refresh", json={"refresh_token": t2["refresh_token"]}).status_code == 401
