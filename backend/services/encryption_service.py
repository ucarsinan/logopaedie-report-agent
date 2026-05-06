"""Encryption service for patient PII field encryption using Fernet."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet


class EncryptionService:
    def __init__(self) -> None:
        key = os.environ.get("PATIENT_ENCRYPTION_KEY")
        if not key:
            raise RuntimeError("PATIENT_ENCRYPTION_KEY environment variable is not set.")
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, value: str | None) -> bytes | None:
        """Encrypt a string value. Returns None if input is None."""
        if value is None:
            return None
        return self._fernet.encrypt(value.encode())

    def decrypt(self, value: bytes | None) -> str | None:
        """Decrypt bytes value. Returns None if input is None."""
        if value is None:
            return None
        return self._fernet.decrypt(value).decode()
