"""Tests for PDF export endpoint."""

from __future__ import annotations

import json
from unittest.mock import patch

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
