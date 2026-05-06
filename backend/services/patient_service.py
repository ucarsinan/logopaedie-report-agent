from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, col, func, select

from models.patient import Patient
from services.encryption_service import EncryptionService


class PatientService:
    def __init__(self, encryption: EncryptionService) -> None:
        self._enc = encryption

    def generate_system_id(self, db: Session, year: int) -> str:
        """Generate a unique system ID for a patient in the given year."""
        prefix = f"PAT-{year}-"
        count = db.exec(select(func.count(Patient.id)).where(col(Patient.system_id).startswith(prefix))).one()
        return f"{prefix}{count + 1:04d}"

    def create_patient(
        self,
        db: Session,
        user_id: UUID,
        *,
        realname: str,
        birthdate: str,
        pseudonym: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        insurance_nr: str | None = None,
        gender: str | None = None,
        age_group: str = "erwachsen",
        icd10_codes: list[str] | None = None,
        disorder_text: str = "",
        indikationsschluessel: str = "",
        insurance_type: str | None = None,
        insurance_name: str | None = None,
        guardian_name: str | None = None,
    ) -> Patient:
        """Create a new patient with encrypted PII fields."""
        year = datetime.now(UTC).year
        system_id = self.generate_system_id(db, year)
        patient = Patient(
            system_id=system_id,
            pseudonym=pseudonym or system_id,
            user_id=user_id,
            realname_enc=self._enc.encrypt(realname),
            birthdate_enc=self._enc.encrypt(birthdate),
            phone_enc=self._enc.encrypt(phone),
            email_enc=self._enc.encrypt(email),
            insurance_nr_enc=self._enc.encrypt(insurance_nr),
            gender=gender,
            age_group=age_group,
            icd10_codes=icd10_codes or [],
            disorder_text=disorder_text,
            indikationsschluessel=indikationsschluessel,
            insurance_type=insurance_type,
            insurance_name=insurance_name,
            guardian_name=guardian_name,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient

    def to_response(self, patient: Patient) -> dict:
        """Convert patient to response dict with decrypted PII fields."""
        return {
            "id": str(patient.id),
            "system_id": patient.system_id,
            "pseudonym": patient.pseudonym,
            "realname": self._enc.decrypt(patient.realname_enc),
            "birthdate": self._enc.decrypt(patient.birthdate_enc),
            "phone": self._enc.decrypt(patient.phone_enc),
            "email": self._enc.decrypt(patient.email_enc),
            "insurance_nr": self._enc.decrypt(patient.insurance_nr_enc),
            "gender": patient.gender,
            "age_group": patient.age_group,
            "icd10_codes": patient.icd10_codes,
            "disorder_text": patient.disorder_text,
            "indikationsschluessel": patient.indikationsschluessel,
            "insurance_type": patient.insurance_type,
            "insurance_name": patient.insurance_name,
            "guardian_name": patient.guardian_name,
            "created_at": patient.created_at.isoformat(),
            "deleted_at": patient.deleted_at.isoformat() if patient.deleted_at else None,
        }
