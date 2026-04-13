"""Business logic for register/verify/login/refresh/reset flows (no 2FA)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from exceptions import (
    AccountLockedError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    TokenInvalidError,
)
from models.auth import EmailToken, User, UserSession
from services.audit_service import AuditService
from services.email_service import EmailService, FakeEmailService
from services.password_service import PasswordService
from services.token_service import TokenService


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC). SQLite returns naive datetimes."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class AuthService:
    LOCKOUT_THRESHOLD = 10
    LOCKOUT_DURATION = timedelta(minutes=15)
    REFRESH_TTL = timedelta(days=7)
    RESET_TTL = timedelta(hours=1)

    def __init__(
        self,
        *,
        password: PasswordService,
        tokens: TokenService,
        email: EmailService | FakeEmailService,
        audit: AuditService,
    ) -> None:
        self.password = password
        self.tokens = tokens
        self.email = email
        self.audit = audit

    def _user_view(self, user: User) -> dict:
        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "totp_enabled": user.totp_enabled,
            "created_at": user.created_at.isoformat(),
        }

    # ---------- register + verify ----------

    def register(self, db: Session, *, email_addr: str, password: str, ip: str | None, ua: str | None) -> None:
        normalized = email_addr.strip().lower()
        if len(password) < 12:
            raise ValueError("password_too_short")
        existing = db.exec(select(User).where(User.email == normalized)).first()
        self.audit.log(
            db,
            user_id=existing.id if existing else None,
            event="user.register_attempt",
            ip=ip,
            user_agent=ua,
            metadata={"email": normalized},
        )
        if existing is not None:
            return
        user = User(email=normalized, password_hash=self.password.hash(password))
        db.add(user)
        db.commit()
        db.refresh(user)
        plain = secrets.token_urlsafe(32)
        db.add(
            EmailToken(
                user_id=user.id,
                token_hash=_sha256(plain),
                purpose="verify_email",
                expires_at=_utcnow() + timedelta(hours=24),
            )
        )
        db.commit()
        self.email.send_verify_email(normalized, plain)

    def verify_email(self, db: Session, *, token: str, ip: str | None, ua: str | None) -> None:
        token_hash = _sha256(token)
        row = db.exec(
            select(EmailToken).where(
                EmailToken.token_hash == token_hash,
                EmailToken.purpose == "verify_email",
            )
        ).first()
        if row is None or row.used_at is not None or _aware(row.expires_at) < _utcnow():
            raise TokenInvalidError()
        row.used_at = _utcnow()
        user = db.exec(select(User).where(User.id == row.user_id)).one()
        user.email_verified = True
        user.email_verified_at = _utcnow()
        user.updated_at = _utcnow()
        db.add(row)
        db.add(user)
        db.commit()
        self.audit.log(db, user_id=user.id, event="user.email_verified", ip=ip, user_agent=ua, metadata={})

    # ---------- login ----------

    def login(self, db: Session, *, email_addr: str, password: str, ip: str | None, ua: str | None) -> dict:
        normalized = email_addr.strip().lower()
        user = db.exec(select(User).where(User.email == normalized)).first()

        if user is None:
            # Equalize timing against dummy argon2 hash.
            self.password.verify(password, self.password.dummy_hash)
            self.audit.log(
                db, user_id=None, event="login.fail", ip=ip, user_agent=ua, metadata={"reason": "unknown_email"}
            )
            raise InvalidCredentialsError()

        if user.locked_until is not None and _aware(user.locked_until) > _utcnow():
            self.audit.log(db, user_id=user.id, event="login.fail", ip=ip, user_agent=ua, metadata={"reason": "locked"})
            raise AccountLockedError(locked_until=user.locked_until.isoformat())

        if not self.password.verify(password, user.password_hash):
            user.failed_login_count += 1
            if user.failed_login_count >= self.LOCKOUT_THRESHOLD:
                user.locked_until = _utcnow() + self.LOCKOUT_DURATION
            user.updated_at = _utcnow()
            db.add(user)
            db.commit()
            self.audit.log(
                db,
                user_id=user.id,
                event="login.fail",
                ip=ip,
                user_agent=ua,
                metadata={"reason": "bad_password", "attempts": user.failed_login_count},
            )
            raise InvalidCredentialsError()

        if not user.email_verified:
            self.audit.log(
                db, user_id=user.id, event="login.fail", ip=ip, user_agent=ua, metadata={"reason": "not_verified"}
            )
            raise EmailNotVerifiedError()

        user.failed_login_count = 0
        user.locked_until = None
        user.updated_at = _utcnow()
        db.add(user)

        plain_refresh, refresh_hash = self.tokens.encode_refresh()
        sess = UserSession(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            user_agent=ua,
            ip_address=ip,
            expires_at=_utcnow() + self.REFRESH_TTL,
        )
        db.add(sess)
        db.commit()
        self.audit.log(db, user_id=user.id, event="login.success", ip=ip, user_agent=ua, metadata={})
        return {
            "access_token": self.tokens.encode_access(user.id),
            "refresh_token": plain_refresh,
            "user": self._user_view(user),
        }

    # ---------- refresh rotation + reuse detection ----------

    def refresh(self, db: Session, *, refresh_token: str, ip: str | None, ua: str | None) -> dict:
        token_hash = self.tokens.hash_refresh(refresh_token)
        row = db.exec(select(UserSession).where(UserSession.refresh_token_hash == token_hash)).first()
        if row is None:
            raise TokenInvalidError()
        if row.revoked_at is not None:
            for s in db.exec(select(UserSession).where(UserSession.user_id == row.user_id)).all():
                if s.revoked_at is None:
                    s.revoked_at = _utcnow()
                    db.add(s)
            db.commit()
            self.audit.log(
                db,
                user_id=row.user_id,
                event="session.refresh_reuse_detected",
                ip=ip,
                user_agent=ua,
                metadata={"session_id": str(row.id)},
            )
            raise TokenInvalidError()
        if _aware(row.expires_at) < _utcnow():
            raise TokenInvalidError()

        row.revoked_at = _utcnow()
        db.add(row)
        new_plain, new_hash = self.tokens.encode_refresh()
        new_row = UserSession(
            user_id=row.user_id,
            refresh_token_hash=new_hash,
            user_agent=ua,
            ip_address=ip,
            expires_at=_utcnow() + self.REFRESH_TTL,
        )
        db.add(new_row)
        db.commit()
        user = db.exec(select(User).where(User.id == row.user_id)).one()
        return {
            "access_token": self.tokens.encode_access(user.id),
            "refresh_token": new_plain,
            "user": self._user_view(user),
        }

    # ---------- logout ----------

    def logout(self, db: Session, *, refresh_token: str, ip: str | None, ua: str | None) -> None:
        token_hash = self.tokens.hash_refresh(refresh_token)
        row = db.exec(select(UserSession).where(UserSession.refresh_token_hash == token_hash)).first()
        if row is not None and row.revoked_at is None:
            row.revoked_at = _utcnow()
            db.add(row)
            db.commit()
            self.audit.log(
                db, user_id=row.user_id, event="logout", ip=ip, user_agent=ua, metadata={"session_id": str(row.id)}
            )

    # ---------- password reset ----------

    def request_password_reset(self, db: Session, *, email_addr: str, ip: str | None, ua: str | None) -> None:
        normalized = email_addr.strip().lower()
        user = db.exec(select(User).where(User.email == normalized)).first()
        self.audit.log(
            db,
            user_id=user.id if user else None,
            event="password.reset_requested",
            ip=ip,
            user_agent=ua,
            metadata={"email": normalized},
        )
        if user is None:
            return
        plain = secrets.token_urlsafe(32)
        db.add(
            EmailToken(
                user_id=user.id,
                token_hash=_sha256(plain),
                purpose="reset_password",
                expires_at=_utcnow() + self.RESET_TTL,
            )
        )
        db.commit()
        self.email.send_password_reset(normalized, plain)

    def confirm_password_reset(
        self, db: Session, *, token: str, new_password: str, ip: str | None, ua: str | None
    ) -> None:
        if len(new_password) < 12:
            raise TokenInvalidError()
        token_hash = _sha256(token)
        row = db.exec(
            select(EmailToken).where(
                EmailToken.token_hash == token_hash,
                EmailToken.purpose == "reset_password",
            )
        ).first()
        if row is None or row.used_at is not None or _aware(row.expires_at) < _utcnow():
            raise TokenInvalidError()
        row.used_at = _utcnow()
        user = db.exec(select(User).where(User.id == row.user_id)).one()
        user.password_hash = self.password.hash(new_password)
        user.failed_login_count = 0
        user.locked_until = None
        user.updated_at = _utcnow()
        db.add(row)
        db.add(user)
        for s in db.exec(
            select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        ).all():
            s.revoked_at = _utcnow()
            db.add(s)
        db.commit()
        self.audit.log(db, user_id=user.id, event="password.reset_completed", ip=ip, user_agent=ua, metadata={})

    # ---------- password change ----------

    def change_password(
        self,
        db: Session,
        *,
        user: User,
        current_password: str,
        new_password: str,
        current_refresh_token: str | None,
        ip: str | None,
        ua: str | None,
    ) -> None:
        if not self.password.verify(current_password, user.password_hash):
            raise InvalidCredentialsError()
        if len(new_password) < 12:
            raise InvalidCredentialsError()
        user.password_hash = self.password.hash(new_password)
        user.updated_at = _utcnow()
        db.add(user)
        current_hash = self.tokens.hash_refresh(current_refresh_token) if current_refresh_token else None
        for s in db.exec(
            select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        ).all():
            if current_hash is None or s.refresh_token_hash != current_hash:
                s.revoked_at = _utcnow()
                db.add(s)
        db.commit()
        self.audit.log(db, user_id=user.id, event="password.change", ip=ip, user_agent=ua, metadata={})

    # ---------- resend verification ----------

    def resend_verification(self, db: Session, *, email_addr: str, ip: str | None, ua: str | None) -> None:
        normalized = email_addr.strip().lower()
        user = db.exec(select(User).where(User.email == normalized)).first()
        self.audit.log(
            db,
            user_id=user.id if user else None,
            event="user.resend_verification",
            ip=ip,
            user_agent=ua,
            metadata={"email": normalized},
        )
        if user is None or user.email_verified:
            return
        plain = secrets.token_urlsafe(32)
        db.add(
            EmailToken(
                user_id=user.id,
                token_hash=_sha256(plain),
                purpose="verify_email",
                expires_at=_utcnow() + timedelta(hours=24),
            )
        )
        db.commit()
        self.email.send_verify_email(normalized, plain)
