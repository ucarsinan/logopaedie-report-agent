"""Admin-only routes: audit log, lock/unlock users, force-disable 2FA."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import update as sa_update
from sqlmodel import Session

from database import get_db
from dependencies import get_admin_user, get_audit_service
from models.auth import User, UserSession
from services.audit_service import AuditService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit")
def list_audit(
    event: str | None = None,
    user_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    _: User = Depends(get_admin_user),
    audit: AuditService = Depends(get_audit_service),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = audit.query(db, event=event, user_id=user_id, limit=limit, offset=offset)
    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id) if r.user_id else None,
            "event": r.event,
            "ip_address": r.ip_address,
            "user_agent": r.user_agent,
            "metadata_json": r.metadata_json,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


class LockBody(BaseModel):
    duration_minutes: int


@router.post("/users/{user_id}/lock")
def lock_user(
    user_id: UUID,
    body: LockBody,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404)
    user.locked_until = datetime.now(UTC) + timedelta(minutes=body.duration_minutes)
    db.add(user)
    db.commit()
    audit.log(
        db,
        user_id=admin.id,
        event="admin.user_locked",
        ip=None,
        user_agent=None,
        metadata={"target_user_id": str(user_id)},
    )
    return {"status": "ok"}


@router.post("/users/{user_id}/unlock")
def unlock_user(
    user_id: UUID,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404)
    user.locked_until = None
    user.failed_login_count = 0
    db.add(user)
    db.commit()
    audit.log(
        db,
        user_id=admin.id,
        event="admin.user_unlocked",
        ip=None,
        user_agent=None,
        metadata={"target_user_id": str(user_id)},
    )
    return {"status": "ok"}


@router.post("/users/{user_id}/disable-2fa")
def admin_disable_2fa(
    user_id: UUID,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404)
    user.totp_secret = None
    user.totp_enabled = False
    user.last_totp_step = None
    db.add(user)
    now = datetime.now(UTC)
    db.execute(
        sa_update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=now)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    audit.log(
        db,
        user_id=admin.id,
        event="admin.2fa_disabled_by_admin",
        ip=None,
        user_agent=None,
        metadata={"admin_id": str(admin.id), "target_user_id": str(user_id)},
    )
    return {"status": "ok"}
