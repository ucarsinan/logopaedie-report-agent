"""Tests for file text extraction."""

import pytest

from backend.services.file_processor import extract_text


@pytest.mark.asyncio
async def test_extract_txt():
    content = "Dies ist ein Testbericht.".encode("utf-8")
    result = await extract_text(content, "test.txt", "text/plain")
    assert result == "Dies ist ein Testbericht."


@pytest.mark.asyncio
async def test_extract_txt_by_content_type():
    content = b"Inhalt"
    result = await extract_text(content, "unknown_name", "text/plain")
    assert result == "Inhalt"


@pytest.mark.asyncio
async def test_unsupported_type():
    with pytest.raises(ValueError, match="nicht unterstützt"):
        await extract_text(b"data", "file.xyz", "application/octet-stream")


@pytest.mark.asyncio
async def test_file_too_large():
    large = b"x" * (11 * 1024 * 1024)  # 11 MB
    with pytest.raises(ValueError, match="zu groß"):
        await extract_text(large, "big.txt", "text/plain")
