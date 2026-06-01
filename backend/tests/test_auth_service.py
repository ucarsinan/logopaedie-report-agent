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


@pytest.mark.asyncio
async def test_register_creates_user_and_sends_verify_email(deps):
    svc, db, email = deps
    await svc.register(db, email_addr="alice@example.com", password="longpassword12", ip="1.1.1.1", ua="pytest")
    users = db.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].email == "alice@example.com"
    assert users[0].email_verified is False
    assert len(email.sent) == 1
    assert email.sent[0][0] == "verify"


@pytest.mark.asyncio
async def test_register_duplicate_email_no_email_sent(deps):
    svc, db, email = deps
    await svc.register(db, email_addr="dup@example.com", password="longpassword12", ip=None, ua=None)
    email.sent.clear()
    await svc.register(db, email_addr="dup@example.com", password="otherlongpass12", ip=None, ua=None)
    assert email.sent == []
    assert len(db.exec(select(User)).all()) == 1


@pytest.mark.asyncio
async def test_verify_email_valid_token_marks_verified(deps):
    svc, db, email = deps
    await svc.register(db, email_addr="v@example.com", password="longpassword12", ip=None, ua=None)
    plain_token = email.sent[-1][2]
    svc.verify_email(db, token=plain_token, ip=None, ua=None)
    user = db.exec(select(User).where(User.email == "v@example.com")).one()
    assert user.email_verified is True
    assert user.email_verified_at is not None


@pytest.mark.asyncio
async def test_verify_email_reused_token_rejected(deps):
    svc, db, email = deps
    await svc.register(db, email_addr="r@example.com", password="longpassword12", ip=None, ua=None)
    plain_token = email.sent[-1][2]
    svc.verify_email(db, token=plain_token, ip=None, ua=None)
    from exceptions import TokenInvalidError

    with pytest.raises(TokenInvalidError):
        svc.verify_email(db, token=plain_token, ip=None, ua=None)


@pytest.mark.asyncio
async def test_verify_email_expired_token_rejected(deps):
    svc, db, email = deps
    await svc.register(db, email_addr="e@example.com", password="longpassword12", ip=None, ua=None)
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


async def _make_verified_user(svc: AuthService, db, email_svc, email: str, password: str = "longpassword12"):
    await svc.register(db, email_addr=email, password=password, ip=None, ua=None)
    plain_token = email_svc.sent[-1][2]
    svc.verify_email(db, token=plain_token, ip=None, ua=None)


@pytest.mark.asyncio
async def test_login_unverified_raises_email_not_verified(deps):
    svc, db, _email = deps
    await svc.register(db, email_addr="u@example.com", password="longpassword12", ip=None, ua=None)
    from exceptions import EmailNotVerifiedError

    with pytest.raises(EmailNotVerifiedError):
        svc.login(db, email_addr="u@example.com", password="longpassword12", ip=None, ua=None)


@pytest.mark.asyncio
async def test_login_wrong_password_generic(deps):
    svc, db, email = deps
    await _make_verified_user(svc, db, email, "good@example.com")
    from exceptions import InvalidCredentialsError

    with pytest.raises(InvalidCredentialsError):
        svc.login(db, email_addr="good@example.com", password="wrongpassword12", ip=None, ua=None)


def test_login_unknown_email_generic(deps):
    svc, db, _email = deps
    from exceptions import InvalidCredentialsError

    with pytest.raises(InvalidCredentialsError):
        svc.login(db, email_addr="nobody@example.com", password="longpassword12", ip=None, ua=None)


@pytest.mark.asyncio
async def test_login_success_returns_tokens(deps):
    svc, db, email = deps
    await _make_verified_user(svc, db, email, "ok@example.com")
    result = svc.login(db, email_addr="ok@example.com", password="longpassword12", ip="1.1.1.1", ua="pytest")
    assert "access_token" in result and "refresh_token" in result
    assert result["user"]["email"] == "ok@example.com"
    sessions = db.exec(select(UserSession)).all()
    assert len(sessions) == 1


