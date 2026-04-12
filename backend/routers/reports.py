"""Persisted reports endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_db
from models.report_record import ReportRecord

router = APIRouter(tags=["reports"])


@router.get("/reports")
async def list_reports(db: Session = Depends(get_db)) -> list[dict]:
    records = db.exec(select(ReportRecord).order_by(ReportRecord.created_at.desc())).all()
    return [
        {
            "id": r.id,
            "pseudonym": r.pseudonym,
            "report_type": r.report_type,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("/reports/{report_id}")
async def get_persisted_report(report_id: int, db: Session = Depends(get_db)) -> dict:
    record = db.get(ReportRecord, report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden.")
    content = json.loads(record.content_json)
    content["_db_id"] = record.id
    content["created_at"] = record.created_at.isoformat()
    return content
