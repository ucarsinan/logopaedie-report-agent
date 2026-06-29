"""Tests for public liveness endpoint."""


def test_livez(client):
    res = client.get("/livez")
    assert res.status_code == 200
    assert res.json() == {"status": "alive"}
