from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlmodel import Session, col, func, select

from database import get_db
from dependencies import get_audit_service, get_current_user, get_patient_service, get_report_comparator
from models.auth import User
from models.patient import ConsentRecord, Patient
from models.report_record import ReportRecord
from services.patient_service import PatientService
from services.report_comparator import ReportComparator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["patients"])
VALID_CONSENT_TYPES = {"data_processing", "ai_processing", "data_sharing"}


class CreatePatientRequest(BaseModel):
    realname: str
    birthdate: str
    pseudonym: str | None = None
    phone: str | None = None
    email: str | None = None
    insurance_nr: str | None = None
    gender: str | None = None
    age_group: str = "erwachsen"
    icd10_codes: list[str] = []
    disorder_text: str = ""
    indikationsschluessel: str = ""
    insurance_type: str | None = None
    insurance_name: str | None = None
    guardian_name: str | None = None


class UpdatePatientRequest(BaseModel):
    pseudonym: str | None = None
    phone: str | None = None
    email: str | None = None
    gender: str | None = None
    age_group: str | None = None
    icd10_codes: list[str] | None = None
    disorder_text: str | None = None
    indikationsschluessel: str | None = None
    insurance_type: str | None = None
    insurance_name: str | None = None
    guardian_name: str | None = None


class ConsentRequest(BaseModel):
    consent_type: str
    granted: bool


def _get_or_404(pid: UUID, user_id: UUID, db: Session) -> Patient:
    p = db.exec(select(Patient).where(Patient.id == pid, Patient.user_id == user_id)).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient nicht gefunden.")
    return p


def _get_active_or_404(pid: UUID, user_id: UUID, db: Session) -> Patient:
    p = db.exec(
        select(Patient).where(
            Patient.id == pid,
            Patient.user_id == user_id,
            Patient.deleted_at.is_(None),  # type: ignore[union-attr]
        )
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient nicht gefunden.")
    return p


@router.post("/patients", status_code=status.HTTP_201_CREATED)
def create_patient(
    req: CreatePatientRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    svc: PatientService = Depends(get_patient_service),
) -> dict[str, Any]:
    patient = svc.create_patient(
        db,
        current_user.id,
        realname=req.realname,
        birthdate=req.birthdate,
        pseudonym=req.pseudonym,
        phone=req.phone,
        email=req.email,
        insurance_nr=req.insurance_nr,
        gender=req.gender,
        age_group=req.age_group,
        icd10_codes=req.icd10_codes,
        disorder_text=req.disorder_text,
        indikationsschluessel=req.indikationsschluessel,
        insurance_type=req.insurance_type,
        insurance_name=req.insurance_name,
        guardian_name=req.guardian_name,
    )
    return svc.to_response(patient)


@router.get("/patients")
def list_patients(
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    svc: PatientService = Depends(get_patient_service),
) -> dict[str, Any]:
    query = select(Patient).where(Patient.user_id == current_user.id, Patient.deleted_at.is_(None))  # type: ignore[union-attr]
    if q:
        query = query.where(col(Patient.pseudonym).ilike(f"%{q}%") | col(Patient.system_id).ilike(f"%{q}%"))
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    patients = db.exec(query.order_by(col(Patient.created_at).desc()).offset((page - 1) * limit).limit(limit)).all()
    return {
        "items": [
            {
                "id": str(p.id),
                "system_id": p.system_id,
                "pseudonym": p.pseudonym,
                "age_group": p.age_group,
                "disorder_text": p.disorder_text,
                "created_at": p.created_at.isoformat(),
            }
            for p in patients
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/patients/{patient_id}")
def get_patient(
    patient_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    svc: PatientService = Depends(get_patient_service),
) -> dict[str, Any]:
    return svc.to_response(_get_or_404(patient_id, current_user.id, db))


@router.patch("/patients/{patient_id}")
def update_patient(
    patient_id: UUID,
    req: UpdatePatientRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    svc: PatientService = Depends(get_patient_service),
    audit=Depends(get_audit_service),
) -> dict[str, Any]:
    patient = _get_active_or_404(patient_id, current_user.id, db)
    patient = svc.update_patient(
        db,
        patient,
        pseudonym=req.pseudonym,
        phone=req.phone,
        email=req.email,
        gender=req.gender,
        age_group=req.age_group,
        icd10_codes=req.icd10_codes,
        disorder_text=req.disorder_text,
        indikationsschluessel=req.indikationsschluessel,
        insurance_type=req.insurance_type,
        insurance_name=req.insurance_name,
        guardian_name=req.guardian_name,
    )
    audit.log(
        db,
        user_id=current_user.id,
        event="patient_updated",
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"patient_id": str(patient_id)},
    )
    return svc.to_response(patient)


@router.delete("/patients/{patient_id}")
def delete_patient(
    patient_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    svc: PatientService = Depends(get_patient_service),
    audit=Depends(get_audit_service),
) -> dict[str, str]:
    patient = _get_active_or_404(patient_id, current_user.id, db)
    patient.deleted_at = datetime.now(UTC)
    db.add(patient)
    db.commit()
    audit.log(
        db,
        user_id=current_user.id,
        event="patient_deleted",
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        metadata={"patient_id": str(patient_id)},
    )
    return {"status": "deleted"}


@router.get("/patients/{patient_id}/history")
def get_history(
    patient_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _get_or_404(patient_id, current_user.id, db)
    reports = db.exec(
        select(ReportRecord)
        .where(ReportRecord.patient_id == patient_id, ReportRecord.user_id == current_user.id)
        .order_by(col(ReportRecord.created_at).desc())
    ).all()
    items = [
        {
            "type": "report",
            "id": r.id,
            "report_type": r.report_type,
            "pseudonym": r.pseudonym,
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]
    return {"items": items, "total": len(items)}


@router.get("/patients/{patient_id}/progress")
async def get_progress(
    patient_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    comparator: ReportComparator = Depends(get_report_comparator),
) -> dict[str, Any]:
    import json

    _get_or_404(patient_id, current_user.id, db)
    reports = db.exec(
        select(ReportRecord)
        .where(ReportRecord.patient_id == patient_id, ReportRecord.user_id == current_user.id)
        .order_by(col(ReportRecord.created_at).desc())
        .limit(2)
    ).all()
    if len(reports) < 2:
        return {"comparison": None, "message": "Mindestens 2 Berichte erforderlich."}
    comparison = await comparator.compare(json.loads(reports[1].content_json), json.loads(reports[0].content_json))
    return {"comparison": comparison.model_dump()}


@router.post("/patients/{patient_id}/consent", status_code=status.HTTP_201_CREATED)
def record_consent(
    patient_id: UUID,
    req: ConsentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if req.consent_type not in VALID_CONSENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Ungültiger consent_type. Erlaubt: {sorted(VALID_CONSENT_TYPES)}",
        )
    _get_or_404(patient_id, current_user.id, db)
    record = ConsentRecord(
        patient_id=patient_id,
        consent_type=req.consent_type,
        granted=req.granted,
        recorded_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "id": str(record.id),
        "consent_type": record.consent_type,
        "granted": record.granted,
        "granted_at": record.granted_at.isoformat(),
        "revoked_at": None,
    }
