"""Phonological analysis and report comparison endpoints."""

import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile

from models.schemas import PhonologicalAnalysis, ReportComparison
from dependencies import phonological_analyzer, report_comparator

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/phonological")
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


@router.post("/phonological-text")
async def analyze_phonological_text(
    word_pairs: list[dict[str, str]],
    child_age: str | None = None,
) -> PhonologicalAnalysis:
    """Analyze phonological processes from text word pairs (no audio needed)."""
    try:
        return await phonological_analyzer.analyze(word_pairs, child_age)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
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
