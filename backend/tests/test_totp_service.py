import time
from urllib.parse import unquote

import pyotp
import pytest
from cryptography.fernet import Fernet

from services.totp_service import TOTPService


@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setenv("SESSION_ENCRYPTION_KEY", Fernet.generate_key().decode())
    return TOTPService()


def test_totp_verify_valid_code(svc):
    secret = svc.generate_secret()
    code = pyotp.TOTP(secret).now()
    assert svc.verify(secret, code) is True


def test_totp_verify_wrong_code(svc):
    secret = svc.generate_secret()
    assert svc.verify(secret, "000000") is False


def test_totp_verify_drift_window_pm30s(svc):
    secret = svc.generate_secret()
    totp = pyotp.TOTP(secret)
    past_code = totp.at(int(time.time()) - 30)
    assert svc.verify(secret, past_code, valid_window=1) is True


def test_totp_secret_fernet_encrypted_at_rest(svc):
    secret = svc.generate_secret()
    cipher = svc.encrypt(secret)
    assert cipher != secret
    assert svc.decrypt(cipher) == secret


def test_totp_provisioning_uri_contains_email(svc):
    secret = svc.generate_secret()
    uri = svc.provisioning_uri(secret, "user@example.com")
    assert uri.startswith("otpauth://totp/")
    assert "user@example.com" in unquote(uri)


# ── I2 deferred: TOTPService error-path coverage ─────────────────────────────


def test_decrypt_tampered_ciphertext_raises_invalid_token(svc):
    """Mutating one byte of a valid Fernet ciphertext must surface as an
    ``InvalidToken`` exception — the wrapper does not silently swallow
    decryption failures.
    """
    from cryptography.fernet import InvalidToken

    cipher = svc.encrypt(svc.generate_secret())
    # Flip a character in the middle of the token body (avoid the version
    # prefix so the failure path is "MAC check failed", not "unknown version").
    mid = len(cipher) // 2
    swapped = "A" if cipher[mid] != "A" else "B"
    tampered = cipher[:mid] + swapped + cipher[mid + 1 :]
    with pytest.raises(InvalidToken):
        svc.decrypt(tampered)


def test_verify_and_get_step_returns_none_for_invalid_code_shape(svc):
    """``verify_and_get_step`` must short-circuit and return None for
    non-6-digit / non-numeric input — same contract as ``verify``.
    """
    secret = svc.generate_secret()
    assert svc.verify_and_get_step(secret, "12345") is None  # too short
    assert svc.verify_and_get_step(secret, "1234567") is None  # too long
    assert svc.verify_and_get_step(secret, "abcdef") is None  # non-digit
    assert svc.verify_and_get_step(secret, "") is None  # empty


def test_verify_and_get_step_outside_drift_window_returns_none(svc):
    """A code that matches a step far outside ``valid_window`` must return
    None — the replay-prevention contract relies on this so a stale code
    can never re-authenticate the user.
    """
    secret = svc.generate_secret()
    totp = pyotp.TOTP(secret)
    # Generate a code for a step 10 windows in the past
    current_step = totp.timecode(__import__("datetime").datetime.now(__import__("datetime").UTC))
    stale_code = totp.generate_otp(current_step - 10)
    assert svc.verify_and_get_step(secret, stale_code, valid_window=1) is None


def test_verify_and_get_step_returns_matched_step_within_window(svc):
    """Positive contract check: a code generated for the *previous* step
    (within the drift window) must return that step's counter, not None.
    Pinning this keeps the replay-prevention invariant
    ``matched_step <= last_totp_step`` meaningful.
    """
    secret = svc.generate_secret()
    totp = pyotp.TOTP(secret)
    current_step = totp.timecode(__import__("datetime").datetime.now(__import__("datetime").UTC))
    past_step = current_step - 1
    code = totp.generate_otp(past_step)
    matched = svc.verify_and_get_step(secret, code, valid_window=1)
    assert matched == past_step


def test_provisioning_uri_handles_email_special_chars(svc):
    """Emails containing ``+`` (gmail-style aliases) or other RFC-5322
    specials must produce a parseable otpauth URI — pyotp percent-encodes
    them in the path, not the query.
    """
    from urllib.parse import parse_qs, unquote, urlparse

    secret = svc.generate_secret()
    uri = svc.provisioning_uri(secret, "user+alias@example.com")
    parsed = urlparse(uri)
    assert parsed.scheme == "otpauth"
    assert parsed.netloc == "totp"
    # The "+" must be percent-encoded (%2B) inside the path, not left raw
    assert "%2B" in parsed.path
    # And the email is recoverable after URL-decoding
    assert "user+alias@example.com" in unquote(parsed.path)
    qs = parse_qs(parsed.query)
    assert qs["secret"] == [secret]
    assert qs["issuer"] == ["Logopaedie Report Agent"]
