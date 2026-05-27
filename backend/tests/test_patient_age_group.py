"""M-1: a patient's age group must follow from their date of birth, not default
to 'erwachsen'. A child born in 2020 must not be classified as an adult.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from models.auth import User  # noqa: F401
from models.patient import Patient  # noqa: F401
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


@pytest.fixture
def enc_svc(monkeypatch):
    monkeypatch.setenv("PATIENT_ENCRYPTION_KEY", Fernet.generate_key().decode())
    from services.encryption_service import EncryptionService

    return EncryptionService()


@pytest.mark.parametrize(
    "birthdate,expected",
    [
        ("2020-01-15", "kind"),
        ("2011-06-01", "jugendlich"),
        ("1985-03-20", "erwachsen"),
    ],
)
def test_derive_age_group_from_birthdate(birthdate, expected):
    from services.patient_service import derive_age_group

    assert derive_age_group(birthdate) == expected


def test_derive_age_group_handles_unparseable():
    from services.patient_service import derive_age_group

    assert derive_age_group("not-a-date") is None


def test_create_patient_derives_age_group_for_child(engine, enc_svc):
    from services.patient_service import PatientService

    svc = PatientService(enc_svc)
    with Session(engine) as db:
        patient = svc.create_patient(
            db,
            user_id=uuid4(),
            realname="Kind Test",
            birthdate="2020-01-15",
        )
        assert patient.age_group == "kind"
