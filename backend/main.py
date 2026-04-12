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

from database import create_db_and_tables
from routers import analysis, health, legacy, reports, sessions, suggestions, therapy_plans

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


# ── Include routers ───────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(reports.router)
app.include_router(analysis.router)
app.include_router(therapy_plans.router)
app.include_router(suggestions.router)
app.include_router(legacy.router)
