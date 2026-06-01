"""HTTP layer for /auth/* endpoints."""

from __future__ import annotations

import contextlib
import hmac
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import update as sa_update
from sqlmodel import Session, select

from database import DBSessionFactory, get_db, get_db_factory
from dependencies import get_auth_service, get_current_user
from exceptions import (
    AccountLockedError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    TokenInvalidError,
)
from middleware.rate_limiter import limiter
from models.auth import User, UserSession
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

GENERIC_REGISTER_MSG = "If the email is new, check your inbox to verify."


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)


class VerifyIn(BaseModel):
    token: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: str


class ResetRequestIn(BaseModel):
    email: EmailStr


class ResetConfirmIn(BaseModel):
    token: str
    new_password: str = Field(min_length=12)


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12)
    current_refresh_token: str | None = None


class ResendIn(BaseModel):
    email: EmailStr


def _client(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


def _err(exc: Exception, response: Response) -> dict:
    if isinstance(exc, InvalidCredentialsError):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "invalid_credentials"}
    if isinstance(exc, EmailNotVerifiedError):
        response.status_code = status.HTTP_403_FORBIDDEN
        return {"error": "email_not_verified"}
    if isinstance(exc, AccountLockedError):
        response.status_code = status.HTTP_423_LOCKED
        return {"error": "account_locked", "locked_until": exc.locked_until}
    if isinstance(exc, TokenInvalidError):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "token_invalid"}
    raise exc


