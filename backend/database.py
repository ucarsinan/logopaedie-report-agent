from __future__ import annotations

import contextlib
import os
from collections.abc import Callable, Iterator

from fastapi import Request
from sqlmodel import Session, SQLModel, create_engine

# Import all models so SQLModel registers their tables
import models.auth
import models.report_record
import models.soap_record
import models.therapy_plan_record  # noqa: F401

DATABASE_URL: str = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or "sqlite:///./reports.db"

# Neon uses postgres:// — SQLAlchemy requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
pool_kwargs: dict = (
    {}
    if DATABASE_URL.startswith("sqlite")
    else {
        # Neon serverless closes idle connections; reconnect transparently
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
)
engine = create_engine(DATABASE_URL, connect_args=connect_args, **pool_kwargs)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_db():
    with Session(engine) as session:
        yield session


# ── BackgroundTasks helper ─────────────────────────────────────────────────────
#
# Audit writes run in FastAPI BackgroundTasks (after the response is sent) so
# their `db.commit()` no longer adds an fsync to the response path. The
# background task cannot reuse the request-scoped session (it's already closed),
# so it needs to open its own. Capturing the *currently active* ``get_db``
# (including any ``dependency_overrides[get_db]`` set by a test fixture) means
# the audit row durably lands in the same engine the rest of the request used —
# without having to wire a parallel override on every test fixture.
SessionContext = contextlib.AbstractContextManager[Session]
DBSessionFactory = Callable[[], SessionContext]


def get_db_factory(request: Request) -> DBSessionFactory:
    """Return a callable producing a fresh ``Session`` context manager.

    Resolves the active ``get_db`` (respecting ``dependency_overrides``) at
    request time so background tasks scheduled from the request can open their
    own session against the same engine. The returned factory yields a context
    manager so callers don't have to manage close/finalize semantics.
    """
    overridden = request.app.dependency_overrides.get(get_db, get_db)

    @contextlib.contextmanager
    def _factory() -> Iterator[Session]:
        gen = overridden()
        session = next(gen)
        try:
            yield session
        finally:
            # Drive the generator to completion so any ``finally`` (and the
            # ``Session.__exit__`` inside ``with Session(...)``) runs.
            with contextlib.suppress(StopIteration):
                next(gen)

    return _factory
