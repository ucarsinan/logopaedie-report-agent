"""Persisted reports endpoints."""

import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, func, select

from database import get_db
from dependencies import get_current_user
from models.auth import User
from models.patient import Patient
from models.report_record import ReportRecord

router = APIRouter(tags=["reports"])


@router.get("/reports")
async def list_reports(
    pseudonym: str | None = Query(None, description="Filter by pseudonym (case-insensitive)"),
    report_type: str | None = Query(None, description="Filter by report type"),
    patient_id: UUID | None = Query(None, description="Filter by patient ID"),
    from_date: str | None = Query(None, description="Filter from date (ISO format)"),
    to_date: str | None = Query(None, description="Filter to date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    include_total: bool = Query(
        True,
        description=(
            "If true (default), return an exact `total` count of matching rows. "
            "If false, `total` is set to None and the COUNT(*) query is skipped — "
            "use this on subsequent pages once the first page returned the total."
        ),
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    def _apply_filters(q):  # type: ignore[no-untyped-def]
        q = q.where(ReportRecord.user_id == current_user.id)
        if pseudonym:
            q = q.where(func.lower(ReportRecord.pseudonym).contains(pseudonym.lower()))
        if report_type:
            q = q.where(ReportRecord.report_type == report_type)
        if patient_id:
            q = q.where(ReportRecord.patient_id == patient_id)
        if from_date:
            try:
                dt = datetime.fromisoformat(from_date)
                q = q.where(col(ReportRecord.created_at) >= dt)
            except ValueError:
                pass
        if to_date:
            try:
                dt = datetime.fromisoformat(to_date)
                q = q.where(col(ReportRecord.created_at) <= dt)
            except ValueError:
                pass
        return q

    # P-5: COUNT(*) over the filtered set is the dominant cost on busy users.
    # Strategy (a) from I3: skip the COUNT(*) when the caller explicitly opts
    # out via `include_total=false` (returns total=None). Default behaviour
    # remains unchanged so existing callers (frontend, fetch-helper) keep
    # working — they can switch to include_total=false on page>1 to halve the
    # DB round-trips once they cache the total from the first page.
    total: int | None
    if include_total:
        count_query = select(func.count()).select_from(_apply_filters(select(ReportRecord)).subquery())
        total = db.exec(count_query).one()
    else:
        total = None

    join_query = _apply_filters(
        select(ReportRecord, Patient.pseudonym.label("patient_pseudonym")).outerjoin(  # type: ignore[attr-defined]
            Patient, col(ReportRecord.patient_id) == col(Patient.id)
        )
    )

    rows = db.exec(
        join_query.order_by(col(ReportRecord.created_at).desc()).offset((page - 1) * limit).limit(limit)
    ).all()

    return {
        "items": [
            {
                "id": r.ReportRecord.id,
                "pseudonym": r.ReportRecord.pseudonym,
                "report_type": r.ReportRecord.report_type,
                "created_at": r.ReportRecord.created_at.isoformat(),
                "patient_id": str(r.ReportRecord.patient_id) if r.ReportRecord.patient_id else None,
                "patient_pseudonym": r.patient_pseudonym,
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/reports/stats")
async def report_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    base = select(ReportRecord).where(ReportRecord.user_id == current_user.id)
    total = db.exec(select(func.count()).select_from(base.subquery())).one()

    type_counts_raw = db.exec(
        select(ReportRecord.report_type, func.count())
        .where(ReportRecord.user_id == current_user.id)
        .group_by(ReportRecord.report_type)
    ).all()
    by_type = {row[0]: row[1] for row in type_counts_raw}

    latest = db.exec(select(func.max(ReportRecord.created_at)).where(ReportRecord.user_id == current_user.id)).one()

    return {
        "total": total,
        "by_type": by_type,
        "latest_date": latest.isoformat() if latest else None,
    }


@router.get("/reports/{report_id}")
async def get_persisted_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    record = db.exec(
        select(ReportRecord).where(ReportRecord.id == report_id, ReportRecord.user_id == current_user.id)
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden.")
    content: dict = json.loads(record.content_json)
    content["_db_id"] = record.id
    content["created_at"] = record.created_at.isoformat()
    return content
