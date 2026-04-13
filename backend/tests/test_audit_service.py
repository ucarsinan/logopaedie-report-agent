import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from models.auth import AuditLog, User
from services.audit_service import AuditService


@pytest.fixture
def db():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    with Session(eng) as session:
        yield session


def test_audit_log_insert_writes_row(db):
    user = User(email="a@example.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    AuditService().log(
        db,
        user_id=user.id,
        event="login.success",
        ip="1.2.3.4",
        user_agent="pytest",
        metadata={"ok": True},
    )
    row = db.exec(select(AuditLog)).one()
    assert row.event == "login.success"
    assert row.ip_address == "1.2.3.4"
    assert row.metadata_json == {"ok": True}


def test_audit_log_user_id_nullable(db):
    AuditService().log(
        db,
        user_id=None,
        event="login.fail",
        ip="1.2.3.4",
        user_agent="pytest",
        metadata={"reason": "bad_password"},
    )
    row = db.exec(select(AuditLog)).one()
    assert row.user_id is None


def test_audit_log_failure_raises_fail_closed(db):
    class BrokenSession:
        def add(self, *_args, **_kwargs):
            raise RuntimeError("db down")

        def commit(self):
            raise RuntimeError("db down")

    with pytest.raises(RuntimeError, match="db down"):
        AuditService().log(
            BrokenSession(),  # type: ignore[arg-type]
            user_id=None,
            event="test.event",
            ip=None,
            user_agent=None,
            metadata={},
        )
