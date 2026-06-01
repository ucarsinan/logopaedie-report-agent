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


def test_rate_limit_login_5_per_min(client, unique_ip_headers):
    """slowapi limit 5/minute/IP on /auth/login — 6th call returns 429."""
    c, email = client
    c.post("/auth/register", json={"email": "rl@example.com", "password": "longpassword12"})
    c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
    for _ in range(5):
        c.post(
            "/auth/login",
            json={"email": "rl@example.com", "password": "wrongpassword12"},
            headers=unique_ip_headers,
        )
    res = c.post(
        "/auth/login",
        json={"email": "rl@example.com", "password": "wrongpassword12"},
        headers=unique_ip_headers,
    )
    assert res.status_code == 429


def test_rate_limit_verify_email_10_per_min(client, unique_ip_headers):
    """slowapi limit 10/minute/IP on /auth/verify-email — 11th call returns 429."""
    c, _ = client
    for _ in range(10):
        c.post("/auth/verify-email", json={"token": "garbage"}, headers=unique_ip_headers)
    res = c.post("/auth/verify-email", json={"token": "garbage"}, headers=unique_ip_headers)
    assert res.status_code == 429


def test_rate_limit_resend_verification_3_per_hour(client, unique_ip_headers):
    """slowapi limit 3/hour/IP on /auth/resend-verification — 4th call returns 429."""
    c, _ = client
    for _ in range(3):
        c.post("/auth/resend-verification", json={"email": "rv@example.com"}, headers=unique_ip_headers)
    res = c.post("/auth/resend-verification", json={"email": "rv@example.com"}, headers=unique_ip_headers)
    assert res.status_code == 429


def test_rate_limit_password_reset_confirm_10_per_hour(client, unique_ip_headers):
    """slowapi limit 10/hour/IP on /auth/password/reset/confirm — 11th call returns 429."""
    c, _ = client
    for _ in range(10):
        c.post(
            "/auth/password/reset/confirm",
            json={"token": "garbage", "new_password": "longpassword12"},
            headers=unique_ip_headers,
        )
    res = c.post(
        "/auth/password/reset/confirm",
        json={"token": "garbage", "new_password": "longpassword12"},
        headers=unique_ip_headers,
    )
    assert res.status_code == 429


def test_rate_limit_password_change_5_per_min(client, unique_ip_headers):
    """slowapi limit 5/minute/IP on /auth/password/change — 6th call returns 429."""
    c, email = client
    c.post("/auth/register", json={"email": "pwch@example.com", "password": "longpassword12"})
    c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
    tokens = c.post("/auth/login", json={"email": "pwch@example.com", "password": "longpassword12"}).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}", **unique_ip_headers}
    for _ in range(5):
        c.post(
            "/auth/password/change",
            json={"current_password": "wrong", "new_password": "longpassword12"},
            headers=headers,
        )
    res = c.post(
        "/auth/password/change",
        json={"current_password": "wrong", "new_password": "longpassword12"},
        headers=headers,
    )
    assert res.status_code == 429


def _assert_rate_limit_payload(res) -> None:
    """The app's custom exception handler returns a JSON body for 429s in
    German — that's the project's rate-limit signal in lieu of a Retry-After
    header (see ``rate_limit_exceeded_handler`` in ``main.py``).
    """
    assert res.status_code == 429
    assert "Zu viele Anfragen" in res.json().get("detail", "")


def test_rate_limit_logout_30_per_min(client, unique_ip_headers):
    """S-2: /auth/logout accepts an attacker-supplied refresh_token and probes
    the DB on every call — slowapi limit 30/minute/IP, 31st call returns 429.
    """
    c, _ = client
    for _ in range(30):
        c.post("/auth/logout", json={"refresh_token": "garbage"}, headers=unique_ip_headers)
    res = c.post("/auth/logout", json={"refresh_token": "garbage"}, headers=unique_ip_headers)
    _assert_rate_limit_payload(res)