@router.post("/register")
@limiter.limit("3/minute")
async def register(
    request: Request,
    body: RegisterIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    with contextlib.suppress(ValueError):
        await svc.register(
            db,
            email_addr=body.email,
            password=body.password,
            ip=ip,
            ua=ua,
            background=background_tasks,
            db_factory=db_factory,
        )
    return {"message": GENERIC_REGISTER_MSG}


@router.post("/verify-email")
@limiter.limit("10/minute")
def verify_email(
    body: VerifyIn,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    try:
        svc.verify_email(
            db,
            token=body.token,
            ip=ip,
            ua=ua,
            background=background_tasks,
            db_factory=db_factory,
        )
    except TokenInvalidError as e:
        return _err(e, response)
    return {"verified": True}


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    body: LoginIn,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    try:
        return svc.login(
            db,
            email_addr=body.email,
            password=body.password,
            ip=ip,
            ua=ua,
            background=background_tasks,
            db_factory=db_factory,
        )
    except (InvalidCredentialsError, EmailNotVerifiedError, AccountLockedError) as e:
        return _err(e, response)


class Login2faBody(BaseModel):
    challenge_id: str
    code: str


@router.post("/login/2fa")
@limiter.limit("5/minute")
def login_2fa(
    body: Login2faBody,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
    svc: AuthService = Depends(get_auth_service),
) -> dict:
    ip, ua = _client(request)
    return svc.login_2fa(
        db,
        challenge_id=body.challenge_id,
        code=body.code,
        ip=ip,
        ua=ua,
        background=background_tasks,
        db_factory=db_factory,
    )


@router.post("/refresh")
@limiter.limit("30/minute")
def refresh(
    request: Request,
    body: RefreshIn,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    try:
        return svc.refresh(
            db,
            refresh_token=body.refresh_token,
            ip=ip,
            ua=ua,
            background=background_tasks,
            db_factory=db_factory,
        )
    except TokenInvalidError as e:
        return _err(e, response)


@router.post("/logout")
@limiter.limit("30/minute")
def logout(
    request: Request,
    body: LogoutIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    svc.logout(
        db,
        refresh_token=body.refresh_token,
        ip=ip,
        ua=ua,
        background=background_tasks,
        db_factory=db_factory,
    )
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "totp_enabled": user.totp_enabled,
        "created_at": user.created_at.isoformat(),
    }


@router.post("/password/reset/request")
@limiter.limit("3/hour")
async def reset_request(
    request: Request,
    body: ResetRequestIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    await svc.request_password_reset(
        db,
        email_addr=body.email,
        ip=ip,
        ua=ua,
        background=background_tasks,
        db_factory=db_factory,
    )
    return {"message": GENERIC_REGISTER_MSG}


@router.post("/password/reset/confirm")
@limiter.limit("10/hour")
def reset_confirm(
    body: ResetConfirmIn,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    try:
        svc.confirm_password_reset(
            db,
            token=body.token,
            new_password=body.new_password,
            ip=ip,
            ua=ua,
            background=background_tasks,
            db_factory=db_factory,
        )
    except TokenInvalidError as e:
        return _err(e, response)
    return {"ok": True}


@router.post("/password/change")
@limiter.limit("5/minute")
def password_change(
    body: PasswordChangeIn,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    try:
        svc.change_password(
            db,
            user=user,
            current_password=body.current_password,
            new_password=body.new_password,
            current_refresh_token=body.current_refresh_token,
            ip=ip,
            ua=ua,
            background=background_tasks,
            db_factory=db_factory,
        )
    except InvalidCredentialsError as e:
        return _err(e, response)
    return {"ok": True}


@router.post("/resend-verification")
@limiter.limit("3/hour")
async def resend(
    body: ResendIn,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    await svc.resend_verification(
        db,
        email_addr=body.email,
        ip=ip,
        ua=ua,
        background=background_tasks,
        db_factory=db_factory,
    )
    return {"message": GENERIC_REGISTER_MSG}


# ── 2FA routes ────────────────────────────────────────────────────────────────


@router.post("/2fa/setup")
@limiter.limit("3/hour")
def twofa_setup(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    svc: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
) -> dict[str, str]:
    ip, ua = _client(request)
    return svc.start_2fa_setup(
        db,
        current_user,
        ip=ip,
        ua=ua,
        background=background_tasks,
        db_factory=db_factory,
    )


class TwoFaEnableBody(BaseModel):
    code: str


class TwoFaDisableBody(BaseModel):
    current_password: str
    code: str


@router.post("/2fa/disable")
@limiter.limit("5/minute")
def twofa_disable(
    body: TwoFaDisableBody,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    svc: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
) -> dict[str, str]:
    ip, ua = _client(request)
    svc.disable_2fa(
        db,
        current_user,
        body.current_password,
        body.code,
        ip=ip,
        ua=ua,
        background=background_tasks,
        db_factory=db_factory,
    )
    return {"status": "ok"}


@router.post("/2fa/enable")
@limiter.limit("5/minute")
def twofa_enable(
    body: TwoFaEnableBody,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    svc: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
    db_factory: DBSessionFactory = Depends(get_db_factory),
) -> dict[str, str]:
    # session_hash is the refresh_token_hash embedded in the JWT sid claim by the middleware
    current_user._current_session_hash = getattr(request.state, "session_hash", None)  # type: ignore[attr-defined]
    ip, ua = _client(request)
    svc.enable_2fa(
        db,
        current_user,
        body.code,
        ip=ip,
        ua=ua,
        background=background_tasks,
        db_factory=db_factory,
    )
    return {"status": "ok"}


# ── Sessions management ───────────────────────────────────────────────────────


@router.get("/sessions")
@limiter.limit("30/minute")
def list_sessions(
    request: Request,
    limit: int = Query(50, ge=1, le=200, description="Max rows to return (1-200, default 50)"),
    offset: int = Query(0, ge=0, description="Rows to skip for pagination (default 0)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    now = datetime.now(UTC)
    session_hash = getattr(request.state, "session_hash", None)
    rows = db.exec(
        select(UserSession)
        .where(
            UserSession.user_id == current_user.id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        .order_by(UserSession.last_used_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        {
            "id": str(s.id),
            "user_agent": s.user_agent,
            "ip_address": s.ip_address,
            "created_at": s.created_at.isoformat(),
            "last_used_at": s.last_used_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "is_current": bool(session_hash) and hmac.compare_digest(s.refresh_token_hash, session_hash),
        }
        for s in rows
    ]


@router.delete("/sessions/{session_id}")
@limiter.limit("30/minute")
def delete_session(
    request: Request,
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    now = datetime.now(UTC)
    result = db.execute(
        sa_update(UserSession)
        .where(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id,
            UserSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")
    db.commit()
    revoked = db.exec(select(UserSession).where(UserSession.id == session_id)).first()
    session_hash = getattr(request.state, "session_hash", None)
    current_revoked = (
        bool(session_hash) and revoked is not None and hmac.compare_digest(revoked.refresh_token_hash, session_hash)
    )
    return {"status": "ok", "current_session_revoked": current_revoked}
