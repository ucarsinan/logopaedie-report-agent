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


def test_password_hash_empty_string_and_verify(svc):
    """Boundary: argon2 accepts the empty string as a password. ``hash("")``
    must produce a valid argon2id hash and ``verify("")`` against it must
    return True, while ``verify("nonempty", h)`` returns False. This is the
    contract callers (auth_service) rely on; the responsibility of rejecting
    empty passwords belongs to validation layers above this service."""
    h = svc.hash("")
    assert h.startswith("$argon2id$")
    assert svc.verify("", h) is True
    assert svc.verify("not-empty", h) is False


def test_password_hash_very_long_password(svc):
    """Boundary: argon2id accepts arbitrarily long passwords (no implicit
    truncation like bcrypt's 72-byte cap). A 1000-char password must hash
    cleanly and round-trip via ``verify``. Catches a regression if the
    backing scheme is ever swapped for one with silent truncation."""
    long_pw = "a" * 1000
    h = svc.hash(long_pw)
    assert h.startswith("$argon2id$")
    assert svc.verify(long_pw, h) is True
    # A single-char difference at the tail must still fail (no truncation).
    assert svc.verify("a" * 999 + "b", h) is False


def test_password_verify_malformed_hash_returns_false(svc):
    """Contract: ``verify`` never raises on a malformed hash string — it
    returns False. Inputs covered: empty string, plain text, argon2-shaped
    but corrupted, and a None-equivalent. This prevents callers from having
    to wrap every verify() in a try/except just to safely handle a corrupt
    DB row or migration artifact."""
    h = svc.hash("real-pass-123")
    # Empty hash → guarded fast-path returns False.
    assert svc.verify("real-pass-123", "") is False
    # Plain non-hash text → guarded fast-path returns False.
    assert svc.verify("real-pass-123", "not-a-hash-at-all") is False
    # Argon2-shaped prefix but truncated/garbage payload → caught try/except.
    assert svc.verify("real-pass-123", "$argon2id$v=19$garbage") is False
    # Sanity: real verify still works alongside the negatives above.
    assert svc.verify("real-pass-123", h) is True
