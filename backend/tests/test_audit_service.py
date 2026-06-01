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


# ── query() ──────────────────────────────────────────────────────────────────
#
# AuditService.query supports: ``event``, ``user_id``, ``limit``, ``offset``.
# There is NO time-range filter on the current API surface (verified by reading
# the implementation). If/when ``since``/``until`` are added, extend these
# tests rather than introducing a parallel suite.


def _insert_audit(
    db: Session,
    *,
    user_id,
    event: str,
    ip: str | None = None,
    user_agent: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Tiny helper: commit one AuditLog row via the service.

    Uses ``AuditService.log`` directly so we exercise the same insertion path
    the production code uses (rather than constructing rows manually and
    bypassing the service contract).
    """
    AuditService().log(
        db,
        user_id=user_id,
        event=event,
        ip=ip,
        user_agent=user_agent,
        metadata=metadata or {},
    )


def test_query_filter_by_user_id(db):
    """``user_id`` narrows to rows owned by that user only."""
    user_a = User(email="qa@example.com", password_hash="x")
    user_b = User(email="qb@example.com", password_hash="x")
    db.add(user_a)
    db.add(user_b)
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    for i in range(3):
        _insert_audit(db, user_id=user_a.id, event=f"a.event.{i}")
    for i in range(2):
        _insert_audit(db, user_id=user_b.id, event=f"b.event.{i}")

    results = AuditService().query(db, user_id=user_a.id)
    assert len(results) == 3
    assert {row.user_id for row in results} == {user_a.id}


def test_query_filter_by_event(db):
    """``event`` narrows to that exact event name (the param is ``event``, not ``event_type``)."""
    user = User(email="qe@example.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    _insert_audit(db, user_id=user.id, event="login.success")
    _insert_audit(db, user_id=user.id, event="login.success")
    _insert_audit(db, user_id=user.id, event="login.fail")
    _insert_audit(db, user_id=user.id, event="logout")

    results = AuditService().query(db, event="login.success")
    assert len(results) == 2
    assert {row.event for row in results} == {"login.success"}


def test_query_filter_combined_user_and_event(db):
    """Combining ``user_id`` and ``event`` AND-s the filters."""
    user_a = User(email="qc1@example.com", password_hash="x")
    user_b = User(email="qc2@example.com", password_hash="x")
    db.add(user_a)
    db.add(user_b)
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    _insert_audit(db, user_id=user_a.id, event="login.success")
    _insert_audit(db, user_id=user_a.id, event="login.fail")
    _insert_audit(db, user_id=user_b.id, event="login.success")

    results = AuditService().query(db, user_id=user_a.id, event="login.success")
    assert len(results) == 1
    assert results[0].user_id == user_a.id
    assert results[0].event == "login.success"


def test_query_pagination(db):
    """``limit`` + ``offset`` walk the result set in newest-first chunks."""
    user = User(email="qp@example.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    for i in range(5):
        _insert_audit(db, user_id=user.id, event=f"paginate.{i}")

    svc = AuditService()
    page_a = svc.query(db, user_id=user.id, limit=2, offset=0)
    page_b = svc.query(db, user_id=user.id, limit=2, offset=2)
    page_c = svc.query(db, user_id=user.id, limit=2, offset=4)

    assert len(page_a) == 2
    assert len(page_b) == 2
    assert len(page_c) == 1

    # Pages must be disjoint — every row id appears in at most one page.
    ids_a = {row.id for row in page_a}
    ids_b = {row.id for row in page_b}
    ids_c = {row.id for row in page_c}
    assert ids_a.isdisjoint(ids_b)
    assert ids_b.isdisjoint(ids_c)
    assert ids_a.isdisjoint(ids_c)
    # Union covers all 5 rows we inserted.
    assert ids_a | ids_b | ids_c == {row.id for row in db.exec(select(AuditLog)).all()}


def test_query_orders_newest_first(db):
    """``created_at DESC`` — the most recently inserted row leads the page."""
    user = User(email="qo@example.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    _insert_audit(db, user_id=user.id, event="ordering.first")
    _insert_audit(db, user_id=user.id, event="ordering.second")
    _insert_audit(db, user_id=user.id, event="ordering.third")

    results = AuditService().query(db, user_id=user.id)
    # newest first → last inserted is at index 0
    assert results[0].event == "ordering.third"
    assert results[-1].event == "ordering.first"
    # Monotonically non-increasing timestamps.
    timestamps = [r.created_at for r in results]
    assert timestamps == sorted(timestamps, reverse=True)


def test_query_limit_is_clamped_to_safe_range(db):
    """``limit`` is clamped to [1, 200] regardless of caller input.

    Pins the defensive clamp in the implementation — a caller passing
    ``limit=0`` or ``limit=10_000`` should not be able to wedge or DoS the
    audit endpoint.
    """
    user = User(email="qlc@example.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    _insert_audit(db, user_id=user.id, event="clamp.row")

    svc = AuditService()
    # limit=0 -> clamped up to 1
    assert len(svc.query(db, user_id=user.id, limit=0)) == 1
    # limit=10_000 -> clamped down to 200 (we only have 1 row, so still 1, but it does not raise)
    assert len(svc.query(db, user_id=user.id, limit=10_000)) == 1
