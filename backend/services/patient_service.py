from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, func, select

from models.patient import Patient
from services.encryption_service import EncryptionService


def derive_age_group(birthdate: str) -> str | None:
    """Map an ISO date of birth to a German logopedic age group.

    Returns "kind" (<13), "jugendlich" (13-17) or "erwachsen" (18+), or None if
    the birthdate cannot be parsed. Deriving from the DOB keeps the age group
    clinically correct instead of relying on a static "erwachsen" default.
    """
    try:
        dob = date.fromisoformat(birthdate.strip()[:10])
    except (ValueError, AttributeError):
        return None
    today = datetime.now(UTC).date()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if years < 13:
        return "kind"
    if years < 18:
        return "jugendlich"
    return "erwachsen"


_MAX_RETRIES = 5


class PatientService:
    def __init__(self, encryption: EncryptionService) -> None:
        self._enc = encryption

    def _next_system_id(self, db: Session, year: int) -> str:
        prefix = f"PAT-{year}-"
        # MAX+1 is safe against gaps from soft-deletes; COUNT+1 was not.
        max_val: str | None = db.exec(
            select(func.max(Patient.system_id)).where(col(Patient.system_id).startswith(prefix))
        ).one()
        seq = 1 if max_val is None else int(max_val.split("-")[-1]) + 1
        return f"{prefix}{seq:04d}"

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
        year = datetime.now(UTC).year
        kwargs = dict(
            user_id=user_id,
            realname_enc=self._enc.encrypt(realname),
            birthdate_enc=self._enc.encrypt(birthdate),
            phone_enc=self._enc.encrypt(phone),
            email_enc=self._enc.encrypt(email),
            insurance_nr_enc=self._enc.encrypt(insurance_nr),
            gender=gender,
            # Birthdate is authoritative for the age group; fall back to the
            # passed value only if the date can't be parsed (M-1).
            age_group=derive_age_group(birthdate) or age_group,
            icd10_codes=icd10_codes or [],
            disorder_text=disorder_text,
            indikationsschluessel=indikationsschluessel,
            insurance_type=insurance_type,
            insurance_name=insurance_name,
            guardian_name=guardian_name,
        )
        for _ in range(_MAX_RETRIES):
            system_id = self._next_system_id(db, year)
            patient = Patient(
                system_id=system_id,
                pseudonym=pseudonym or system_id,
                **kwargs,
            )
            db.add(patient)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                continue
            db.refresh(patient)
            return patient
        raise RuntimeError(f"Could not generate unique system_id after {_MAX_RETRIES} retries.")

    def update_patient(
        self,
        db: Session,
        patient: Patient,
        *,
        pseudonym: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        gender: str | None = None,
        age_group: str | None = None,
        icd10_codes: list[str] | None = None,
        disorder_text: str | None = None,
        indikationsschluessel: str | None = None,
        insurance_type: str | None = None,
        insurance_name: str | None = None,
        guardian_name: str | None = None,
    ) -> Patient:
        if pseudonym is not None:
            patient.pseudonym = pseudonym
        if phone is not None:
            patient.phone_enc = self._enc.encrypt(phone)
        if email is not None:
            patient.email_enc = self._enc.encrypt(email)
        if gender is not None:
            patient.gender = gender
        if age_group is not None:
            patient.age_group = age_group
        if icd10_codes is not None:
            patient.icd10_codes = icd10_codes
        if disorder_text is not None:
            patient.disorder_text = disorder_text
        if indikationsschluessel is not None:
            patient.indikationsschluessel = indikationsschluessel
        if insurance_type is not None:
            patient.insurance_type = insurance_type
        if insurance_name is not None:
            patient.insurance_name = insurance_name
        if guardian_name is not None:
            patient.guardian_name = guardian_name
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient

    def to_response(self, patient: Patient) -> dict[str, Any]:
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
