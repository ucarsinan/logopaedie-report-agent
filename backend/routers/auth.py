"""HTTP layer for /auth/* endpoints."""

from __future__ import annotations

import contextlib
import hmac
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import update as sa_update
from sqlmodel import Session, select

from database import get_db
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
def register(
    request: Request,
    body: RegisterIn,
    db: Session = Depends(get_db),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    with contextlib.suppress(ValueError):
        svc.register(db, email_addr=body.email, password=body.password, ip=ip, ua=ua)
    return {"message": GENERIC_REGISTER_MSG, "auto_verified": svc.auto_verify}


@router.post("/verify-email")
def verify_email(
    body: VerifyIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    try:
        svc.verify_email(db, token=body.token, ip=ip, ua=ua)
    except TokenInvalidError as e:
        return _err(e, response)
    return {"verified": True}


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    body: LoginIn,
    response: Response,
    db: Session = Depends(get_db),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    try:
        return svc.login(db, email_addr=body.email, password=body.password, ip=ip, ua=ua)
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
    db: Session = Depends(get_db),
    svc: AuthService = Depends(get_auth_service),
) -> dict:
    ip, ua = _client(request)
    return svc.login_2fa(db, challenge_id=body.challenge_id, code=body.code, ip=ip, ua=ua)


@router.post("/refresh")
@limiter.limit("30/minute")
def refresh(
    request: Request,
    body: RefreshIn,
    response: Response,
    db: Session = Depends(get_db),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    try:
        return svc.refresh(db, refresh_token=body.refresh_token, ip=ip, ua=ua)
    except TokenInvalidError as e:
        return _err(e, response)


@router.post("/logout")
def logout(
    body: LogoutIn,
    request: Request,
    db: Session = Depends(get_db),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    svc.logout(db, refresh_token=body.refresh_token, ip=ip, ua=ua)
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
def reset_request(
    request: Request,
    body: ResetRequestIn,
    db: Session = Depends(get_db),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    svc.request_password_reset(db, email_addr=body.email, ip=ip, ua=ua)
    return {"message": GENERIC_REGISTER_MSG}


@router.post("/password/reset/confirm")
def reset_confirm(
    body: ResetConfirmIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    try:
        svc.confirm_password_reset(db, token=body.token, new_password=body.new_password, ip=ip, ua=ua)
    except TokenInvalidError as e:
        return _err(e, response)
    return {"ok": True}


@router.post("/password/change")
def password_change(
    body: PasswordChangeIn,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
        )
    except InvalidCredentialsError as e:
        return _err(e, response)
    return {"ok": True}


@router.post("/resend-verification")
def resend(
    body: ResendIn,
    request: Request,
    db: Session = Depends(get_db),
    svc: AuthService = Depends(get_auth_service),
):
    ip, ua = _client(request)
    svc.resend_verification(db, email_addr=body.email, ip=ip, ua=ua)
    return {"message": GENERIC_REGISTER_MSG}


# ── 2FA routes ────────────────────────────────────────────────────────────────


@router.post("/2fa/setup")
def twofa_setup(
    current_user: User = Depends(get_current_user),
    svc: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    return svc.start_2fa_setup(db, current_user)


class TwoFaEnableBody(BaseModel):
    code: str


class TwoFaDisableBody(BaseModel):
    current_password: str
    code: str


@router.post("/2fa/disable")
def twofa_disable(
    body: TwoFaDisableBody,
    request: Request,
    current_user: User = Depends(get_current_user),
    svc: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    ip, ua = _client(request)
    svc.disable_2fa(db, current_user, body.current_password, body.code, ip=ip, ua=ua)
    return {"status": "ok"}


@router.post("/2fa/enable")
def twofa_enable(
    body: TwoFaEnableBody,
    request: Request,
    current_user: User = Depends(get_current_user),
    svc: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    # session_hash is the refresh_token_hash embedded in the JWT sid claim by the middleware
    current_user._current_session_hash = getattr(request.state, "session_hash", None)  # type: ignore[attr-defined]
    ip, ua = _client(request)
    svc.enable_2fa(db, current_user, body.code, ip=ip, ua=ua)
    return {"status": "ok"}


# ── Sessions management ───────────────────────────────────────────────────────


@router.get("/sessions")
def list_sessions(
    request: Request,
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
def delete_session(
    session_id: UUID,
    request: Request,
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
