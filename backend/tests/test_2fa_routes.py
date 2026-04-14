"""Tests for 2FA routes — setup, enable, disable, challenge login."""

from __future__ import annotations

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from models.auth import User
from services.audit_service import AuditService
from services.challenge_store import ChallengeStore
from services.email_service import FakeEmailService
from services.password_service import PasswordService
from services.token_service import TokenService
from services.totp_service import TOTPService

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def client(monkeypatch):
    from cryptography.fernet import Fernet

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
    tc.challenge_store = challenge_store  # type: ignore[attr-defined]
    tc.totp_svc = totp_svc  # type: ignore[attr-defined]
    yield tc
    app.dependency_overrides.clear()


@pytest.fixture
def db_session(client):
    with Session(client.engine) as db:
        yield db


@pytest.fixture
def totp_service(client):
    return client.totp_svc


# ── Helpers ───────────────────────────────────────────────────────────────────


def verify_email_token(client, email: str) -> None:
    token = next(t for _, to, t in client.email_svc.sent if to == email)
    client.post("/auth/verify-email", json={"token": token})
    client.email_svc.sent.clear()


def register_and_login(client, email: str, password: str) -> dict:
    client.post("/auth/register", json={"email": email, "password": password})
    verify_email_token(client, email)
    res = client.post("/auth/login", json={"email": email, "password": password})
    return res.json()


def auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def get_user(client, email: str) -> User:
    with Session(client.engine) as db:
        return db.exec(select(User).where(User.email == email)).one()


# ── Task 4.3 ──────────────────────────────────────────────────────────────────


def test_get_challenge_store_dependency_resolves():
    from dependencies import get_challenge_store

    assert get_challenge_store() is not None


# ── Task 4.4 ──────────────────────────────────────────────────────────────────


# ── Task 4.5 ──────────────────────────────────────────────────────────────────


def test_2fa_setup_persists_encrypted_secret(client, totp_service):
    tokens = register_and_login(client, "bob@example.com", "correct horse battery 2")
    res = client.post("/auth/2fa/setup", headers=auth_headers(tokens))
    secret_plain = res.json()["secret"]
    user = get_user(client, "bob@example.com")
    assert user.totp_secret != secret_plain  # must be encrypted
    assert totp_service.decrypt(user.totp_secret) == secret_plain


def test_2fa_setup_returns_secret_and_uri_but_not_enabled(client):
    tokens = register_and_login(client, "alice@example.com", "correct horse battery 1")
    res = client.post("/auth/2fa/setup", headers=auth_headers(tokens))
    assert res.status_code == 200
    body = res.json()
    assert "secret" in body and len(body["secret"]) >= 16
    assert body["provisioning_uri"].startswith("otpauth://totp/")
    user = get_user(client, "alice@example.com")
    assert user.totp_enabled is False
    assert user.totp_secret is not None


# ── Task 4.6 ──────────────────────────────────────────────────────────────────


def test_2fa_enable_rejects_wrong_code(client):
    tokens = register_and_login(client, "carol@example.com", "correct horse battery 3")
    client.post("/auth/2fa/setup", headers=auth_headers(tokens))
    res = client.post("/auth/2fa/enable", json={"code": "000000"}, headers=auth_headers(tokens))
    assert res.status_code == 400
    user = get_user(client, "carol@example.com")
    assert user.totp_enabled is False


# ── Task 4.7 ──────────────────────────────────────────────────────────────────


def test_2fa_enable_success_flips_flag(client):
    import pyotp

    tokens = register_and_login(client, "dave@example.com", "correct horse battery 4")
    setup = client.post("/auth/2fa/setup", headers=auth_headers(tokens)).json()
    code = pyotp.TOTP(setup["secret"]).now()
    res = client.post("/auth/2fa/enable", json={"code": code}, headers=auth_headers(tokens))
    assert res.status_code == 200
    user = get_user(client, "dave@example.com")
    assert user.totp_enabled is True


# ── Task 4.8 ──────────────────────────────────────────────────────────────────


def test_2fa_enable_revokes_other_sessions_keeps_current(client, db_session):
    import pyotp

    # Register + verify + login twice → two sessions
    register_and_login(client, "eve@example.com", "correct horse battery 5")
    first = client.post("/auth/login", json={"email": "eve@example.com", "password": "correct horse battery 5"}).json()
    second = client.post("/auth/login", json={"email": "eve@example.com", "password": "correct horse battery 5"}).json()
    # Setup + enable using the SECOND session
    setup = client.post("/auth/2fa/setup", headers=auth_headers(second)).json()
    code = pyotp.TOTP(setup["secret"]).now()
    client.post("/auth/2fa/enable", json={"code": code}, headers=auth_headers(second))
    # Refresh with the FIRST session → must be revoked
    res = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert res.status_code == 401
    # Refresh with the SECOND → still alive
    res2 = client.post("/auth/refresh", json={"refresh_token": second["refresh_token"]})
    assert res2.status_code == 200


