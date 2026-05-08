"""Tests for legacy /process-audio and /transcribe endpoints."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch

from models.schemas import MedicalReport

_FAKE_REPORT = MedicalReport(
    patient_pseudonym="M.S.",
    symptoms=["Sprachstörung"],
    therapy_progress="Stabil",
    prognosis="Gut",
)


class TestProcessAudio:
    def test_process_audio_success(self, client, mock_groq):
        mock_groq["transcribe"].return_value = "Der Patient zeigt Fortschritte."

        with patch(
            "services.groq_client.GroqService.generate_structured_report",
            new_callable=AsyncMock,
            return_value=_FAKE_REPORT,
        ):
            audio_bytes = b"RIFF" + b"\x00" * 100
            res = client.post(
                "/process-audio",
                files={"audio_file": ("test.wav", io.BytesIO(audio_bytes), "audio/wav")},
            )
        assert res.status_code == 200
        data = res.json()
        assert "patient_pseudonym" in data

    def test_process_audio_file_too_large(self, client):
        large_content = b"x" * (26 * 1024 * 1024)  # 26 MB > 25 MB limit
        res = client.post(
            "/process-audio",
            files={"audio_file": ("big.wav", io.BytesIO(large_content), "audio/wav")},
        )
        assert res.status_code == 413

    def test_process_audio_no_extension(self, client, mock_groq):
        mock_groq["transcribe"].return_value = "Transcript text"
        with patch(
            "services.groq_client.GroqService.generate_structured_report",
            new_callable=AsyncMock,
            return_value=MedicalReport(
                patient_pseudonym="P.Q.",
                symptoms=[],
                therapy_progress="",
                prognosis="",
            ),
        ):
            res = client.post(
                "/process-audio",
                files={"audio_file": ("noextension", io.BytesIO(b"audiodata"), "audio/wav")},
            )
        assert res.status_code == 200


class TestTranscribeOnly:
    def test_transcribe_success(self, client, mock_groq):
        mock_groq["transcribe"].return_value = "Dies ist ein Transkript."
        audio_bytes = b"RIFF" + b"\x00" * 50
        res = client.post(
            "/transcribe",
            files={"audio_file": ("recording.webm", io.BytesIO(audio_bytes), "audio/webm")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["transcript"] == "Dies ist ein Transkript."

    def test_transcribe_file_too_large(self, client):
        large_content = b"x" * (26 * 1024 * 1024)  # 26 MB
        res = client.post(
            "/transcribe",
            files={"audio_file": ("big.webm", io.BytesIO(large_content), "audio/webm")},
        )
        assert res.status_code == 413

    def test_transcribe_no_extension(self, client, mock_groq):
        mock_groq["transcribe"].return_value = "Test transcript"
        res = client.post(
            "/transcribe",
            files={"audio_file": ("noext", io.BytesIO(b"data"), "audio/webm")},
        )
        assert res.status_code == 200
        assert res.json()["transcript"] == "Test transcript"
