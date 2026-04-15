"""Ownership tests: reports are scoped to the authenticated user (IDOR prevention)."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from models.auth import GUID, User  # noqa: F401 — registers User in SQLModel metadata
from models.report_record import ReportRecord


@pytest.fixture
def eng():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def two_users(eng):
    """Return (user_a, user_b) inserted into the DB."""
    user_a = User(id=uuid4(), email="alice@test.example", password_hash="x", role="user")
    user_b = User(id=uuid4(), email="bob@test.example", password_hash="x", role="user")
    with Session(eng) as db:
        db.add(user_a)
        db.add(user_b)
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)
    return user_a, user_b


@pytest.fixture
def ownership_client(eng, mock_groq, mock_redis):
    """TestClient with DB override; current_user is swappable via client.set_user()."""

    from fastapi.testclient import TestClient

    from database import get_db
    from dependencies import get_current_user
    from main import app

    _current_user: list = [None]

    def _db_override():
        with Session(eng) as db:
            yield db

    def _user_override():
        if _current_user[0] is None:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication_required")
        return _current_user[0]

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_current_user] = _user_override

    with TestClient(app, raise_server_exceptions=False) as c:

        def set_user(user):
            _current_user[0] = user

        c.set_user = set_user
        yield c

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


def _report(user_id, pseudonym="P"):
    return ReportRecord(
        pseudonym=pseudonym,
        report_type="befundbericht",
        content_json=json.dumps({"report_type": "befundbericht"}),
        user_id=user_id,
    )


def test_list_reports_scoped_to_current_user(ownership_client, eng, two_users):
    user_a, user_b = two_users
    with Session(eng) as db:
        db.add(_report(user_a.id, "Alice-Patient"))
        db.add(_report(user_b.id, "Bob-Patient"))
        db.commit()

    ownership_client.set_user(user_a)
    res = ownership_client.get("/reports")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["pseudonym"] == "Alice-Patient"


def test_get_report_returns_own_report(ownership_client, eng, two_users):
    user_a, _ = two_users
    with Session(eng) as db:
        r = _report(user_a.id)
        db.add(r)
        db.commit()
        db.refresh(r)
        rid = r.id

    ownership_client.set_user(user_a)
    res = ownership_client.get(f"/reports/{rid}")
    assert res.status_code == 200


def test_get_report_404_for_other_user(ownership_client, eng, two_users):
    user_a, user_b = two_users
    with Session(eng) as db:
        r = _report(user_a.id)
        db.add(r)
        db.commit()
        db.refresh(r)
        rid = r.id

    ownership_client.set_user(user_b)
    res = ownership_client.get(f"/reports/{rid}")
    assert res.status_code == 404


def test_pdf_export_404_for_other_user(ownership_client, eng, two_users):
    user_a, user_b = two_users
    with Session(eng) as db:
        r = _report(user_a.id)
        db.add(r)
        db.commit()
        db.refresh(r)
        rid = r.id

    ownership_client.set_user(user_b)
    res = ownership_client.get(f"/reports/{rid}/pdf")
    assert res.status_code == 404


def test_report_stats_counts_only_own(ownership_client, eng, two_users):
    user_a, user_b = two_users
    with Session(eng) as db:
        db.add(_report(user_a.id))
        db.add(_report(user_b.id))
        db.add(_report(user_b.id))
        db.commit()

    ownership_client.set_user(user_a)
    res = ownership_client.get("/reports/stats")
    assert res.status_code == 200
    assert res.json()["total"] == 1


def test_unauthenticated_reports_returns_401(ownership_client):
    res = ownership_client.get("/reports")
    assert res.status_code == 401
