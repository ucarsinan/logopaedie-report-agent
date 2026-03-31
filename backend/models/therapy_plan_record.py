from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class TherapyPlanRecord(SQLModel, table=True):
    __tablename__ = "therapyplanrecord"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    patient_pseudonym: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    report_id: Optional[int] = Field(default=None, foreign_key="reportrecord.id")
    plan_data: str  # full TherapyPlan as JSON string
