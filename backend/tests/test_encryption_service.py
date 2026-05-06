from __future__ import annotations

import pytest
from cryptography.fernet import Fernet


@pytest.fixture
def key(monkeypatch):
    k = Fernet.generate_key().decode()
    monkeypatch.setenv("PATIENT_ENCRYPTION_KEY", k)
    return k


def test_encrypt_returns_bytes(key):
    from services.encryption_service import EncryptionService

    svc = EncryptionService()
    result = svc.encrypt("Max Mustermann")
    assert isinstance(result, bytes)
    assert result != b"Max Mustermann"


def test_decrypt_round_trips(key):
    from services.encryption_service import EncryptionService

    svc = EncryptionService()
    original = "Maria Muster"
    assert svc.decrypt(svc.encrypt(original)) == original


def test_encrypt_none_returns_none(key):
    from services.encryption_service import EncryptionService

    svc = EncryptionService()
    assert svc.encrypt(None) is None
    assert svc.decrypt(None) is None


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("PATIENT_ENCRYPTION_KEY", raising=False)
    import importlib

    import services.encryption_service as mod

    importlib.reload(mod)
    with pytest.raises(RuntimeError, match="PATIENT_ENCRYPTION_KEY"):
        mod.EncryptionService()
    importlib.reload(mod)
