import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from models.auth import EmailToken, User, UserSession
from services.audit_service import AuditService
from services.auth_service import AuthService
from services.email_service import FakeEmailService
from services.password_service import PasswordService
from services.token_service import TokenService


@pytest.fixture
def deps(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    email = FakeEmailService()
    svc = AuthService(
        password=PasswordService(),
        tokens=TokenService(),
        email=email,
        audit=AuditService(),
    )
    with Session(eng) as db:
        yield svc, db, email


def test_register_creates_user_and_sends_verify_email(deps):
    svc, db, email = deps
    svc.register(db, email_addr="alice@example.com", password="longpassword12", ip="1.1.1.1", ua="pytest")
    users = db.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].email == "alice@example.com"
    assert users[0].email_verified is False
    assert len(email.sent) == 1
    assert email.sent[0][0] == "verify"


def test_register_duplicate_email_no_email_sent(deps):
    svc, db, email = deps
    svc.register(db, email_addr="dup@example.com", password="longpassword12", ip=None, ua=None)
    email.sent.clear()
    svc.register(db, email_addr="dup@example.com", password="otherlongpass12", ip=None, ua=None)
    assert email.sent == []
    assert len(db.exec(select(User)).all()) == 1


def test_verify_email_valid_token_marks_verified(deps):
    svc, db, email = deps
    svc.register(db, email_addr="v@example.com", password="longpassword12", ip=None, ua=None)
    plain_token = email.sent[-1][2]
    svc.verify_email(db, token=plain_token, ip=None, ua=None)
    user = db.exec(select(User).where(User.email == "v@example.com")).one()
    assert user.email_verified is True
    assert user.email_verified_at is not None


def test_verify_email_reused_token_rejected(deps):
    svc, db, email = deps
    svc.register(db, email_addr="r@example.com", password="longpassword12", ip=None, ua=None)
    plain_token = email.sent[-1][2]
    svc.verify_email(db, token=plain_token, ip=None, ua=None)
    from exceptions import TokenInvalidError

    with pytest.raises(TokenInvalidError):
        svc.verify_email(db, token=plain_token, ip=None, ua=None)


def test_verify_email_expired_token_rejected(deps):
    svc, db, email = deps
    svc.register(db, email_addr="e@example.com", password="longpassword12", ip=None, ua=None)
    plain_token = email.sent[-1][2]
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    tok = db.exec(select(EmailToken).where(EmailToken.token_hash == token_hash)).one()
    tok.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.add(tok)
    db.commit()
    from exceptions import TokenInvalidError

    with pytest.raises(TokenInvalidError):
        svc.verify_email(db, token=plain_token, ip=None, ua=None)


# ── Task 3.3: login / refresh / logout ───────────────────────────────────────


def _make_verified_user(svc: AuthService, db, email_svc, email: str, password: str = "longpassword12"):
    svc.register(db, email_addr=email, password=password, ip=None, ua=None)
    plain_token = email_svc.sent[-1][2]
    svc.verify_email(db, token=plain_token, ip=None, ua=None)


def test_login_unverified_raises_email_not_verified(deps):
    svc, db, email = deps
    svc.register(db, email_addr="u@example.com", password="longpassword12", ip=None, ua=None)
    from exceptions import EmailNotVerifiedError

    with pytest.raises(EmailNotVerifiedError):
        svc.login(db, email_addr="u@example.com", password="longpassword12", ip=None, ua=None)


def test_login_wrong_password_generic(deps):
    svc, db, email = deps
    _make_verified_user(svc, db, email, "good@example.com")
    from exceptions import InvalidCredentialsError

    with pytest.raises(InvalidCredentialsError):
        svc.login(db, email_addr="good@example.com", password="wrongpassword12", ip=None, ua=None)


def test_login_unknown_email_generic(deps):
    svc, db, email = deps
    from exceptions import InvalidCredentialsError

    with pytest.raises(InvalidCredentialsError):
        svc.login(db, email_addr="nobody@example.com", password="longpassword12", ip=None, ua=None)


