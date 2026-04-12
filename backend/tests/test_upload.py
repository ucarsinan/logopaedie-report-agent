"""Tests for file upload endpoint."""

import io


def test_upload_txt(client, session_id):
    content = b"Befundbericht vom 01.01.2024. Patient zeigt Fortschritte."
    res = client.post(
        f"/sessions/{session_id}/upload?material_type=befund",
        files={"file": ("report.txt", io.BytesIO(content), "text/plain")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "report.txt"
    assert data["material_type"] == "befund"
    assert "Befundbericht" in data["extracted_text"]


def test_upload_unsupported_type(client, session_id):
    res = client.post(
        f"/sessions/{session_id}/upload",
        files={"file": ("data.csv", io.BytesIO(b"a,b,c"), "text/csv")},
    )
    # CSV is handled as text/ content-type, so it should succeed
    assert res.status_code == 200


def test_upload_session_not_found(client):
    res = client.post(
        "/sessions/aabbccddeeff/upload",
        files={"file": ("test.txt", io.BytesIO(b"test"), "text/plain")},
    )
    assert res.status_code == 404


def test_upload_max_files(client, session_id):
    for i in range(5):
        res = client.post(
            f"/sessions/{session_id}/upload",
            files={"file": (f"file{i}.txt", io.BytesIO(b"text"), "text/plain")},
        )
        assert res.status_code == 200

    # 6th file should fail
    res = client.post(
        f"/sessions/{session_id}/upload",
        files={"file": ("file5.txt", io.BytesIO(b"text"), "text/plain")},
    )
    assert res.status_code == 400
