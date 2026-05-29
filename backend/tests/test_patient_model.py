from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from models.auth import User  # noqa: F401
from models.patient import ConsentRecord, Patient
from models.report_record import ReportRecord  # noqa: F401


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    yield eng
    SQLModel.metadata.drop_all(eng)


def test_patient_can_be_created(engine):
    user_id = uuid4()
    with Session(engine) as db:
        p = Patient(
            system_id="PAT-2026-0001",
            pseudonym="PAT-2026-0001",
            user_id=user_id,
            realname_enc=b"enc",
            birthdate_enc=b"enc",
            age_group="kind",
        )
        db.add(p)
        db.commit()
        db.refresh(p)
    assert p.id is not None
    assert p.deleted_at is None


def test_patient_pseudonym_has_no_standalone_index(engine):
    """Guard against re-introducing `index=True` on Patient.pseudonym.

    The composite `idx_patients_user_active` from migration 0011 already covers
    the only access path that scopes by user_id; the search endpoint uses
    `ILIKE '%q%'` which a plain B-tree cannot serve. Resolution recorded in
    docs/ai/AUDIT_2026-05-29_schema.md.
    """
    indexes = SQLModel.metadata.tables["patients"].indexes
    # No single-column index over only `pseudonym` should exist.
    pseudonym_only = [ix for ix in indexes if {col.name for col in ix.columns} == {"pseudonym"}]
    assert pseudonym_only == [], f"Patient.pseudonym should not declare a standalone index; found {pseudonym_only}"


def test_consent_links_to_patient(engine):
    user_id = uuid4()
    with Session(engine) as db:
        p = Patient(
            system_id="PAT-2026-0001",
            pseudonym="PAT-2026-0001",
            user_id=user_id,
            realname_enc=b"enc",
            birthdate_enc=b"enc",
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        patient_id = p.id  # capture before second commit expires p
        c = ConsentRecord(patient_id=patient_id, consent_type="data_processing", granted=True, recorded_by=user_id)
        db.add(c)
        db.commit()
        db.refresh(c)
        consent_patient_id = c.patient_id
        consent_revoked_at = c.revoked_at
    assert consent_patient_id == patient_id
    assert consent_revoked_at is None
