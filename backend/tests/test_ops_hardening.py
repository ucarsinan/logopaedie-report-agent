"""Welle 4 low-severity hardening:
- L-4: a public liveness probe (/livez) reachable without the service token.
- L-2: the primary model lists must not contain decommissioned Groq models.
"""

from __future__ import annotations


def test_livez_is_public_even_when_service_token_set(client, monkeypatch):
    """/health is token-guarded; /livez must stay public for load balancers."""
    monkeypatch.setenv("SERVICE_TOKEN", "secret-token")
    assert client.get("/health").status_code == 401
    res = client.get("/livez")
    assert res.status_code == 200
    assert res.json()["status"] == "alive"


def test_no_decommissioned_models_in_primary_lists():
    from services.groq_client import _CHAT_MODELS, _JSON_MODELS

    decommissioned = {"llama-3.1-70b-versatile"}
    assert not (set(_JSON_MODELS) & decommissioned)
    assert not (set(_CHAT_MODELS) & decommissioned)


def test_service_token_middleware_refuses_to_boot_in_production_without_token(monkeypatch):
    """A misconfigured prod must fail loudly, not silently expose /health."""
    import pytest
    from starlette.applications import Starlette

    from middleware.service_token import ServiceTokenMiddleware

    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("ENV", raising=False)

    with pytest.raises(RuntimeError, match="SERVICE_TOKEN"):
        ServiceTokenMiddleware(Starlette())


def test_service_token_middleware_boots_in_production_with_token(monkeypatch):
    from starlette.applications import Starlette

    from middleware.service_token import ServiceTokenMiddleware

    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("SERVICE_TOKEN", "any-non-empty")
    ServiceTokenMiddleware(Starlette())  # must not raise


def test_service_token_middleware_boots_outside_production_without_token(monkeypatch):
    from starlette.applications import Starlette

    from middleware.service_token import ServiceTokenMiddleware

    for var in ("VERCEL_ENV", "ENV"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("SERVICE_TOKEN", raising=False)
    ServiceTokenMiddleware(Starlette())  # must not raise — dev/test mode
