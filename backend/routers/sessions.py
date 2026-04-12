"""Session management, chat, audio, upload, consent, report generation endpoints."""

import json
import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session

from models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    SessionInfo,
    UploadedMaterial,
)
from services.session_store import store
from services.file_processor import extract_text
from database import get_db
from models.report_record import ReportRecord
from dependencies import anamnesis_engine, groq_service, report_generator

router = APIRouter(tags=["sessions"])

_MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
_MAX_MATERIALS = 5
_MAX_MATERIAL_BYTES = 10 * 1024 * 1024  # 10 MB


class CreateSessionRequest(BaseModel):
    mode: str = "anamnesis"  # "anamnesis" | "therapy_plan"


class ConsentRequest(BaseModel):
    consent: bool


# ── Session management ──────────────────────────────────────────────────────
@router.post("/sessions")
async def create_session(req: CreateSessionRequest | None = None) -> SessionInfo:
    session = store.create()
    if req and req.mode == "therapy_plan":
        session.therapy_plan_mode = True
    try:
        greeting = await anamnesis_engine.get_initial_greeting(session)
    except Exception:
        greeting = (
            "Willkommen! Ich bin bereit, Ihnen bei der Erstellung des Therapieplans zu helfen. "
            "Bitte nennen Sie das Pseudonym des Patienten."
            if (req and req.mode == "therapy_plan")
            else
            "Willkommen! Ich bin bereit, Ihnen bei der Dokumentation zu helfen. "
            "Bitte beschreiben Sie den Patienten und den Therapiebereich."
        )
    store.save(session)
    return SessionInfo(
        session_id=session.session_id,
        status=session.status,
        report_type=session.report_type,
        collected_data={"greeting": greeting},
        therapy_plan_mode=session.therapy_plan_mode,
    )


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> SessionInfo:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")
    return SessionInfo(
        session_id=session.session_id,
        status=session.status,
        report_type=session.report_type,
        collected_data=session.collected_data,
        chat_history=session.chat_history,
    )


@router.post("/sessions/{session_id}/new-conversation")
async def new_conversation(session_id: str) -> SessionInfo:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    patient_name = session.collected_data.get("patient_pseudonym") or session.collected_data.get("patient_name")

    session.chat_history = []
    session.collected_data = {"patient_pseudonym": patient_name} if patient_name else {}
    session.status = "anamnesis"
    session.report_type = None
    session.generated_report = None
    session.materials = []
    session.materials_consent = False

    try:
        greeting = await anamnesis_engine.get_contextual_greeting(session)
    except Exception:
        greeting = (
            "Willkommen zurück! Bitte beschreiben Sie den Berichtstyp für diese Sitzung."
        )
        session.chat_history.append(ChatMessage(role="assistant", content=greeting))

    store.save(session)
    return SessionInfo(
        session_id=session.session_id,
        status=session.status,
        report_type=session.report_type,
        collected_data={"greeting": greeting},
    )


# ── Chat (text) ────────────────────────────────────────────────────────────
@router.post("/sessions/{session_id}/chat")
async def chat(session_id: str, req: ChatRequest) -> ChatResponse:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    if not req.message:
        raise HTTPException(status_code=400, detail="Nachricht darf nicht leer sein.")

    try:
        response_text = await anamnesis_engine.process_message(session, req.message, req.mode)
    except RuntimeError as e:
        if "429" in str(e) or "rate_limit" in str(e):
            raise HTTPException(
                status_code=429,
                detail="Das KI-Tageslimit ist leider erreicht. Bitte versuchen Sie es morgen erneut.",
            )
        raise HTTPException(status_code=500, detail="KI-Anfrage fehlgeschlagen. Bitte versuchen Sie es erneut.")

    store.save(session)
    return ChatResponse(
        message=response_text,
        phase=session.collected_data.get("current_phase", "greeting"),
        is_anamnesis_complete=session.status != "anamnesis",
        collected_fields=session.collected_data.get("collected_fields", []),
        missing_fields=anamnesis_engine._compute_missing_fields(session),
    )


# ── Chat via audio ─────────────────────────────────────────────────────────
@router.post("/sessions/{session_id}/audio")
async def chat_audio(session_id: str, audio_file: UploadFile = File(...)) -> ChatResponse:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    suffix = os.path.splitext(audio_file.filename or "audio")[1] or ".wav"
    tmp_path: str | None = None

    try:
        content = await audio_file.read()
        if len(content) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Datei zu groß. Maximum: 25 MB.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        transcript = await groq_service.transcribe_audio(tmp_path)
        response_text = await anamnesis_engine.process_message(session, transcript)

        store.save(session)
        return ChatResponse(
            message=response_text,
            phase=session.collected_data.get("current_phase", "greeting"),
            is_anamnesis_complete=session.status != "anamnesis",
            collected_fields=session.collected_data.get("collected_fields", []),
            missing_fields=anamnesis_engine._compute_missing_fields(session),
            transcript=transcript,
        )
    except RuntimeError as e:
        if "429" in str(e) or "rate_limit" in str(e):
            raise HTTPException(
                status_code=429,
                detail="Das KI-Tageslimit ist leider erreicht. Bitte versuchen Sie es morgen erneut.",
            )
        raise HTTPException(status_code=500, detail="KI-Anfrage fehlgeschlagen. Bitte versuchen Sie es erneut.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ── File upload ─────────────────────────────────────────────────────────────
@router.post("/sessions/{session_id}/upload")
async def upload_material(
    session_id: str,
    file: UploadFile = File(...),
    material_type: str = "sonstiges",
) -> UploadedMaterial:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    if len(session.materials) >= _MAX_MATERIALS:
        raise HTTPException(status_code=400, detail=f"Maximum {_MAX_MATERIALS} Dateien pro Session.")

    try:
        content = await file.read()
        extracted = await extract_text(content, file.filename or "file", file.content_type or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    material = UploadedMaterial(
        filename=file.filename or "unbekannt",
        content_type=file.content_type or "application/octet-stream",
        extracted_text=extracted,
        material_type=material_type,
    )
    session.materials.append(material)
    store.save(session)
    return material


# ── Materials consent ────────────────────────────────────────────────────────
@router.post("/sessions/{session_id}/materials-consent")
async def set_materials_consent(session_id: str, req: ConsentRequest) -> SessionInfo:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")
    session.materials_consent = req.consent
    store.save(session)
    return SessionInfo(
        session_id=session.session_id,
        status=session.status,
        report_type=session.report_type,
        collected_data=session.collected_data,
        materials_consent=session.materials_consent,
    )


# ── Report generation ───────────────────────────────────────────────────────
@router.post("/sessions/{session_id}/generate")
async def generate_report(session_id: str, db: Session = Depends(get_db)) -> dict:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    session.status = "generating"
    store.save(session)

    try:
        report = await report_generator.generate(session)
        session.generated_report = report.model_dump()
        session.status = "complete"
        store.save(session)

        record = ReportRecord(
            pseudonym=session.generated_report.get("patient", {}).get("pseudonym", "Unbekannt"),
            report_type=session.generated_report.get("report_type", "unbekannt"),
            content_json=json.dumps(session.generated_report, ensure_ascii=False),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        session.generated_report["_db_id"] = record.id

        return session.generated_report
    except RuntimeError as e:
        session.status = "materials"  # Allow retry
        store.save(session)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/report")
async def get_report(session_id: str) -> dict:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    if not session.generated_report:
        raise HTTPException(status_code=404, detail="Noch kein Bericht generiert.")

    return session.generated_report
