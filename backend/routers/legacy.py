"""Legacy endpoints for backward compatibility."""

import logging
import os
import tempfile

from fastapi import APIRouter, Depends, File, Request, UploadFile

from dependencies import get_current_user, groq_service
from exceptions import FileTooLargeError
from middleware.rate_limiter import AUDIO_LIMIT, limiter
from models.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["legacy"])

_MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB


@router.post("/process-audio")
@limiter.limit(AUDIO_LIMIT)
async def process_audio(
    request: Request,
    audio_file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    suffix = os.path.splitext(audio_file.filename or "audio")[1] or ".wav"
    tmp_path: str | None = None

    try:
        content = await audio_file.read()
        if len(content) > _MAX_UPLOAD_BYTES:
            raise FileTooLargeError("Datei zu groß. Maximum: 25 MB.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        transcript = await groq_service.transcribe_audio(tmp_path)
        report = await groq_service.generate_structured_report(transcript)
        return report
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/transcribe")
@limiter.limit(AUDIO_LIMIT)
async def transcribe_only(
    request: Request,
    audio_file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    """Whisper STT only -- no session, no chat engine, just transcript."""
    suffix = os.path.splitext(audio_file.filename or "audio")[1] or ".webm"
    tmp_path: str | None = None
    try:
        content = await audio_file.read()
        if len(content) > _MAX_UPLOAD_BYTES:
            raise FileTooLargeError("Datei zu groß. Maximum: 25 MB.")
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        transcript = await groq_service.transcribe_audio(tmp_path)
        return {"transcript": transcript}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
