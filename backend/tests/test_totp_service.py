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
