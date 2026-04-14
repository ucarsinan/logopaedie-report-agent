"""Synchronous, fail-closed audit logger."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from models.auth import AuditLog


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
        entry = AuditLog(
            user_id=user_id,
            event=event,
            ip_address=ip,
            user_agent=user_agent,
            metadata_json=metadata,
        )
        db.add(entry)
        db.commit()

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
