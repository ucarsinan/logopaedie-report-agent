"""Phonological analysis and report comparison endpoints."""

import logging
import os
import tempfile

from fastapi import APIRouter, File, Request, UploadFile

from dependencies import phonological_analyzer, report_comparator
from middleware.rate_limiter import ANALYSIS_LIMIT, limiter
from models.schemas import PhonologicalAnalysis, ReportComparison

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/phonological")
@limiter.limit(ANALYSIS_LIMIT)
async def analyze_phonological(
    request: Request,
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

        return await phonological_analyzer.analyze_audio(target_path, production_path, child_age)
    finally:
        for p in (target_path, production_path):
            if p and os.path.exists(p):
                os.unlink(p)


@router.post("/phonological-text")
@limiter.limit(ANALYSIS_LIMIT)
async def analyze_phonological_text(
    request: Request,
    word_pairs: list[dict[str, str]],
    child_age: str | None = None,
) -> PhonologicalAnalysis:
    """Analyze phonological processes from text word pairs (no audio needed)."""
    return await phonological_analyzer.analyze(word_pairs, child_age)


@router.post("/compare")
@limiter.limit(ANALYSIS_LIMIT)
async def compare_reports(
    request: Request,
    initial_report: UploadFile = File(...),
    current_report: UploadFile = File(...),
) -> ReportComparison:
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
