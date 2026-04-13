"""Schema-only tests for auth SQLModel classes."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from models.auth import AuditLog, EmailToken, User, UserSession


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    yield eng
    SQLModel.metadata.drop_all(eng)


def test_auth_models_create_all(engine):
    table_names = set(SQLModel.metadata.tables.keys())
    assert {"users", "user_sessions", "email_tokens", "audit_log"} <= table_names


def test_user_email_unique_constraint(engine):
    with Session(engine) as db:
        db.add(User(email="a@example.com", password_hash="x"))
        db.commit()
        db.add(User(email="a@example.com", password_hash="y"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_user_default_role_and_flags(engine):
    with Session(engine) as db:
        u = User(email="b@example.com", password_hash="x")
        db.add(u)
        db.commit()
        db.refresh(u)
        assert u.role == "user"
        assert u.email_verified is False
        assert u.totp_enabled is False
        assert u.failed_login_count == 0
        assert isinstance(u.id, UUID)


def test_audit_log_metadata_json_roundtrip(engine):
    with Session(engine) as db:
        entry = AuditLog(
            user_id=None,
            event="login.fail",
            ip_address="127.0.0.1",
            user_agent="pytest",
            metadata_json={"reason": "bad_password", "attempt": 3},
        )
        db.add(entry)
        db.commit()
        row = db.exec(select(AuditLog)).one()
        assert row.metadata_json == {"reason": "bad_password", "attempt": 3}


def test_user_sessions_indexes_present(engine):
    table = SQLModel.metadata.tables["user_sessions"]
    indexed = {col.name for col in table.columns if col.index}
    assert "user_id" in indexed
    assert "refresh_token_hash" in indexed


def test_email_token_purpose_and_expiry(engine):
    with Session(engine) as db:
        user = User(email="c@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        tok = EmailToken(
            user_id=user.id,
            token_hash="deadbeef",
            purpose="verify_email",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db.add(tok)
        db.commit()
        db.refresh(tok)
        assert tok.purpose == "verify_email"
        assert tok.used_at is None


def test_user_session_has_revoked_at_nullable(engine):
    with Session(engine) as db:
        user = User(email="d@example.com", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        sess = UserSession(
            user_id=user.id,
            refresh_token_hash="hash",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)
        assert sess.revoked_at is None
