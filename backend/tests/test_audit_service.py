import contextlib
import logging
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from models.auth import AuditLog, User
from services.audit_service import AuditService


@pytest.fixture
def engine():
    """In-memory SQLite engine with all SQLModel tables, shared across sessions."""
    # StaticPool: every Session opened against this engine sees the same
    # in-memory database. Required so the background task's fresh session
    # writes a row that the verification session can read.
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    with Session(engine) as session:
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


# ── T1: log_in_background end-to-end on direct call ──────────────────────────


@pytest.mark.asyncio
async def test_log_in_background_persists_via_fresh_session(engine):
    """Schedule an audit emit via BackgroundTasks, drive the queued task, and
    confirm the row landed using a *third* session.

    Critical lifecycle property under test: the captured ``db_factory`` must
    produce a *fresh* ``Session`` per invocation against the same engine.
    The test never reuses the request-time session for the background write
    (that would not exercise ``_persist_with_fresh_session``'s ``with
    db_factory() as db`` path).
    """
    # Pre-insert a user so user_id has a real FK target.
    with Session(engine) as setup_db:
        user = User(email="t1@example.com", password_hash="x")
        setup_db.add(user)
        setup_db.commit()
        setup_db.refresh(user)
        user_id = user.id

    @contextlib.contextmanager
    def db_factory() -> Iterator[Session]:
        # New Session per call, no outer-scope capture.
        with Session(engine) as session:
            yield session

    audit = AuditService()
    background = BackgroundTasks()

    audit.log_in_background(
        background,
        db_factory,
        user_id=user_id,
        event="t1.test_background_path",
        ip="10.0.0.1",
        user_agent="pytest-bg",
        metadata={"trace": "t1"},
    )

    # Nothing should have been written yet — log_in_background only schedules.
    with Session(engine) as pre_check:
        assert pre_check.exec(select(AuditLog)).first() is None

    # Drive the scheduled tasks exactly as FastAPI does after the response.
    await background()

    # Verify in a third, fresh session.
    with Session(engine) as verify_db:
        row = verify_db.exec(select(AuditLog)).one()
        assert row.user_id == user_id
        assert row.event == "t1.test_background_path"
        assert row.ip_address == "10.0.0.1"
        assert row.user_agent == "pytest-bg"
        assert row.metadata_json == {"trace": "t1"}


# ── T3: fail-open on DB-write failure ────────────────────────────────────────


def test_log_in_background_swallows_db_failure_and_logs(engine, monkeypatch, caplog):
    """If ``db.commit()`` raises inside the background task, the worker must
    not crash: the exception is swallowed and ``logger.exception`` is called
    with the event name.

    This is the complement to ``test_audit_log_failure_raises_fail_closed``
    (which pins the sync path's fail-closed contract). The background path
    has no response left to fail, so the contract is fail-open + structured
    log.
    """

    @contextlib.contextmanager
    def broken_db_factory() -> Iterator[Session]:
        # Fresh session, but ``commit`` is monkeypatched on the instance to
        # raise — simulates a closed/severed DB connection mid-task.
        with Session(engine) as session:

            def _raise_on_commit(*_args, **_kwargs):
                raise OperationalError("simulated", {}, Exception("connection closed"))

            monkeypatch.setattr(session, "commit", _raise_on_commit)
            yield session

    audit = AuditService()
    background = BackgroundTasks()
    audit.log_in_background(
        background,
        broken_db_factory,
        user_id=uuid4(),
        event="t3.simulated_failure",
        ip=None,
        user_agent=None,
        metadata={},
    )

    # alembic.ini's ``fileConfig`` (loaded by ``backend/alembic/env.py`` during
    # migration-related tests earlier in the suite) defaults to
    # ``disable_existing_loggers=True``, which leaves ``services.audit_service``
    # in a disabled state. Re-enable + force-propagate so caplog can capture.
    # Use monkeypatch so the mutation is restored at test teardown — leaking
    # ``disabled=False`` into later tests would silently re-enable a logger
    # alembic intentionally disabled.
    audit_logger = logging.getLogger("services.audit_service")
    monkeypatch.setattr(audit_logger, "disabled", False)
    monkeypatch.setattr(audit_logger, "propagate", True)

    # Drive the queued task directly. ``BackgroundTask`` exposes ``func``,
    # ``args``, ``kwargs`` — calling those mirrors what Starlette does at
    # request-end but lets us assert no exception escapes.
    task = background.tasks[0]
    with caplog.at_level(logging.ERROR, logger="services.audit_service"):
        # Must NOT raise — fail-open is the whole point.
        task.func(*task.args, **task.kwargs)

    # No row was committed.
    with Session(engine) as verify_db:
        assert verify_db.exec(select(AuditLog)).first() is None

    # logger.exception was called with the event name in the message.
    failure_records = [r for r in caplog.records if r.name == "services.audit_service" and r.levelno == logging.ERROR]
    assert failure_records, "expected an ERROR-level log from audit_service"
    msg = failure_records[0].getMessage()
    assert "audit_service.background_log_failed" in msg
    assert "t3.simulated_failure" in msg
    # logger.exception attaches the originating exception via exc_info.
    assert failure_records[0].exc_info is not None
    assert failure_records[0].exc_info[0] is OperationalError
