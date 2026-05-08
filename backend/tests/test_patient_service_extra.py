"""Extra tests for PatientService.update_patient covering all optional branches."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from services.encryption_service import EncryptionService
from services.patient_service import PatientService


@pytest.fixture
def enc(monkeypatch):
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    monkeypatch.setenv("PATIENT_ENCRYPTION_KEY", key)
    return EncryptionService()


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def patient_record(db_engine, enc):
    """Create a base patient record for update tests."""
    svc = PatientService(enc)
    user_id = uuid4()
    with Session(db_engine) as db:
        patient = svc.create_patient(
            db,
            user_id,
            realname="Test Patient",
            birthdate="2000-01-01",
            pseudonym="T.P.",
            phone="+49123",
            email="test@example.com",
            insurance_nr="INS001",
            gender="männlich",
            age_group="erwachsen",
        )
    return patient, user_id


class TestUpdatePatient:
    def test_update_pseudonym(self, db_engine, enc, patient_record):
        svc = PatientService(enc)
        patient, _ = patient_record
        with Session(db_engine) as db:
            db.add(patient)
            updated = svc.update_patient(db, patient, pseudonym="New Name")
        assert updated.pseudonym == "New Name"

    def test_update_phone(self, db_engine, enc, patient_record):
        svc = PatientService(enc)
        patient, _ = patient_record
        with Session(db_engine) as db:
            db.add(patient)
            updated = svc.update_patient(db, patient, phone="+49999")
        decrypted = enc.decrypt(updated.phone_enc)
        assert decrypted == "+49999"

    def test_update_email(self, db_engine, enc, patient_record):
        svc = PatientService(enc)
        patient, _ = patient_record
        with Session(db_engine) as db:
            db.add(patient)
            updated = svc.update_patient(db, patient, email="new@example.com")
        assert enc.decrypt(updated.email_enc) == "new@example.com"

    def test_update_gender(self, db_engine, enc, patient_record):
        svc = PatientService(enc)
        patient, _ = patient_record
        with Session(db_engine) as db:
            db.add(patient)
            updated = svc.update_patient(db, patient, gender="weiblich")
        assert updated.gender == "weiblich"

    def test_update_age_group(self, db_engine, enc, patient_record):
        svc = PatientService(enc)
        patient, _ = patient_record
        with Session(db_engine) as db:
            db.add(patient)
            updated = svc.update_patient(db, patient, age_group="kind")
        assert updated.age_group == "kind"

    def test_update_icd10_codes(self, db_engine, enc, patient_record):
        svc = PatientService(enc)
        patient, _ = patient_record
        with Session(db_engine) as db:
            db.add(patient)
            updated = svc.update_patient(db, patient, icd10_codes=["F80.0", "F80.1"])
        assert updated.icd10_codes == ["F80.0", "F80.1"]

    def test_update_disorder_text(self, db_engine, enc, patient_record):
        svc = PatientService(enc)
        patient, _ = patient_record
        with Session(db_engine) as db:
            db.add(patient)
            updated = svc.update_patient(db, patient, disorder_text="Phonologische Störung")
        assert updated.disorder_text == "Phonologische Störung"

    def test_update_indikationsschluessel(self, db_engine, enc, patient_record):
        svc = PatientService(enc)
        patient, _ = patient_record
        with Session(db_engine) as db:
            db.add(patient)
            updated = svc.update_patient(db, patient, indikationsschluessel="SP1")
        assert updated.indikationsschluessel == "SP1"

    def test_update_insurance_type(self, db_engine, enc, patient_record):
        svc = PatientService(enc)
        patient, _ = patient_record
        with Session(db_engine) as db:
            db.add(patient)
            updated = svc.update_patient(db, patient, insurance_type="GKV")
        assert updated.insurance_type == "GKV"

    def test_update_insurance_name(self, db_engine, enc, patient_record):
        svc = PatientService(enc)
        patient, _ = patient_record
        with Session(db_engine) as db:
            db.add(patient)
            updated = svc.update_patient(db, patient, insurance_name="AOK")
        assert updated.insurance_name == "AOK"

    def test_update_guardian_name(self, db_engine, enc, patient_record):
        svc = PatientService(enc)
        patient, _ = patient_record
        with Session(db_engine) as db:
            db.add(patient)
            updated = svc.update_patient(db, patient, guardian_name="Maria M.")
        assert updated.guardian_name == "Maria M."

    def test_update_none_values_not_applied(self, db_engine, enc, patient_record):
        """Passing None should NOT overwrite existing values."""
        svc = PatientService(enc)
        patient, _ = patient_record
        original_gender = patient.gender
        with Session(db_engine) as db:
            db.add(patient)
            updated = svc.update_patient(db, patient)  # all kwargs are None
        assert updated.gender == original_gender
