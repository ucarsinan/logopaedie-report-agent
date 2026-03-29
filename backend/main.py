import os
import sys
import tempfile

# On Vercel (experimentalServices), backend/ is the function root (/var/task/).
# Add it to sys.path so "from models.X" and "from services.X" resolve correctly
# both locally (when running via uvicorn backend.main:app) and on Vercel.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from models.schemas import (
    ChatRequest,
    ChatResponse,
    PhonologicalAnalysis,
    ReportComparison,
    SessionInfo,
    SuggestRequest,
    TextSuggestion,
    TherapyPlan,
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

load_dotenv()

app = FastAPI(title="Logopädie Report Agent API")

_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ── Session management ──────────────────────────────────────────────────────
@app.post("/sessions")
async def create_session() -> SessionInfo:
    session = store.create()
    # Generate initial greeting
    greeting = await anamnesis_engine.get_initial_greeting(session)
    return SessionInfo(
        session_id=session.session_id,
        status=session.status,
        report_type=session.report_type,
        collected_data={"greeting": greeting},
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
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(
        message=response_text,
        phase=session.collected_data.get("current_phase", "greeting"),
        is_anamnesis_complete=session.status != "anamnesis",
        collected_fields=session.collected_data.get("collected_fields", []),
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

        return ChatResponse(
            message=response_text,
            phase=session.collected_data.get("current_phase", "greeting"),
            is_anamnesis_complete=session.status != "anamnesis",
            collected_fields=session.collected_data.get("collected_fields", []),
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
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
    return material


# ── Report generation ───────────────────────────────────────────────────────
@app.post("/sessions/{session_id}/generate")
async def generate_report(session_id: str) -> dict:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    session.status = "generating"

    try:
        report = await report_generator.generate(session)
        session.generated_report = report.model_dump()
        session.status = "complete"
        return session.generated_report
    except RuntimeError as e:
        session.status = "materials"  # Allow retry
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/report")
async def get_report(session_id: str) -> dict:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden oder abgelaufen.")

    if not session.generated_report:
        raise HTTPException(status_code=404, detail="Noch kein Bericht generiert.")

    return session.generated_report


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
