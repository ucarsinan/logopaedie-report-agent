"""Extract text from uploaded files (PDF, DOCX, TXT)."""

from __future__ import annotations

import asyncio
import io
import logging

from exceptions import FileTooLargeError, UnsupportedFileTypeError

logger = logging.getLogger(__name__)

_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


async def extract_text(content: bytes, filename: str, content_type: str) -> str:
    """Return plain text extracted from the uploaded file."""
    if len(content) > _MAX_FILE_BYTES:
        raise FileTooLargeError("Datei zu groß. Maximum: 10 MB.")

    lower = filename.lower()

    if lower.endswith(".pdf") or content_type == "application/pdf":
        return await asyncio.to_thread(_extract_pdf, content)
    if lower.endswith(".docx") or content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        return await asyncio.to_thread(_extract_docx, content)
    if lower.endswith(".txt") or content_type.startswith("text/"):
        return content.decode("utf-8", errors="replace")

    raise UnsupportedFileTypeError(f"Dateityp nicht unterstützt: {filename}")


def _extract_pdf(content: bytes) -> str:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise RuntimeError("PyPDF2 ist nicht installiert. Bitte installieren: pip install PyPDF2")

    reader = PdfReader(io.BytesIO(content))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _extract_docx(content: bytes) -> str:
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError("python-docx ist nicht installiert. Bitte installieren: pip install python-docx")

    doc = Document(io.BytesIO(content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
