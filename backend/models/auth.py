"""SQLModel tables for multi-user authentication."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CHAR, Column, DateTime, ForeignKey, String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import JSON, Field, SQLModel


class GUID(TypeDecorator):
    """Platform-independent GUID type that uses CHAR(36) on SQLite and UUID on PostgreSQL."""

    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, UUID):
            if dialect.name == "postgresql":
                return value
            return str(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return UUID(value) if not isinstance(value, UUID) else value


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, sa_column=Column(GUID, primary_key=True))
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="user", sa_type=String(50))  # type: ignore[call-overload]
    email_verified: bool = Field(default=False)
    email_verified_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    totp_secret: str | None = Field(default=None)
    totp_enabled: bool = Field(default=False)
    last_totp_step: int | None = Field(default=None)  # replay-prevention: last accepted TOTP step counter
    failed_login_count: int = Field(default=0)
    locked_until: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            onupdate=_utcnow,
        ),
    )


class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"

    id: UUID = Field(default_factory=uuid4, sa_column=Column(GUID, primary_key=True))
    user_id: UUID = Field(
        sa_column=Column(
            GUID,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    refresh_token_hash: str = Field(index=True)
    user_agent: str | None = Field(default=None)
    ip_address: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    last_used_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    revoked_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    rotated: bool = Field(default=False)  # True only when revoked via token rotation (enables reuse detection)


class EmailToken(SQLModel, table=True):
    __tablename__ = "email_tokens"

    id: UUID = Field(default_factory=uuid4, sa_column=Column(GUID, primary_key=True))
    user_id: UUID = Field(
        sa_column=Column(
            GUID,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    token_hash: str = Field(index=True)
    purpose: str = Field(sa_type=String(50))  # type: ignore[call-overload]
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    used_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: UUID = Field(default_factory=uuid4, sa_column=Column(GUID, primary_key=True))
    user_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            GUID,
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    event: str = Field(index=True)
    ip_address: str | None = Field(default=None)
    user_agent: str | None = Field(default=None)
    metadata_json: dict = Field(
        default_factory=dict,
        sa_column=Column("metadata_json", JSON, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
