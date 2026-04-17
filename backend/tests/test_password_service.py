import pytest

from services.password_service import PasswordService


@pytest.fixture
def svc():
    return PasswordService()


def test_password_hash_is_argon2id(svc):
    h = svc.hash("correct horse battery staple")
    assert h.startswith("$argon2id$")


def test_password_verify_roundtrip(svc):
    h = svc.hash("s3cret-passphrase-12")
    assert svc.verify("s3cret-passphrase-12", h) is True
    assert svc.verify("wrong", h) is False


def test_password_verify_rejects_tampered_hash(svc):
    h = svc.hash("another-long-pass12")
    tampered = h[:-4] + "AAAA"
    assert svc.verify("another-long-pass12", tampered) is False


def test_password_verify_rejects_non_argon2(svc):
    bcrypt_like = "$2b$12$abcdefghijklmnopqrstuv.abcdefghijklmnopqrstuvwxyz0123"
    assert svc.verify("whatever", bcrypt_like) is False
