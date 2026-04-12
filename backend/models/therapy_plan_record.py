from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class TherapyPlanRecord(SQLModel, table=True):
    __tablename__ = "therapyplanrecord"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    patient_pseudonym: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    report_id: int | None = Field(default=None, foreign_key="reportrecord.id")
    plan_data: str  # full TherapyPlan as JSON string
