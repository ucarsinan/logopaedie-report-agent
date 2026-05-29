"""Tests for PDF export endpoint."""

from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import patch

import httpx
import pytest
from sqlmodel import Session

from models.report_record import ReportRecord


@pytest.fixture()
def report_in_db(test_db, fake_user):
    """Insert a ReportRecord and return its ID."""
    content = {
        "report_type": "befundbericht",
        "patient": {"pseudonym": "A.B.", "age_group": "Kind", "gender": "weiblich"},
        "diagnose": {"icd_10_codes": ["F80.0"], "indikationsschluessel": "SP1", "diagnose_text": "Störung"},
        "befund": "Befundtext.",
    }
    record = ReportRecord(
        pseudonym="A.B.",
        report_type="befundbericht",
        content_json=json.dumps(content),
        user_id=fake_user.id,
    )
    with Session(test_db) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        return record.id


def test_download_pdf_returns_pdf_bytes(client, report_in_db):
    fake_pdf = b"%PDF-1.4 fake content"
    with patch("routers.exports.generate_pdf", return_value=fake_pdf):
        resp = client.get(f"/reports/{report_in_db}/pdf")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == fake_pdf


def test_download_pdf_filename_contains_pseudonym(client, report_in_db):
    with patch("routers.exports.generate_pdf", return_value=b"%PDF-1.4"):
        resp = client.get(f"/reports/{report_in_db}/pdf")

    disposition = resp.headers.get("content-disposition", "")
    # filename format: bericht_{pseudonym}_{report_type}.pdf
    assert "A.B." in disposition
    assert "befundbericht" in disposition


def test_download_pdf_not_found(client):
    resp = client.get("/reports/99999/pdf")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_pdf_does_not_block_event_loop(mock_groq, mock_redis, fake_user, test_db, report_in_db):
    """Regression: ``generate_pdf`` must run off the event loop.

    The reportlab render is sync and takes 1-3s per call; invoking it directly
    from the ``async def`` handler would block the loop for the full render
    duration. We monkeypatch ``generate_pdf`` to ``time.sleep(0.4)`` and fire
    two concurrent requests through an ASGI client. With the
    ``asyncio.to_thread`` offload both renders overlap and total elapsed is
    close to ~0.4s; without it they serialize on the event loop and elapsed
    climbs to ~0.8s+. We assert < 0.7s to leave generous CI headroom while
    still catching a regression that drops the offload.
    """
    from database import get_db
    from dependencies import get_current_user
    from main import app

    def override_get_db():
        with Session(test_db) as session:
            yield session

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = override_get_db
    sleep_s = 0.4

    def _slow_pdf(*args: object, **kwargs: object) -> bytes:
        time.sleep(sleep_s)
        return b"%PDF-1.4 slow"

    try:
        with patch("routers.exports.generate_pdf", side_effect=_slow_pdf):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
                start = time.perf_counter()
                r1, r2 = await asyncio.gather(
                    ac.get(f"/reports/{report_in_db}/pdf"),
                    ac.get(f"/reports/{report_in_db}/pdf"),
                )
                elapsed = time.perf_counter() - start
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert elapsed < sleep_s + 0.3, (
        f"two concurrent PDF downloads took {elapsed:.2f}s for {sleep_s}s renders — "
        "renders serialized on the event loop; asyncio.to_thread offload regressed"
    )


def test_download_pdf_wrong_user(client, test_db):
    from uuid import uuid4

    other_user_id = uuid4()
    content = {"report_type": "befundbericht", "patient": {}}
    record = ReportRecord(
        pseudonym="Other",
        report_type="befundbericht",
        content_json=json.dumps(content),
        user_id=other_user_id,
    )
    with Session(test_db) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
        record_id = record.id

    resp = client.get(f"/reports/{record_id}/pdf")
    assert resp.status_code == 404
