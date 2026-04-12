import logging
import os
import sys
from contextlib import asynccontextmanager

# On Vercel (experimentalServices), backend/ is the function root (/var/task/).
# Add it to sys.path so "from models.X" and "from services.X" resolve correctly
# both locally (when running via uvicorn backend.main:app) and on Vercel.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from database import create_db_and_tables
from exceptions import (
    AIServiceError,
    AppError,
    FileTooLargeError,
    ModelExhaustedError,
    RateLimitError,
    ReportGenerationError,
    ReportNotFoundError,
    SessionExpiredError,
    SessionNotFoundError,
    TranscriptionError,
    UnsupportedFileTypeError,
    ValidationError,
)
from logging_config import setup_logging
from middleware.auth import APIKeyAuthMiddleware
from middleware.rate_limiter import limiter
from routers import analysis, exports, health, legacy, reports, sessions, soap, suggestions, therapy_plans

load_dotenv()
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Logopädie Report Agent API", lifespan=lifespan)

# Attach rate limiter state
app.state.limiter = limiter

_allowed_origins = list({
    *os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    "http://localhost:3000",
})

# Auth middleware (must be added before CORS to process requests)
app.add_middleware(APIKeyAuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


# ── Custom exception handlers ────────────────────────────────────────────────
@app.exception_handler(SessionNotFoundError)
async def session_not_found_handler(request: Request, exc: SessionNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(SessionExpiredError)
async def session_expired_handler(request: Request, exc: SessionExpiredError) -> JSONResponse:
    return JSONResponse(status_code=410, content={"detail": str(exc)})


@app.exception_handler(RateLimitError)
async def rate_limit_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Das KI-Tageslimit ist leider erreicht. Bitte versuchen Sie es morgen erneut."},
    )


@app.exception_handler(ModelExhaustedError)
async def model_exhausted_handler(request: Request, exc: ModelExhaustedError) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Alle Modelle erschöpft. Bitte morgen erneut versuchen."},
    )


@app.exception_handler(TranscriptionError)
async def transcription_error_handler(request: Request, exc: TranscriptionError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(AIServiceError)
async def ai_service_error_handler(request: Request, exc: AIServiceError) -> JSONResponse:
    logger.error("AI service error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "KI-Anfrage fehlgeschlagen. Bitte versuchen Sie es erneut."})


@app.exception_handler(FileTooLargeError)
async def file_too_large_handler(request: Request, exc: FileTooLargeError) -> JSONResponse:
    return JSONResponse(status_code=413, content={"detail": str(exc)})


@app.exception_handler(UnsupportedFileTypeError)
async def unsupported_file_type_handler(request: Request, exc: UnsupportedFileTypeError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ReportNotFoundError)
async def report_not_found_handler(request: Request, exc: ReportNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ReportGenerationError)
async def report_generation_error_handler(request: Request, exc: ReportGenerationError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Zu viele Anfragen. Bitte warten Sie einen Moment."},
    )


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


# ── Include routers ───────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(reports.router)
app.include_router(analysis.router)
app.include_router(therapy_plans.router)
app.include_router(suggestions.router)
app.include_router(exports.router)
app.include_router(soap.router)
app.include_router(legacy.router)
