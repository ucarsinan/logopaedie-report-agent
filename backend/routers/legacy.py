"""Legacy endpoints for backward compatibility."""

import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile

from dependencies import groq_service

router = APIRouter(tags=["legacy"])

_MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


@router.post("/process-audio")
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


@router.post("/transcribe")
async def transcribe_only(audio_file: UploadFile = File(...)):
    """Whisper STT only — no session, no chat engine, just transcript."""
    suffix = os.path.splitext(audio_file.filename or "audio")[1] or ".webm"
    tmp_path: str | None = None
    try:
        content = await audio_file.read()
        if len(content) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Datei zu groß. Maximum: 25 MB.")
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        transcript = await groq_service.transcribe_audio(tmp_path)
        return {"transcript": transcript}
    except RuntimeError as e:
        if "429" in str(e) or "rate_limit" in str(e):
            raise HTTPException(status_code=429, detail="Das KI-Tageslimit ist leider erreicht.")
        raise HTTPException(status_code=500, detail="Transkription fehlgeschlagen.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
