"""Synchronous, fail-closed audit logger."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

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
