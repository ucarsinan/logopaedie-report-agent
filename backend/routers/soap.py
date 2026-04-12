"""SOAP notes endpoints."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from database import get_db
from dependencies import get_soap_generator
from models.report_record import ReportRecord
from models.soap_record import SOAPRecord
from services.session_store import SessionStore
from services.soap_generator import SOAPGenerator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["soap"])

_store = SessionStore()


@router.post("/sessions/{session_id}/soap")
async def generate_soap_from_session(
    session_id: str,
    soap_gen: SOAPGenerator = Depends(get_soap_generator),
    db: Session = Depends(get_db),
):
    session = _store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden.")

    collected_data = session.collected_data
    report = session.generated_report

    result = await soap_gen.generate_from_data(collected_data, report)

    # Persist
    record = SOAPRecord(
        session_id=session_id,
        subjective=result["subjective"],
        objective=result["objective"],
        assessment=result["assessment"],
        plan=result["plan"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

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


@router.post("/reports/{report_id}/soap")
async def generate_soap_from_report(
    report_id: int,
    soap_gen: SOAPGenerator = Depends(get_soap_generator),
    db: Session = Depends(get_db),
):
    record = db.get(ReportRecord, report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden.")

    report = json.loads(record.content_json)
    result = await soap_gen.generate_from_data({}, report)

    soap_record = SOAPRecord(
        report_id=report_id,
        subjective=result["subjective"],
        objective=result["objective"],
        assessment=result["assessment"],
        plan=result["plan"],
    )
    db.add(soap_record)
    db.commit()
    db.refresh(soap_record)

    return {
        "id": soap_record.id,
        "session_id": soap_record.session_id,
        "report_id": soap_record.report_id,
        "subjective": soap_record.subjective,
        "objective": soap_record.objective,
        "assessment": soap_record.assessment,
        "plan": soap_record.plan,
        "created_at": soap_record.created_at.isoformat(),
    }


@router.get("/soap/{soap_id}")
async def get_soap_note(soap_id: int, db: Session = Depends(get_db)):
    record = db.get(SOAPRecord, soap_id)
    if not record:
        raise HTTPException(status_code=404, detail="SOAP-Notiz nicht gefunden.")

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