def test_rate_limit_list_sessions_30_per_min(client, unique_ip_headers):
    """S-2: GET /auth/sessions is auth-gated but write-amplifying (one DB scan
    per call) — slowapi limit 30/minute/IP, 31st call returns 429.
    """
    c, email = client
    c.post("/auth/register", json={"email": "ls@example.com", "password": "longpassword12"})
    c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
    tokens = c.post("/auth/login", json={"email": "ls@example.com", "password": "longpassword12"}).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}", **unique_ip_headers}
    for _ in range(30):
        c.get("/auth/sessions", headers=headers)
    res = c.get("/auth/sessions", headers=headers)
    _assert_rate_limit_payload(res)


def test_rate_limit_delete_session_30_per_min(client, unique_ip_headers):
    """S-2: DELETE /auth/sessions/{id} is auth-gated but DB-touching — slowapi
    limit 30/minute/IP, 31st call returns 429. The handler returns 404 for the
    unknown UUID below, but the limit decorator runs first and still counts
    every call, so the 31st attempt is rejected with 429 before the handler.
    """
    c, email = client
    c.post("/auth/register", json={"email": "ds@example.com", "password": "longpassword12"})
    c.post("/auth/verify-email", json={"token": email.sent[-1][2]})
    tokens = c.post("/auth/login", json={"email": "ds@example.com", "password": "longpassword12"}).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}", **unique_ip_headers}
    target = "00000000-0000-0000-0000-000000000000"
    for _ in range(30):
        c.delete(f"/auth/sessions/{target}", headers=headers)
    res = c.delete(f"/auth/sessions/{target}", headers=headers)
    _assert_rate_limit_payload(res)


# ── P-1: pagination on GET /auth/sessions ─────────────────────────────────────


def _login_3_times(c, email_obj, addr: str) -> str:
    """Register, verify, then create 3 active sessions; return the latest access_token."""
    c.post("/auth/register", json={"email": addr, "password": "longpassword12"})
    c.post("/auth/verify-email", json={"token": email_obj.sent[-1][2]})
    tokens = None
    for _ in range(3):
        tokens = c.post("/auth/login", json={"email": addr, "password": "longpassword12"}).json()
    assert tokens is not None
    return tokens["access_token"]


def test_list_sessions_default_limit_returns_all(client):
    """No query params → default limit=50 returns all 3 sessions."""
    c, email = client
    access = _login_3_times(c, email, "p1a@example.com")
    res = c.get("/auth/sessions", headers={"Authorization": f"Bearer {access}"})
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_list_sessions_limit_clamps_page_size(client):
    """limit=2 returns exactly 2 rows (the most recently used)."""
    c, email = client
    access = _login_3_times(c, email, "p1b@example.com")
    res = c.get("/auth/sessions?limit=2", headers={"Authorization": f"Bearer {access}"})
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_list_sessions_offset_returns_next_batch(client):
    """offset=2 with limit=2 returns the 3rd session, no overlap."""
    c, email = client
    access = _login_3_times(c, email, "p1c@example.com")
    page1 = c.get("/auth/sessions?limit=2&offset=0", headers={"Authorization": f"Bearer {access}"}).json()
    page2 = c.get("/auth/sessions?limit=2&offset=2", headers={"Authorization": f"Bearer {access}"}).json()
    assert len(page1) == 2
    assert len(page2) == 1
    page1_ids = {s["id"] for s in page1}
    page2_ids = {s["id"] for s in page2}
    assert page1_ids.isdisjoint(page2_ids)


def test_list_sessions_limit_over_cap_returns_422(client):
    """limit > 200 violates the FastAPI Query(le=200) constraint and 422s."""
    c, email = client
    access = _login_3_times(c, email, "p1d@example.com")
    res = c.get("/auth/sessions?limit=300", headers={"Authorization": f"Bearer {access}"})
    assert res.status_code == 422


def test_list_sessions_negative_offset_returns_422(client):
    """offset must be ge=0 — negative offset is a validation error."""
    c, email = client
    access = _login_3_times(c, email, "p1e@example.com")
    res = c.get("/auth/sessions?offset=-1", headers={"Authorization": f"Bearer {access}"})
    assert res.status_code == 422
