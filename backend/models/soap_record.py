from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class SOAPRecord(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    report_id: int | None = Field(default=None, index=True)
    session_id: str | None = Field(default=None, index=True)
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
