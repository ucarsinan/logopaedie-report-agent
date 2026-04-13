import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.service_token import ServiceTokenMiddleware


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("SERVICE_TOKEN", "svc-secret")
    application = FastAPI()
    application.add_middleware(ServiceTokenMiddleware)

    @application.get("/health")
    def health():
        return {"ok": True}

    @application.get("/cron/cleanup")
    def cleanup():
        return {"ran": True}

    @application.get("/other")
    def other():
        return {"other": True}

    return application


def test_service_token_middleware_health_requires_token(app):
    client = TestClient(app)
    assert client.get("/health").status_code == 401
    ok = client.get("/health", headers={"Authorization": "Bearer svc-secret"})
    assert ok.status_code == 200


def test_service_token_middleware_cron_requires_token(app):
    client = TestClient(app)
    assert client.get("/cron/cleanup").status_code == 401
    ok = client.get("/cron/cleanup", headers={"Authorization": "Bearer svc-secret"})
    assert ok.status_code == 200


def test_service_token_middleware_other_paths_passthrough(app):
    client = TestClient(app)
    res = client.get("/other")
    assert res.status_code == 200


def test_service_token_middleware_inactive_when_env_unset(monkeypatch):
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)
    app = FastAPI()
    app.add_middleware(ServiceTokenMiddleware)

    @app.get("/health")
    def health():
        return {"ok": True}

    assert TestClient(app).get("/health").status_code == 200
