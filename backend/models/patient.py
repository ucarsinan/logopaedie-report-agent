from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, LargeBinary, String
from sqlmodel import JSON, Field, SQLModel

from models.auth import GUID


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Patient(SQLModel, table=True):
    __tablename__ = "patients"
    __table_args__ = {"extend_existing": True}

    id: UUID = Field(default_factory=uuid4, sa_column=Column(GUID, primary_key=True))
    system_id: str = Field(index=True, unique=True)
    # No index here: every read of `pseudonym` is scoped to user_id (see
    # routers/patients.py list_patients), so the composite
    # `idx_patients_user_active` (user_id, created_at DESC) WHERE deleted_at IS NULL
    # from migration 0011 already covers the access path. The only other
    # predicate is an ILIKE '%q%' search whose leading wildcard a plain B-tree
    # cannot serve anyway — a trigram (gin_trgm_ops) index would be required if
    # that ever becomes hot. Declaration history: had `index=True` until
    # 2026-05-29, but no migration ever emitted `ix_patients_pseudonym`.
    pseudonym: str = Field()
    user_id: UUID = Field(
        sa_column=Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    )

    realname_enc: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    birthdate_enc: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    phone_enc: bytes | None = Field(default=None, sa_column=Column(LargeBinary, nullable=True))
    email_enc: bytes | None = Field(default=None, sa_column=Column(LargeBinary, nullable=True))
    insurance_nr_enc: bytes | None = Field(default=None, sa_column=Column(LargeBinary, nullable=True))

    gender: str | None = Field(default=None, sa_type=String(20))  # type: ignore[call-overload]
    age_group: str = Field(default="erwachsen", sa_type=String(20))  # type: ignore[call-overload]
    icd10_codes: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    disorder_text: str = Field(default="")
    indikationsschluessel: str = Field(default="", sa_type=String(10))  # type: ignore[call-overload]

    insurance_type: str | None = Field(default=None, sa_type=String(10))  # type: ignore[call-overload]
    insurance_name: str | None = Field(default=None)
    guardian_name: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    deleted_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))


class ConsentRecord(SQLModel, table=True):
    __tablename__ = "consent_records"
    __table_args__ = {"extend_existing": True}

    id: UUID = Field(default_factory=uuid4, sa_column=Column(GUID, primary_key=True))
    patient_id: UUID = Field(
        sa_column=Column(GUID(), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    consent_type: str = Field(sa_type=String(30))  # type: ignore[call-overload]
    granted: bool
    granted_at: datetime = Field(default_factory=_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))
    revoked_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    # RESTRICT: consent records are audit trails and must survive user deletion attempts
    recorded_by: UUID = Field(sa_column=Column(GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False))