def test_login_success_returns_tokens(deps):
    svc, db, email = deps
    _make_verified_user(svc, db, email, "ok@example.com")
    result = svc.login(db, email_addr="ok@example.com", password="longpassword12", ip="1.1.1.1", ua="pytest")
    assert "access_token" in result and "refresh_token" in result
    assert result["user"]["email"] == "ok@example.com"
    sessions = db.exec(select(UserSession)).all()
    assert len(sessions) == 1


def test_login_lockout_after_10_fails(deps):
    svc, db, email = deps
    _make_verified_user(svc, db, email, "lock@example.com")
    from exceptions import AccountLockedError, InvalidCredentialsError

    for _ in range(10):
        with pytest.raises(InvalidCredentialsError):
            svc.login(db, email_addr="lock@example.com", password="wrongpassword12", ip=None, ua=None)
    with pytest.raises(AccountLockedError):
        svc.login(db, email_addr="lock@example.com", password="longpassword12", ip=None, ua=None)


def test_refresh_rotates_token(deps):
    svc, db, email = deps
    _make_verified_user(svc, db, email, "rot@example.com")
    first = svc.login(db, email_addr="rot@example.com", password="longpassword12", ip=None, ua=None)
    second = svc.refresh(db, refresh_token=first["refresh_token"], ip=None, ua=None)
    assert second["refresh_token"] != first["refresh_token"]
    from exceptions import TokenInvalidError

    with pytest.raises(TokenInvalidError):
        svc.refresh(db, refresh_token=first["refresh_token"], ip=None, ua=None)


def test_refresh_reuse_revokes_all_sessions(deps):
    svc, db, email = deps
    _make_verified_user(svc, db, email, "reuse@example.com")
    first = svc.login(db, email_addr="reuse@example.com", password="longpassword12", ip=None, ua=None)
    _ = svc.login(db, email_addr="reuse@example.com", password="longpassword12", ip=None, ua=None)
    svc.refresh(db, refresh_token=first["refresh_token"], ip=None, ua=None)
    from exceptions import TokenInvalidError

    with pytest.raises(TokenInvalidError):
        svc.refresh(db, refresh_token=first["refresh_token"], ip=None, ua=None)
    active = db.exec(select(UserSession).where(UserSession.revoked_at.is_(None))).all()
    assert active == []
    from models.auth import AuditLog

    events = [row.event for row in db.exec(select(AuditLog)).all()]
    assert "session.refresh_reuse_detected" in events


# ── Task 3.4: password reset / change ────────────────────────────────────────


def test_password_reset_request_unknown_email_silent(deps):
    svc, db, email = deps
    svc.request_password_reset(db, email_addr="ghost@example.com", ip=None, ua=None)
    assert email.sent == []


def test_password_reset_confirm_revokes_all_sessions(deps):
    svc, db, email = deps
    _make_verified_user(svc, db, email, "reset@example.com")
    svc.login(db, email_addr="reset@example.com", password="longpassword12", ip=None, ua=None)
    svc.login(db, email_addr="reset@example.com", password="longpassword12", ip=None, ua=None)
    email.sent.clear()
    svc.request_password_reset(db, email_addr="reset@example.com", ip=None, ua=None)
    reset_token = email.sent[-1][2]
    svc.confirm_password_reset(db, token=reset_token, new_password="newlongpassword34", ip=None, ua=None)
    active = db.exec(select(UserSession).where(UserSession.revoked_at.is_(None))).all()
    assert active == []
    svc.login(db, email_addr="reset@example.com", password="newlongpassword34", ip=None, ua=None)


def test_password_change_revokes_other_sessions_only(deps):
    svc, db, email = deps
    _make_verified_user(svc, db, email, "ch@example.com")
    s1 = svc.login(db, email_addr="ch@example.com", password="longpassword12", ip=None, ua=None)
    _s2 = svc.login(db, email_addr="ch@example.com", password="longpassword12", ip=None, ua=None)
    user = db.exec(select(User).where(User.email == "ch@example.com")).one()
    svc.change_password(
        db,
        user=user,
        current_password="longpassword12",
        new_password="newlongpassword34",
        current_refresh_token=s1["refresh_token"],
        ip=None,
        ua=None,
    )
    active = db.exec(select(UserSession).where(UserSession.revoked_at.is_(None))).all()
    assert len(active) == 1
    svc.refresh(db, refresh_token=s1["refresh_token"], ip=None, ua=None)
