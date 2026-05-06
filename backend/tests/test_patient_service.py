from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from models.auth import User  # noqa: F401
from models.patient import Patient
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
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("PATIENT_ENCRYPTION_KEY", key)
    from services.encryption_service import EncryptionService

    return EncryptionService()


def test_generate_system_id_first_patient(engine, enc_svc):
    from services.patient_service import PatientService

    svc = PatientService(enc_svc)
    year = datetime.now(UTC).year
    with Session(engine) as db:
        sid = svc._next_system_id(db, year)
    assert sid == f"PAT-{year}-0001"


def test_generate_system_id_increments(engine, enc_svc):
    from services.patient_service import PatientService

    svc = PatientService(enc_svc)
    year = datetime.now(UTC).year
    user_id = uuid4()
    with Session(engine) as db:
        p = Patient(
            system_id=f"PAT-{year}-0001",
            pseudonym=f"PAT-{year}-0001",
            user_id=user_id,
            realname_enc=b"e",
            birthdate_enc=b"e",
        )
        db.add(p)
        db.commit()
        sid = svc._next_system_id(db, year)
    assert sid == f"PAT-{year}-0002"


def test_to_response_decrypts_pii(engine, enc_svc):
    from services.patient_service import PatientService

    svc = PatientService(enc_svc)
    user_id = uuid4()
    year = datetime.now(UTC).year
    with Session(engine) as db:
        p = Patient(
            system_id=f"PAT-{year}-0001",
            pseudonym="Sonnenschein",
            user_id=user_id,
            realname_enc=enc_svc.encrypt("Max Mustermann"),
            birthdate_enc=enc_svc.encrypt("2019-03-15"),
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        result = svc.to_response(p)
    assert result["realname"] == "Max Mustermann"
    assert result["birthdate"] == "2019-03-15"
    assert result["pseudonym"] == "Sonnenschein"
