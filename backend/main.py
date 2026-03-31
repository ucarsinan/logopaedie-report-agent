import json
import logging
import os
import sys
import tempfile
from contextlib import asynccontextmanager

# On Vercel (experimentalServices), backend/ is the function root (/var/task/).
# Add it to sys.path so "from models.X" and "from services.X" resolve correctly
# both locally (when running via uvicorn backend.main:app) and on Vercel.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    PhonologicalAnalysis,
    ReportComparison,
    SessionInfo,
    SuggestRequest,
    TextSuggestion,
    TherapyPlan,
    TherapyPlanSaveRequest,
    TherapyPlanSummary,
    UploadedMaterial,
)
from services.anamnesis_engine import AnamnesisEngine
from services.file_processor import extract_text
from services.groq_client import GroqService
from services.phonological_analyzer import PhonologicalAnalyzer
from services.report_comparator import ReportComparator
from services.report_generator import ReportGenerator
from services.session_store import store
from services.text_suggester import TextSuggester
from services.therapy_planner import TherapyPlanner
from database import create_db_and_tables, get_db
from models.report_record import ReportRecord
from models.therapy_plan_record import TherapyPlanRecord

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Logopädie Report Agent API", lifespan=lifespan)

_allowed_origins = list({
    *os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    "http://localhost:3000",
})

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    origin = request.headers.get("origin", "")
    headers: dict[str, str] = {}
    if origin in _allowed_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": "Interner Serverfehler. Bitte versuchen Sie es erneut."},
        headers=headers,
    )


groq_service = GroqService()
anamnesis_engine = AnamnesisEngine(groq_service)
report_generator = ReportGenerator(groq_service)
phonological_analyzer = PhonologicalAnalyzer(groq_service)
therapy_planner = TherapyPlanner(groq_service)
report_comparator = ReportComparator(groq_service)
text_suggester = TextSuggester(groq_service)


# ── Health ──────────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ── Legacy endpoint (backward compatibility) ────────────────────────────────
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


@app.post("/process-audio")
async def process_audio(audio_file: UploadFile = File(...)):
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
        report = await groq_service.generate_structured_report(transcript)
        return report
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


class CreateSessionRequest(BaseModel):
    mode: str = "anamnesis"  # "anamnesis" | "therapy_plan"


# ── Session management ──────────────────────────────────────────────────────
@app.post("/sessions")
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


@app.get("/sessions/{session_id}")
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


@app.post("/sessions/{session_id}/new-conversation")
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
@app.post("/sessions/{session_id}/chat")
async def chat(session_id: str, req: ChatRequest) -> ChatResponse:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    if not req.message:
        raise HTTPException(status_code=400, detail="Nachricht darf nicht leer sein.")

    try:
        response_text = await anamnesis_engine.process_message(session, req.message)
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
@app.post("/sessions/{session_id}/audio")
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
_MAX_MATERIALS = 5
_MAX_MATERIAL_BYTES = 10 * 1024 * 1024  # 10 MB


@app.post("/sessions/{session_id}/upload")
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
class ConsentRequest(BaseModel):
    consent: bool


@app.post("/sessions/{session_id}/materials-consent")
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
@app.post("/sessions/{session_id}/generate")
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


@app.get("/sessions/{session_id}/report")
async def get_report(session_id: str) -> dict:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    if not session.generated_report:
        raise HTTPException(status_code=404, detail="Noch kein Bericht generiert.")

    return session.generated_report


# ── Persisted reports ────────────────────────────────────────────────
@app.get("/reports")
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


@app.get("/reports/{report_id}")
async def get_persisted_report(report_id: int, db: Session = Depends(get_db)) -> dict:
    record = db.get(ReportRecord, report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Bericht nicht gefunden.")
    content = json.loads(record.content_json)
    content["_db_id"] = record.id
    content["created_at"] = record.created_at.isoformat()
    return content


# ── Feature 1: Phonological Process Analysis ───────────────────────────────
@app.post("/analysis/phonological")
async def analyze_phonological(
    target_audio: UploadFile = File(...),
    production_audio: UploadFile = File(...),
    child_age: str | None = None,
) -> PhonologicalAnalysis:
    target_path: str | None = None
    production_path: str | None = None

    try:
        target_content = await target_audio.read()
        production_content = await production_audio.read()

        target_suffix = os.path.splitext(target_audio.filename or "a")[1] or ".wav"
        prod_suffix = os.path.splitext(production_audio.filename or "a")[1] or ".wav"

        with tempfile.NamedTemporaryFile(delete=False, suffix=target_suffix) as tmp:
            tmp.write(target_content)
            target_path = tmp.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=prod_suffix) as tmp:
            tmp.write(production_content)
            production_path = tmp.name

        return await phonological_analyzer.analyze_audio(
            target_path, production_path, child_age
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for p in (target_path, production_path):
            if p and os.path.exists(p):
                os.unlink(p)


@app.post("/analysis/phonological-text")
async def analyze_phonological_text(
    word_pairs: list[dict[str, str]],
    child_age: str | None = None,
) -> PhonologicalAnalysis:
    """Analyze phonological processes from text word pairs (no audio needed)."""
    try:
        return await phonological_analyzer.analyze(word_pairs, child_age)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Feature 2: Therapy Plan Generator ──────────────────────────────────────
@app.post("/sessions/{session_id}/therapy-plan")
async def generate_therapy_plan(session_id: str) -> TherapyPlan:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    try:
        return await therapy_planner.generate_plan(session)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Therapy Plan persistence ────────────────────────────────────────────────
@app.post("/therapy-plans", status_code=201)
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


@app.get("/therapy-plans")
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


@app.get("/therapy-plans/{plan_id}")
async def get_therapy_plan(plan_id: int, db: Session = Depends(get_db)) -> dict:
    record = db.get(TherapyPlanRecord, plan_id)
    if not record:
        raise HTTPException(status_code=404, detail="Therapieplan nicht gefunden.")
    plan = json.loads(record.plan_data)
    plan["_db_id"] = record.id
    plan["created_at"] = record.created_at.isoformat()
    return plan


@app.put("/therapy-plans/{plan_id}")
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


# ── Feature 3: Comparative Report Analysis ─────────────────────────────────
@app.post("/analysis/compare")
async def compare_reports(
    initial_report: UploadFile = File(...),
    current_report: UploadFile = File(...),
) -> ReportComparison:
    try:
        initial_content = await initial_report.read()
        current_content = await current_report.read()

        return await report_comparator.compare_files(
            initial_content,
            initial_report.filename or "initial",
            initial_report.content_type or "",
            current_content,
            current_report.filename or "current",
            current_report.content_type or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Feature 4: Intelligent Text Suggestions ────────────────────────────────
@app.post("/suggest")
async def suggest_text(req: SuggestRequest) -> TextSuggestion:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text darf nicht leer sein.")

    try:
        return await text_suggester.suggest(
            req.text, req.report_type, req.disorder, req.section
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
