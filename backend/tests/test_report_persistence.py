"""Tests for ReportRecord persistence layer."""
from __future__ import annotations

import json
import pytest
from sqlmodel import Session, SQLModel, create_engine

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})


from backend.models.report_record import ReportRecord  # noqa: E402 — must be imported before create_all


@pytest.fixture(autouse=True)
def setup_tables():
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


def test_report_record_can_be_created():

    with Session(test_engine) as db:
        record = ReportRecord(
            pseudonym="Max M.",
            report_type="befundbericht",
            content_json=json.dumps({"report_type": "befundbericht", "patient": {"pseudonym": "Max M."}}),
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    assert record.id is not None
    assert record.pseudonym == "Max M."
    assert record.report_type == "befundbericht"
    assert record.created_at is not None
