import os
import tempfile

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.services.groq_client import GroqService

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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


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
