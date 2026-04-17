from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel

from models.auth import GUID


class ReportRecord(SQLModel, table=True):
    __tablename__ = "reports"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    pseudonym: str = Field(index=True)
    report_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_json: str  # full report as JSON string
    user_id: UUID = Field(sa_column=Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
