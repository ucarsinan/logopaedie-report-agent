"""Email delivery via Resend SDK, with console fallback for local dev.

The Resend HTTP call is a blocking I/O round-trip (typ. 200-800ms). To keep it
from monopolising the event loop while waiting on the network, ``_send`` awaits
``asyncio.to_thread`` around the SDK call. The public ``send_verify_email`` /
``send_password_reset`` helpers are themselves ``async`` and ``await self._send``
directly — async callers (the auth route handlers and the auth service methods
that send mail) just ``await`` them, which keeps the event loop free for other
requests during the SDK round-trip.
"""

from __future__ import annotations

import asyncio
import os
from typing import Literal


class EmailService:
    def __init__(self) -> None:
        self._api_key = os.getenv("RESEND_API_KEY", "")
        self._from = os.getenv("EMAIL_FROM", "noreply@localhost")
        self._app_url = os.getenv("APP_URL", "http://localhost:3000")

    async def _send(self, to: str, subject: str, body: str) -> None:
        if not self._api_key:
            print(f"EMAIL (console mode) -> {to}\nSubject: {subject}\n{body}\n")
            return
        import resend  # type: ignore

        resend.api_key = self._api_key
        # Offload the blocking SDK call to a worker thread so we never hold the
        # event loop on a 200-800ms HTTP round-trip.
        await asyncio.to_thread(
            resend.Emails.send,
            {"from": self._from, "to": [to], "subject": subject, "text": body},
        )

    async def send_verify_email(self, to: str, token: str) -> None:
        link = f"{self._app_url}/verify-email?token={token}"
        body = (
            f"Welcome. Please verify your email by clicking:\n{link}\n"
            "If you did not create an account, ignore this message."
        )
        await self._send(to, "Verify your email", body)

    async def send_password_reset(self, to: str, token: str) -> None:
        link = f"{self._app_url}/reset-password?token={token}"
        body = (
            f"A password reset was requested. Click to continue:\n{link}\n"
            "If you did not request this, you can safely ignore this message."
        )
        await self._send(to, "Password reset request", body)


class FakeEmailService:
    def __init__(self) -> None:
        self.sent: list[tuple[Literal["verify", "reset"], str, str]] = []

    async def send_verify_email(self, to: str, token: str) -> None:
        self.sent.append(("verify", to, token))

    async def send_password_reset(self, to: str, token: str) -> None:
        self.sent.append(("reset", to, token))
