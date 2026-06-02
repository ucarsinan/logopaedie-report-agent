from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from middleware.auth import JWTAuthMiddleware
from services.token_service import TokenService


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
    application = FastAPI()
    application.add_middleware(JWTAuthMiddleware)

    @application.get("/whoami")
    def whoami(request: Request):
        return {"user": request.state.user}

    return application


def test_middleware_no_header_sets_user_none(app):
    client = TestClient(app)
    res = client.get("/whoami")
    assert res.status_code == 200
    assert res.json() == {"user": None}


def test_middleware_valid_token_populates_user(app, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
    svc = TokenService()
    uid = uuid4()
    tok = svc.encode_access(uid)
    client = TestClient(app)
    res = client.get("/whoami", headers={"Authorization": f"Bearer {tok}"})
    assert res.status_code == 200
    assert res.json()["user"]["id"] == str(uid)


def test_middleware_invalid_token_sets_user_none_never_401(app):
    client = TestClient(app)
    res = client.get("/whoami", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 200
    assert res.json() == {"user": None}


def test_middleware_revoked_token_sets_user_none(app, monkeypatch):
    """I3 S-7: when the access-token blocklist marks a token's `iat` as
    pre-cutoff, the middleware must fall through to the anonymous path
    (request.state.user is None), same as for an invalid JWT."""
    import time

    import fakeredis

    from services.access_token_blocklist import AccessTokenBlocklist

    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
    svc = TokenService()
    uid = uuid4()
    tok = svc.encode_access(uid)

    # Wire a fakeredis blocklist via the singleton lookup the middleware uses
    redis_client = fakeredis.FakeStrictRedis(decode_responses=True)
    blocklist = AccessTokenBlocklist(redis_client, ttl_seconds=900)
    import dependencies

    monkeypatch.setattr(dependencies, "get_access_token_blocklist", lambda: blocklist)

    # Sanity: before revocation, the token works
    client = TestClient(app)
    res = client.get("/whoami", headers={"Authorization": f"Bearer {tok}"})
    assert res.json()["user"]["id"] == str(uid)

    # Revoke ALL tokens for this user (cutoff = now). Sleep 1s so the
    # cutoff is strictly greater than the JWT's iat.
    time.sleep(1)
    blocklist.revoke_all_for_user(str(uid))
    res = client.get("/whoami", headers={"Authorization": f"Bearer {tok}"})
    assert res.status_code == 200
    assert res.json() == {"user": None}
