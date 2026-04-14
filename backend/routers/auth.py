"""HTTP layer for /auth/* endpoints."""

from __future__ import annotations

import contextlib

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session

from database import get_db
from dependencies import get_auth_service, get_current_user
from exceptions import (
    AccountLockedError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    TokenInvalidError,
)
from middleware.rate_limiter import limiter
from models.auth import User
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
    return {"message": GENERIC_REGISTER_MSG}


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
