"""SOAP notes endpoints."""

import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_db
from dependencies import get_current_user, get_soap_generator
from models.auth import User
from models.report_record import ReportRecord
from models.soap_record import SOAPRecord
from services.session_store import SessionStore
from services.soap_generator import SOAPGenerator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["soap"])

_store = SessionStore()
_SESSION_ID_PATTERN = re.compile(r"^[0-9a-f]{12}$")


class SOAPUpdateRequest(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str


def _validate_session_id(session_id: str) -> None:
    if not _SESSION_ID_PATTERN.match(session_id):
        raise HTTPException(status_code=400, detail="Ungültige Session-ID.")


def _serialize_soap(record: SOAPRecord) -> dict:
    return {
        "id": record.id,
        "session_id": record.session_id,
        "report_id": record.report_id,
        "subjective": record.subjective,
        "objective": record.objective,
        "assessment": record.assessment,
        "plan": record.plan,
        "created_at": record.created_at.isoformat(),
    }


@router.post("/sessions/{session_id}/soap")
async def generate_soap_from_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    soap_gen: SOAPGenerator = Depends(get_soap_generator),
    db: Session = Depends(get_db),
):
    _validate_session_id(session_id)
    session = _store.get_authorized(session_id, str(current_user.id))

    collected_data = session.collected_data
    report = session.generated_report

    result = await soap_gen.generate_from_data(collected_data, report)

    # Persist
    record = SOAPRecord(
        session_id=session_id,
        user_id=current_user.id,
        subjective=result["subjective"],
        objective=result["objective"],
        assessment=result["assessment"],
        plan=result["plan"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return _serialize_soap(record)


@router.post("/reports/{report_id}/soap")
async def generate_soap_from_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    soap_gen: SOAPGenerator = Depends(get_soap_generator),
    db: Session = Depends(get_db),
):
    record = db.exec(
        select(ReportRecord).where(ReportRecord.id == report_id, ReportRecord.user_id == current_user.id)
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden.")

    report = json.loads(record.content_json)
    result = await soap_gen.generate_from_data({}, report)

    soap_record = SOAPRecord(
        report_id=report_id,
        user_id=current_user.id,
        subjective=result["subjective"],
        objective=result["objective"],
        assessment=result["assessment"],
        plan=result["plan"],
    )
    db.add(soap_record)
    db.commit()
    db.refresh(soap_record)

    return _serialize_soap(soap_record)


@router.get("/reports/{report_id}/soap")
async def get_soap_for_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.exec(
        select(SOAPRecord)
        .where(SOAPRecord.report_id == report_id, SOAPRecord.user_id == current_user.id)
        .order_by(SOAPRecord.created_at.desc())
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Keine SOAP-Notiz für diesen Bericht.")
    return _serialize_soap(record)


@router.get("/soap/{soap_id}")
async def get_soap_note(
    soap_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.exec(select(SOAPRecord).where(SOAPRecord.id == soap_id, SOAPRecord.user_id == current_user.id)).first()
    if not record:
        raise HTTPException(status_code=404, detail="SOAP-Notiz nicht gefunden.")

    return _serialize_soap(record)


@router.put("/soap/{soap_id}")
async def update_soap_note(
    soap_id: int,
    req: SOAPUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.exec(select(SOAPRecord).where(SOAPRecord.id == soap_id, SOAPRecord.user_id == current_user.id)).first()
    if not record:
        raise HTTPException(status_code=404, detail="SOAP-Notiz nicht gefunden.")

    record.subjective = req.subjective
    record.objective = req.objective
    record.assessment = req.assessment
    record.plan = req.plan
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize_soap(record)
