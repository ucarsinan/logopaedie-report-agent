from __future__ import annotations


def _payload(**kw):
    return {
        "realname": "Max Mustermann",
        "birthdate": "2019-03-15",
        "pseudonym": "Sonnenschein",
        "age_group": "kind",
        "disorder_text": "Dyslalie",
        "icd10_codes": ["F80.0"],
        **kw,
    }


def test_create_patient(client):
    res = client.post("/patients", json=_payload())
    assert res.status_code == 201
    data = res.json()
    assert data["system_id"].startswith("PAT-")
    assert data["pseudonym"] == "Sonnenschein"
    assert data["realname"] == "Max Mustermann"


def test_create_patient_auto_pseudonym(client):
    res = client.post("/patients", json=_payload(pseudonym=None))
    assert res.status_code == 201
    assert res.json()["pseudonym"] == res.json()["system_id"]


def test_list_patients_empty(client):
    res = client.get("/patients")
    assert res.status_code == 200
    assert res.json()["total"] == 0


def test_list_patients_returns_created(client):
    client.post("/patients", json=_payload())
    res = client.get("/patients")
    assert res.json()["total"] == 1


def test_list_patients_search(client):
    client.post("/patients", json=_payload(pseudonym="Sonnenschein"))
    client.post("/patients", json=_payload(pseudonym="Mond"))
    res = client.get("/patients?q=sonn")
    assert res.json()["total"] == 1


def test_get_patient_detail(client):
    pid = client.post("/patients", json=_payload()).json()["id"]
    res = client.get(f"/patients/{pid}")
    assert res.status_code == 200
    assert res.json()["realname"] == "Max Mustermann"


def test_get_patient_not_found(client):
    import uuid

    res = client.get(f"/patients/{uuid.uuid4()}")
    assert res.status_code == 404


def test_patch_patient(client):
    pid = client.post("/patients", json=_payload()).json()["id"]
    res = client.patch(f"/patients/{pid}", json={"pseudonym": "Stern"})
    assert res.status_code == 200
    assert res.json()["pseudonym"] == "Stern"


def test_delete_patient_soft(client):
    pid = client.post("/patients", json=_payload()).json()["id"]
    assert client.delete(f"/patients/{pid}").status_code == 200
    assert client.get("/patients").json()["total"] == 0
    assert client.get(f"/patients/{pid}").status_code == 404


def test_get_history_empty(client):
    pid = client.post("/patients", json=_payload()).json()["id"]
    res = client.get(f"/patients/{pid}/history")
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1
    assert body["limit"] == 50


def _seed_reports(client, patient_id: str, count: int) -> None:
    """Insert ``count`` reports for ``patient_id`` directly via the test DB.

    No public endpoint mints persisted reports, so we write straight to the
    SQLModel table the route reads from, reusing the ``get_db`` dependency
    override that ``client`` installed (so we hit the same in-memory engine).
    """
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    from sqlmodel import Session

    from database import get_db
    from main import app
    from models.report_record import ReportRecord

    db_dep = app.dependency_overrides[get_db]
    gen = db_dep()
    session: Session = next(gen)
    try:
        base_time = datetime.now(UTC)
        for i in range(count):
            session.add(
                ReportRecord(
                    pseudonym=f"PAT-{i}",
                    report_type="befundbericht",
                    content_json="{}",
                    user_id=client.fake_user.id,
                    patient_id=UUID(patient_id),
                    created_at=base_time + timedelta(seconds=i),
                )
            )
        session.commit()
    finally:
        gen.close()


def test_get_history_pagination_default_caps_items(client):
    """Default limit (50) returns at most 50 items even when more exist."""
    pid = client.post("/patients", json=_payload()).json()["id"]
    _seed_reports(client, pid, 60)
    res = client.get(f"/patients/{pid}/history")
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 50
    assert body["total"] == 60
    assert body["limit"] == 50
    assert body["page"] == 1


def test_get_history_pagination_second_page(client):
    """Page 2 with limit=50 returns the remaining items."""
    pid = client.post("/patients", json=_payload()).json()["id"]
    _seed_reports(client, pid, 60)
    res = client.get(f"/patients/{pid}/history?page=2&limit=50")
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 10
    assert body["total"] == 60
    assert body["page"] == 2


def test_get_history_total_reflects_full_count_not_page_size(client):
    """``total`` is the unfiltered row count, not the size of the page."""
    pid = client.post("/patients", json=_payload()).json()["id"]
    _seed_reports(client, pid, 25)
    res = client.get(f"/patients/{pid}/history?limit=10")
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 10
    assert body["total"] == 25


def test_get_progress_no_reports(client):
    pid = client.post("/patients", json=_payload()).json()["id"]
    res = client.get(f"/patients/{pid}/progress")
    assert res.status_code == 200
    assert res.json()["comparison"] is None


def test_record_consent(client):
    pid = client.post("/patients", json=_payload()).json()["id"]
    res = client.post(
        f"/patients/{pid}/consent",
        json={"consent_type": "data_processing", "granted": True},
    )
    assert res.status_code == 201
    assert res.json()["granted"] is True


def test_record_consent_invalid_type(client):
    pid = client.post("/patients", json=_payload()).json()["id"]
    res = client.post(
        f"/patients/{pid}/consent",
        json={"consent_type": "bad_type", "granted": True},
    )
    assert res.status_code == 422
