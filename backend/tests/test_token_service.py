import time
from uuid import uuid4

import jwt
import pytest

from services.token_service import TokenService


@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-32-chars-minimum-length!")
    return TokenService()


def test_jwt_encode_contains_sub_and_exp(svc):
    uid = uuid4()
    tok = svc.encode_access(uid)
    decoded = jwt.decode(tok, "test-secret-32-chars-minimum-length!", algorithms=["HS256"])
    assert decoded["sub"] == str(uid)
    assert decoded["type"] == "access"
    assert "exp" in decoded and "iat" in decoded


def test_jwt_decode_rejects_bad_signature(svc):
    uid = uuid4()
    tok = svc.encode_access(uid)
    tampered = tok[:-4] + "AAAA"
    with pytest.raises(jwt.InvalidTokenError):
        svc.decode_access(tampered)


def test_jwt_decode_rejects_expired(svc):
    uid = uuid4()
    payload = {
        "sub": str(uid),
        "type": "access",
        "iat": int(time.time()) - 3600,
        "exp": int(time.time()) - 10,
    }
    expired = jwt.encode(payload, "test-secret-32-chars-minimum-length!", algorithm="HS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        svc.decode_access(expired)


def test_jwt_decode_rejects_alg_none(svc):
    payload = {"sub": str(uuid4()), "type": "access", "iat": int(time.time()), "exp": int(time.time()) + 60}
    none_token = jwt.encode(payload, key="", algorithm="none")
    with pytest.raises(jwt.InvalidTokenError):
        svc.decode_access(none_token)


def test_refresh_token_sha256_hash_stable(svc):
    plain, h1 = svc.encode_refresh()
    h2 = svc.hash_refresh(plain)
    assert h1 == h2
    assert len(h1) == 64
    assert plain != h1
