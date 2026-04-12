from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class SOAPRecord(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: Optional[int] = Field(default=None, index=True)
    session_id: Optional[str] = Field(default=None, index=True)
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