@pytest.mark.asyncio
async def test_login_lockout_after_10_fails(deps):
    svc, db, email = deps
    await _make_verified_user(svc, db, email, "lock@example.com")
    from exceptions import AccountLockedError, InvalidCredentialsError

    for _ in range(10):
        with pytest.raises(InvalidCredentialsError):
            svc.login(db, email_addr="lock@example.com", password="wrongpassword12", ip=None, ua=None)
    with pytest.raises(AccountLockedError):
        svc.login(db, email_addr="lock@example.com", password="longpassword12", ip=None, ua=None)


@pytest.mark.asyncio
async def test_refresh_rotates_token(deps):
    svc, db, email = deps
    await _make_verified_user(svc, db, email, "rot@example.com")
    first = svc.login(db, email_addr="rot@example.com", password="longpassword12", ip=None, ua=None)
    second = svc.refresh(db, refresh_token=first["refresh_token"], ip=None, ua=None)
    assert second["refresh_token"] != first["refresh_token"]
    from exceptions import TokenInvalidError

    with pytest.raises(TokenInvalidError):
        svc.refresh(db, refresh_token=first["refresh_token"], ip=None, ua=None)


@pytest.mark.asyncio
async def test_refresh_happy_path_emits_audit_row(deps):
    """M4: token rotation is security-relevant and must be auditable.

    Drives ``AuthService.refresh`` directly (no BackgroundTasks → sync audit
    path) and asserts the ``user.token_refreshed`` row landed with the
    expected user_id and metadata pointing at the rotated session ids.
    """
    svc, db, email = deps
    await _make_verified_user(svc, db, email, "audit@example.com")
    first = svc.login(db, email_addr="audit@example.com", password="longpassword12", ip="9.9.9.9", ua="pytest-ua")

    # Capture the session id about to be rotated so we can verify the
    # metadata.old_session_id linkage.
    from models.auth import AuditLog

    user = db.exec(select(User).where(User.email == "audit@example.com")).one()
    old_session = db.exec(
        select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    ).one()
    pre_event_count = len(db.exec(select(AuditLog).where(AuditLog.event == "user.token_refreshed")).all())

    svc.refresh(db, refresh_token=first["refresh_token"], ip="9.9.9.9", ua="pytest-ua")

    rows = db.exec(select(AuditLog).where(AuditLog.event == "user.token_refreshed")).all()
    assert len(rows) == pre_event_count + 1
    row = rows[-1]
    assert row.user_id == user.id
    assert row.ip_address == "9.9.9.9"
    assert row.user_agent == "pytest-ua"
    assert row.metadata_json.get("old_session_id") == str(old_session.id)
    new_session = db.exec(
        select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    ).one()
    assert row.metadata_json.get("new_session_id") == str(new_session.id)


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_all_sessions(deps):
    svc, db, email = deps
    await _make_verified_user(svc, db, email, "reuse@example.com")
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


@pytest.mark.asyncio
async def test_password_reset_request_unknown_email_silent(deps):
    svc, db, email = deps
    await svc.request_password_reset(db, email_addr="ghost@example.com", ip=None, ua=None)
    assert email.sent == []


@pytest.mark.asyncio
async def test_password_reset_confirm_revokes_all_sessions(deps):
    svc, db, email = deps
    await _make_verified_user(svc, db, email, "reset@example.com")
    svc.login(db, email_addr="reset@example.com", password="longpassword12", ip=None, ua=None)
    svc.login(db, email_addr="reset@example.com", password="longpassword12", ip=None, ua=None)
    email.sent.clear()
    await svc.request_password_reset(db, email_addr="reset@example.com", ip=None, ua=None)
    reset_token = email.sent[-1][2]
    svc.confirm_password_reset(db, token=reset_token, new_password="newlongpassword34", ip=None, ua=None)
    active = db.exec(select(UserSession).where(UserSession.revoked_at.is_(None))).all()
    assert active == []
    svc.login(db, email_addr="reset@example.com", password="newlongpassword34", ip=None, ua=None)


# ── S-1: audit_log.metadata must not contain raw email ──────────────────────


