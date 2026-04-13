"""TOTP 2FA wrapper with Fernet encryption for secret storage."""

from __future__ import annotations

import os

import pyotp
from cryptography.fernet import Fernet


class TOTPService:
    _ISSUER = "Logopaedie Report Agent"

    def __init__(self) -> None:
        key = os.getenv("SESSION_ENCRYPTION_KEY")
        if not key:
            raise RuntimeError("SESSION_ENCRYPTION_KEY env var is required")
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def generate_secret(self) -> str:
        return pyotp.random_base32()

    def provisioning_uri(self, secret: str, email: str) -> str:
        return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=self._ISSUER)

    def verify(self, secret: str, code: str, valid_window: int = 1) -> bool:
        if not code or not code.isdigit() or len(code) != 6:
            return False
        return pyotp.TOTP(secret).verify(code, valid_window=valid_window)

    def encrypt(self, secret: str) -> str:
        return self._fernet.encrypt(secret.encode("utf-8")).decode("utf-8")

    def decrypt(self, cipher: str) -> str:
        return self._fernet.decrypt(cipher.encode("utf-8")).decode("utf-8")
