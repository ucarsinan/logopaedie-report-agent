"""Therapy plan generation and persistence endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from models.schemas import TherapyPlan, TherapyPlanSaveRequest, TherapyPlanSummary
from services.session_store import store
from database import get_db
from models.therapy_plan_record import TherapyPlanRecord
from dependencies import therapy_planner

router = APIRouter(tags=["therapy-plans"])


@router.post("/sessions/{session_id}/therapy-plan")
async def generate_therapy_plan(session_id: str) -> TherapyPlan:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    try:
        return await therapy_planner.generate_plan(session)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/therapy-plans", status_code=201)
async def save_therapy_plan(
    req: TherapyPlanSaveRequest, db: Session = Depends(get_db)
) -> TherapyPlanSummary:
    session = store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    if req.plan_data:
        plan_json = json.dumps(req.plan_data, ensure_ascii=False)
        patient_pseudonym = (
            req.plan_data.get("patient_pseudonym")
            or session.collected_data.get("patient_pseudonym", "Unbekannt")
        )
    else:
        try:
            plan = await therapy_planner.generate_plan(session)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        plan_json = json.dumps(plan.model_dump(), ensure_ascii=False)
        patient_pseudonym = plan.patient_pseudonym or session.collected_data.get("patient_pseudonym", "Unbekannt")

    record = TherapyPlanRecord(
        patient_pseudonym=patient_pseudonym,
        report_id=req.report_id,
        plan_data=plan_json,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return TherapyPlanSummary(
        id=record.id,
        created_at=record.created_at.isoformat(),
        patient_pseudonym=record.patient_pseudonym,
        report_id=record.report_id,
    )


@router.get("/therapy-plans")
async def list_therapy_plans(db: Session = Depends(get_db)) -> list[TherapyPlanSummary]:
    records = db.exec(
        select(TherapyPlanRecord).order_by(TherapyPlanRecord.created_at.desc())
    ).all()
    return [
        TherapyPlanSummary(
            id=r.id,
            created_at=r.created_at.isoformat(),
            patient_pseudonym=r.patient_pseudonym,
            report_id=r.report_id,
        )
        for r in records
    ]


@router.get("/therapy-plans/{plan_id}")
async def get_therapy_plan(plan_id: int, db: Session = Depends(get_db)) -> dict:
    record = db.get(TherapyPlanRecord, plan_id)
    if not record:
        raise HTTPException(status_code=404, detail="Therapieplan nicht gefunden.")
    plan = json.loads(record.plan_data)
    plan["_db_id"] = record.id
    plan["created_at"] = record.created_at.isoformat()
    return plan


@router.put("/therapy-plans/{plan_id}")
async def update_therapy_plan(
    plan_id: int, plan: dict, db: Session = Depends(get_db)
) -> TherapyPlanSummary:
    record = db.get(TherapyPlanRecord, plan_id)
    if not record:
        raise HTTPException(status_code=404, detail="Therapieplan nicht gefunden.")
    record.plan_data = json.dumps(plan, ensure_ascii=False)
    db.add(record)
    db.commit()
    db.refresh(record)
    return TherapyPlanSummary(
        id=record.id,
        created_at=record.created_at.isoformat(),
        patient_pseudonym=record.patient_pseudonym,
        report_id=record.report_id,
    )
