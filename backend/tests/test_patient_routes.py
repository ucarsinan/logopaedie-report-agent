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
    res = client.post("/api/patients", json=_payload())
    assert res.status_code == 201
    data = res.json()
    assert data["system_id"].startswith("PAT-")
    assert data["pseudonym"] == "Sonnenschein"
    assert data["realname"] == "Max Mustermann"


def test_create_patient_auto_pseudonym(client):
    res = client.post("/api/patients", json=_payload(pseudonym=None))
    assert res.status_code == 201
    assert res.json()["pseudonym"] == res.json()["system_id"]


def test_list_patients_empty(client):
    res = client.get("/api/patients")
    assert res.status_code == 200
    assert res.json()["total"] == 0


def test_list_patients_returns_created(client):
    client.post("/api/patients", json=_payload())
    res = client.get("/api/patients")
    assert res.json()["total"] == 1


def test_list_patients_search(client):
    client.post("/api/patients", json=_payload(pseudonym="Sonnenschein"))
    client.post("/api/patients", json=_payload(pseudonym="Mond"))
    res = client.get("/api/patients?q=sonn")
    assert res.json()["total"] == 1


def test_get_patient_detail(client):
    pid = client.post("/api/patients", json=_payload()).json()["id"]
    res = client.get(f"/api/patients/{pid}")
    assert res.status_code == 200
    assert res.json()["realname"] == "Max Mustermann"


def test_get_patient_not_found(client):
    import uuid

    res = client.get(f"/api/patients/{uuid.uuid4()}")
    assert res.status_code == 404


def test_patch_patient(client):
    pid = client.post("/api/patients", json=_payload()).json()["id"]
    res = client.patch(f"/api/patients/{pid}", json={"pseudonym": "Stern"})
    assert res.status_code == 200
    assert res.json()["pseudonym"] == "Stern"


def test_delete_patient_soft(client):
    pid = client.post("/api/patients", json=_payload()).json()["id"]
    assert client.delete(f"/api/patients/{pid}").status_code == 200
    assert client.get("/api/patients").json()["total"] == 0
    assert client.get(f"/api/patients/{pid}").status_code == 404


def test_get_history_empty(client):
    pid = client.post("/api/patients", json=_payload()).json()["id"]
    res = client.get(f"/api/patients/{pid}/history")
    assert res.status_code == 200
    assert res.json()["items"] == []


def test_get_progress_no_reports(client):
    pid = client.post("/api/patients", json=_payload()).json()["id"]
    res = client.get(f"/api/patients/{pid}/progress")
    assert res.status_code == 200
    assert res.json()["comparison"] is None


def test_record_consent(client):
    pid = client.post("/api/patients", json=_payload()).json()["id"]
    res = client.post(
        f"/api/patients/{pid}/consent",
        json={"consent_type": "data_processing", "granted": True},
    )
    assert res.status_code == 201
    assert res.json()["granted"] is True


def test_record_consent_invalid_type(client):
    pid = client.post("/api/patients", json=_payload()).json()["id"]
    res = client.post(
        f"/api/patients/{pid}/consent",
        json={"consent_type": "bad_type", "granted": True},
    )
    assert res.status_code == 422
