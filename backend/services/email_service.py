"""Email delivery via Resend SDK, with console fallback for local dev."""

from __future__ import annotations

import os
from typing import Literal


class EmailService:
    def __init__(self) -> None:
        self._api_key = os.getenv("RESEND_API_KEY", "")
        self._from = os.getenv("EMAIL_FROM", "noreply@localhost")
        self._app_url = os.getenv("APP_URL", "http://localhost:3000")

    def _send(self, to: str, subject: str, body: str) -> None:
        if not self._api_key:
            print(f"EMAIL (console mode) -> {to}\nSubject: {subject}\n{body}\n")
            return
        import resend  # type: ignore

        resend.api_key = self._api_key
        resend.Emails.send({"from": self._from, "to": [to], "subject": subject, "text": body})

    def send_verify_email(self, to: str, token: str) -> None:
        link = f"{self._app_url}/verify-email?token={token}"
        body = (
            f"Welcome. Please verify your email by clicking:\n{link}\n"
            "If you did not create an account, ignore this message."
        )
        self._send(to, "Verify your email", body)

    def send_password_reset(self, to: str, token: str) -> None:
        link = f"{self._app_url}/reset-password?token={token}"
        body = (
            f"A password reset was requested. Click to continue:\n{link}\n"
            "If you did not request this, you can safely ignore this message."
        )
        self._send(to, "Password reset request", body)


class FakeEmailService:
    def __init__(self) -> None:
        self.sent: list[tuple[Literal["verify", "reset"], str, str]] = []

    def send_verify_email(self, to: str, token: str) -> None:
        self.sent.append(("verify", to, token))

    def send_password_reset(self, to: str, token: str) -> None:
        self.sent.append(("reset", to, token))