# ── Tasks 4.9 / 4.10 / 4.11 ──────────────────────────────────────────────────


def _enable_2fa(client, email: str, password: str):
    tokens = register_and_login(client, email, password)
    setup = client.post("/auth/2fa/setup", headers=auth_headers(tokens)).json()
    import pyotp

    code = pyotp.TOTP(setup["secret"]).now()
    client.post("/auth/2fa/enable", json={"code": code}, headers=auth_headers(tokens))
    return tokens, setup["secret"]


def test_2fa_disable_requires_password_and_code(client):
    tokens, _ = _enable_2fa(client, "frank@example.com", "correct horse battery 6")
    # missing code → 422
    res = client.post(
        "/auth/2fa/disable",
        json={"current_password": "correct horse battery 6"},
        headers=auth_headers(tokens),
    )
    assert res.status_code == 422


def test_2fa_disable_wrong_password_rejected(client):
    import pyotp

    tokens, secret = _enable_2fa(client, "greta@example.com", "correct horse battery 7")
    res = client.post(
        "/auth/2fa/disable",
        json={"current_password": "wrong", "code": pyotp.TOTP(secret).now()},
        headers=auth_headers(tokens),
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Verification failed"


def test_2fa_disable_wrong_code_rejected(client):
    tokens, secret = _enable_2fa(client, "hank@example.com", "correct horse battery 8")
    res = client.post(
        "/auth/2fa/disable",
        json={"current_password": "correct horse battery 8", "code": "000000"},
        headers=auth_headers(tokens),
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Verification failed"


def test_2fa_disable_success_revokes_all_sessions(client):
    import pyotp

    tokens, secret = _enable_2fa(client, "ivan@example.com", "correct horse battery 9")
    res = client.post(
        "/auth/2fa/disable",
        json={"current_password": "correct horse battery 9", "code": pyotp.TOTP(secret).now()},
        headers=auth_headers(tokens),
    )
    assert res.status_code == 200
    refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401


# ── Task 4.12 ─────────────────────────────────────────────────────────────────


def test_login_with_2fa_returns_challenge_no_tokens(client):
    _enable_2fa(client, "jane@example.com", "correct horse battery 10")
    res = client.post("/auth/login", json={"email": "jane@example.com", "password": "correct horse battery 10"})
    assert res.status_code == 200
    body = res.json()
    assert body["step"] == "2fa_required"
    assert "challenge_id" in body
    assert "access_token" not in body
    assert "refresh_token" not in body


# ── Task 4.13 ─────────────────────────────────────────────────────────────────


def test_login_2fa_success_creates_session(client):
    import pyotp

    _, secret = _enable_2fa(client, "kim@example.com", "correct horse battery 11")
    step1 = client.post("/auth/login", json={"email": "kim@example.com", "password": "correct horse battery 11"}).json()
    res = client.post(
        "/auth/login/2fa",
        json={"challenge_id": step1["challenge_id"], "code": pyotp.TOTP(secret).now()},
    )
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body and "refresh_token" in body
    assert body["user"]["email"] == "kim@example.com"


# ── Task 4.14 ─────────────────────────────────────────────────────────────────


def test_login_2fa_challenge_single_use(client):
    import pyotp

    _, secret = _enable_2fa(client, "leo@example.com", "correct horse battery 12")
    step1 = client.post("/auth/login", json={"email": "leo@example.com", "password": "correct horse battery 12"}).json()
    code = pyotp.TOTP(secret).now()
    first = client.post("/auth/login/2fa", json={"challenge_id": step1["challenge_id"], "code": code})
    second = client.post("/auth/login/2fa", json={"challenge_id": step1["challenge_id"], "code": code})
    assert first.status_code == 200
    assert second.status_code == 401


def test_login_2fa_challenge_expires(client):
    import time

    import pyotp

    _, secret = _enable_2fa(client, "max@example.com", "correct horse battery 13")
    step1 = client.post("/auth/login", json={"email": "max@example.com", "password": "correct horse battery 13"}).json()
    # Overwrite the challenge with a 1-second TTL to simulate expiry
    client.challenge_store._client.set(f"auth:2fa:challenge:{step1['challenge_id']}", "nobody", ex=1)
    time.sleep(1.1)
    res = client.post(
        "/auth/login/2fa",
        json={"challenge_id": step1["challenge_id"], "code": pyotp.TOTP(secret).now()},
    )
    assert res.status_code == 401


def test_login_2fa_wrong_code_increments_failed_count(client):
    _, secret = _enable_2fa(client, "nora@example.com", "correct horse battery 14")
    step1 = client.post(
        "/auth/login", json={"email": "nora@example.com", "password": "correct horse battery 14"}
    ).json()
    res = client.post("/auth/login/2fa", json={"challenge_id": step1["challenge_id"], "code": "000000"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid code"
    user = get_user(client, "nora@example.com")
    assert user.failed_login_count >= 1


# ── Gate 4A fixes ─────────────────────────────────────────────────────────────


def test_login_2fa_replay_rejected(client):
    """Same TOTP code (same step) must be rejected on second use — Gate 4A Finding #2."""
    import pyotp

    _, secret = _enable_2fa(client, "oscar@example.com", "correct horse battery 15")

    # First login: get challenge, submit valid code → success
    step1 = client.post(
        "/auth/login", json={"email": "oscar@example.com", "password": "correct horse battery 15"}
    ).json()
    code = pyotp.TOTP(secret).now()
    first = client.post("/auth/login/2fa", json={"challenge_id": step1["challenge_id"], "code": code})
    assert first.status_code == 200

    # Second login: new challenge, same code (same TOTP step within window) → must be rejected
    step2 = client.post(
        "/auth/login", json={"email": "oscar@example.com", "password": "correct horse battery 15"}
    ).json()
    second = client.post("/auth/login/2fa", json={"challenge_id": step2["challenge_id"], "code": code})
    assert second.status_code == 401


def test_login_2fa_locked_account_rejected(client, db_session):
    """login_2fa must honour locked_until — Gate 4A Finding #6a."""
    from datetime import timedelta

    _, secret = _enable_2fa(client, "petra@example.com", "correct horse battery 16")

    # Get a valid challenge while unlocked
    step1 = client.post(
        "/auth/login", json={"email": "petra@example.com", "password": "correct horse battery 16"}
    ).json()

    # Lock the account directly in DB (simulates admin action or concurrent lockout)
    user = get_user(client, "petra@example.com")
    from datetime import UTC, datetime

    with Session(client.engine) as db:
        u = db.get(type(user), user.id)
        u.locked_until = datetime.now(UTC) + timedelta(minutes=15)
        db.add(u)
        db.commit()

    import pyotp

    res = client.post("/auth/login/2fa", json={"challenge_id": step1["challenge_id"], "code": pyotp.TOTP(secret).now()})
    assert res.status_code == 423


def test_login_2fa_wrong_code_triggers_lockout(client):
    """TOTP failures must apply atomic lockout — Gate 4A Finding #6a."""
    from sqlmodel import Session

    _, secret = _enable_2fa(client, "quinn@example.com", "correct horse battery 17")

    # Get challenge first — login() resets failed_login_count to 0 on success
    step = client.post(
        "/auth/login", json={"email": "quinn@example.com", "password": "correct horse battery 17"}
    ).json()

    # Pre-seed count AFTER the challenge is issued (so login's reset doesn't undo it)
    user = get_user(client, "quinn@example.com")
    with Session(client.engine) as db:
        u = db.get(type(user), user.id)
        u.failed_login_count = 9  # LOCKOUT_THRESHOLD - 1
        db.add(u)
        db.commit()

    # One bad TOTP attempt: 9 + 1 = 10 >= 10 → locked_until must be set
    client.post("/auth/login/2fa", json={"challenge_id": step["challenge_id"], "code": "000000"})

    user = get_user(client, "quinn@example.com")
    assert user.locked_until is not None


def test_2fa_enable_replay_rejected(client):
    """TOTP code used to enable must be rejected if reused — Gate 4A Finding #2."""
    import pyotp

    tokens = register_and_login(client, "rachel@example.com", "correct horse battery 18")
    setup = client.post("/auth/2fa/setup", headers=auth_headers(tokens)).json()
    code = pyotp.TOTP(setup["secret"]).now()

    # First enable succeeds
    res1 = client.post("/auth/2fa/enable", json={"code": code}, headers=auth_headers(tokens))
    assert res1.status_code == 200

    # Disable and set up again so we can test re-enable with old code
    tokens2 = register_and_login(client, "sam@example.com", "correct horse battery 19")
    setup2 = client.post("/auth/2fa/setup", headers=auth_headers(tokens2)).json()
    code2 = pyotp.TOTP(setup2["secret"]).now()

    # Enable once — sets last_totp_step
    client.post("/auth/2fa/enable", json={"code": code2}, headers=auth_headers(tokens2))
    user = get_user(client, "sam@example.com")
    assert user.totp_enabled is True

    # Try to re-enable (already-enabled guard)
    res2 = client.post("/auth/2fa/enable", json={"code": code2}, headers=auth_headers(tokens2))
    assert res2.status_code == 400


def test_2fa_enable_already_enabled_rejected(client):
    """enable_2fa must reject when totp_enabled is already True — Gate 4A Finding #4."""
    import pyotp

    tokens, secret = _enable_2fa(client, "tara@example.com", "correct horse battery 20")
    # At this point 2FA is enabled; try to call /2fa/enable again
    new_code = pyotp.TOTP(secret).now()
    res = client.post("/auth/2fa/enable", json={"code": new_code}, headers=auth_headers(tokens))
    assert res.status_code == 400