@pytest.mark.asyncio
async def test_register_audit_metadata_uses_email_hash_not_raw_email(deps):
    """S-1: ``user.register_attempt`` must store an email_hash, never raw email.

    audit_log rows are admin-readable via /admin/audit and stored unencrypted,
    so raw email turns the table into a GDPR-relevant PII store.
    """
    from models.auth import AuditLog

    svc, db, _email = deps
    await svc.register(db, email_addr="pii-register@example.com", password="longpassword12", ip=None, ua=None)
    row = db.exec(select(AuditLog).where(AuditLog.event == "user.register_attempt")).one()
    assert "email" not in row.metadata_json
    assert "email_hash" in row.metadata_json
    # Hash must be stable + correlate same email across emits
    from services.auth_service import _hash_email

    assert row.metadata_json["email_hash"] == _hash_email("pii-register@example.com")


@pytest.mark.asyncio
async def test_password_reset_request_audit_uses_email_hash(deps):
    """S-1: ``password.reset_requested`` must store an email_hash, never raw email."""
    from models.auth import AuditLog

    svc, db, _email = deps
    await svc.request_password_reset(db, email_addr="pii-reset@example.com", ip=None, ua=None)
    row = db.exec(select(AuditLog).where(AuditLog.event == "password.reset_requested")).one()
    assert "email" not in row.metadata_json
    assert "email_hash" in row.metadata_json


@pytest.mark.asyncio
async def test_resend_verification_audit_uses_email_hash(deps):
    """S-1: ``user.resend_verification`` must store an email_hash, never raw email."""
    from models.auth import AuditLog

    svc, db, _email = deps
    await svc.resend_verification(db, email_addr="pii-resend@example.com", ip=None, ua=None)
    row = db.exec(select(AuditLog).where(AuditLog.event == "user.resend_verification")).one()
    assert "email" not in row.metadata_json
    assert "email_hash" in row.metadata_json


# ── S-3: 2FA setup must emit audit event ─────────────────────────────────────


@pytest.mark.asyncio
async def test_start_2fa_setup_emits_audit_event(deps, monkeypatch):
    """S-3: ``start_2fa_setup`` must emit ``user.2fa_setup_started``.

    Without this, an attacker with a stolen access token could silently rotate
    the TOTP secret and leave no trace for the user / admin to detect.
    """
    from cryptography.fernet import Fernet

    from models.auth import AuditLog
    from services.totp_service import TOTPService

    monkeypatch.setenv("SESSION_ENCRYPTION_KEY", Fernet.generate_key().decode())
    svc, db, email = deps
    # Wire a TOTPService into the existing AuthService (deps fixture omits it).
    svc.totp = TOTPService()
    await _make_verified_user(svc, db, email, "twofa-audit@example.com")
    user = db.exec(select(User).where(User.email == "twofa-audit@example.com")).one()
    svc.start_2fa_setup(db, user)
    rows = db.exec(select(AuditLog).where(AuditLog.event == "user.2fa_setup_started")).all()
    assert len(rows) == 1
    assert rows[0].user_id == user.id
    assert rows[0].metadata_json.get("user_id") == str(user.id)


# ── S-4: ``_audit`` partial-wiring guard must raise (not assert) ─────────────


def test_audit_partial_wiring_raises_runtime_error(deps):
    """S-4: ``background`` and ``db_factory`` must be passed together.

    A bare ``assert`` is stripped under ``python -O``; this test pins the
    explicit ``RuntimeError`` so the guard survives optimization.
    """
    svc, db, _email = deps
    db_factory_stub = lambda: db  # noqa: E731 — minimal callable for the test

    # background=None, db_factory=callable → must raise
    with pytest.raises(RuntimeError, match="background and db_factory must be passed together"):
        svc._audit(
            db,
            None,
            db_factory_stub,
            user_id=None,
            event="test.event",
            ip=None,
            user_agent=None,
            metadata={},
        )

    # Symmetric: background=object, db_factory=None → must raise
    class _FakeBg:
        def add_task(self, *args, **kwargs):
            pass

    with pytest.raises(RuntimeError, match="background and db_factory must be passed together"):
        svc._audit(
            db,
            _FakeBg(),  # type: ignore[arg-type]
            None,
            user_id=None,
            event="test.event",
            ip=None,
            user_agent=None,
            metadata={},
        )


@pytest.mark.asyncio
async def test_password_change_revokes_other_sessions_only(deps):
    svc, db, email = deps
    await _make_verified_user(svc, db, email, "ch@example.com")
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
