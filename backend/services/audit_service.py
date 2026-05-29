"""Synchronous (fail-closed) and BackgroundTasks-deferred audit logger.

The synchronous ``log`` path is preserved for direct callers (tests, anywhere
that needs an immediate, in-transaction insert). The new ``log_in_background``
path takes a ``BackgroundTasks`` instance and a session factory, registers the
insert to run *after* the HTTP response is sent, and opens its own ``Session``
inside the task body — the request-scoped session is already closed by the
time the task runs.

The point: eliminate the second per-request ``db.commit()`` (the audit row's
fsync) from the response latency path. Durability is preserved — the row still
lands, just after the user got their answer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Session, select

from models.auth import AuditLog

if TYPE_CHECKING:
    from fastapi import BackgroundTasks

    from database import DBSessionFactory

logger = logging.getLogger(__name__)


class AuditService:
    def log(
        self,
        db: Session,
        *,
        user_id: UUID | None,
        event: str,
        ip: str | None,
        user_agent: str | None,
        metadata: dict,
    ) -> None:
        """Synchronous insert + commit on the caller's session.

        Preserved for direct callers (unit tests of services, fallback when no
        ``BackgroundTasks`` is plumbed). Fail-closed: re-raises on insert
        failure so the caller can decide whether to suppress.
        """
        entry = AuditLog(
            user_id=user_id,
            event=event,
            ip_address=ip,
            user_agent=user_agent,
            metadata_json=metadata,
        )
        db.add(entry)
        db.commit()

    def log_in_background(
        self,
        background: BackgroundTasks,
        db_factory: DBSessionFactory,
        *,
        user_id: UUID | None,
        event: str,
        ip: str | None,
        user_agent: str | None,
        metadata: dict,
    ) -> None:
        """Schedule the audit-row insert to run after the response is sent.

        The task body opens a *fresh* session via the captured ``db_factory``
        — the per-request session is already closed by the time
        ``BackgroundTasks`` fires. Errors are logged (not raised) since there
        is no response left to fail.
        """
        background.add_task(
            self._persist_with_fresh_session,
            db_factory,
            user_id=user_id,
            event=event,
            ip=ip,
            user_agent=user_agent,
            metadata=metadata,
        )

    def _persist_with_fresh_session(
        self,
        db_factory: DBSessionFactory,
        *,
        user_id: UUID | None,
        event: str,
        ip: str | None,
        user_agent: str | None,
        metadata: dict,
    ) -> None:
        try:
            with db_factory() as db:
                self.log(
                    db,
                    user_id=user_id,
                    event=event,
                    ip=ip,
                    user_agent=user_agent,
                    metadata=metadata,
                )
        except Exception:
            # No response left to fail. Log and move on — losing one audit row
            # is better than crashing the worker on a closed DB / network blip.
            logger.exception("audit_service.background_log_failed event=%s", event)

    def query(
        self,
        db: Session,
        *,
        event: str | None = None,
        user_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        limit = max(1, min(200, limit))
        stmt = select(AuditLog)
        if event:
            stmt = stmt.where(AuditLog.event == event)
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        results = db.execute(stmt)
        return list(results.scalars().all())
