from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class ReportRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pseudonym: str = Field(index=True)
    report_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content_json: str  # full report as JSON string
