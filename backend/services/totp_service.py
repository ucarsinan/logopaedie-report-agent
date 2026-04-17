"""TOTP 2FA wrapper with Fernet encryption for secret storage."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pyotp
from cryptography.fernet import Fernet


class TOTPService:
    _ISSUER = "Logopaedie Report Agent"
    # Stable base32 secret used for constant-time dummy verifications — never stored.
    _DUMMY_SECRET = "JBSWY3DPEHPK3PXP"

    def __init__(self) -> None:
        key = os.getenv("SESSION_ENCRYPTION_KEY")
        if not key:
            raise RuntimeError("SESSION_ENCRYPTION_KEY env var is required")
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    @property
    def dummy_secret(self) -> str:
        return self._DUMMY_SECRET

    def generate_secret(self) -> str:
        return pyotp.random_base32()  # type: ignore[no-any-return]

    def provisioning_uri(self, secret: str, email: str) -> str:
        return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=self._ISSUER)  # type: ignore[no-any-return]

    def verify(self, secret: str, code: str, valid_window: int = 1) -> bool:
        if not code or not code.isdigit() or len(code) != 6:
            return False
        return pyotp.TOTP(secret).verify(code, valid_window=valid_window)  # type: ignore[no-any-return]

    def verify_and_get_step(self, secret: str, code: str, valid_window: int = 1) -> int | None:
        """Verify a TOTP code and return the matched step counter, or None if invalid.

        The step counter enables replay detection: callers must reject the code if
        matched_step <= user.last_totp_step (same code reused within the validity window).
        """
        if not code or not code.isdigit() or len(code) != 6:
            return None
        totp = pyotp.TOTP(secret)
        current_step = totp.timecode(datetime.now(UTC))
        for step in range(current_step - valid_window, current_step + valid_window + 1):
            if totp.generate_otp(step) == code:
                return step
        return None

    def encrypt(self, secret: str) -> str:
        return self._fernet.encrypt(secret.encode("utf-8")).decode("utf-8")

    def decrypt(self, cipher: str) -> str:
        return self._fernet.decrypt(cipher.encode("utf-8")).decode("utf-8")
