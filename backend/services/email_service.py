"""Email delivery via Resend SDK, with console fallback for local dev.

The Resend HTTP call is a blocking I/O round-trip (typ. 200-800ms). To keep it
from monopolising the calling thread while waiting on the network, ``_send``
is an async coroutine that awaits ``asyncio.to_thread`` around the SDK call.
The public ``send_verify_email`` / ``send_password_reset`` wrappers stay
synchronous so existing sync callers (AuthService, FastAPI sync routes) keep
their signatures unchanged; they bridge into the coroutine via ``asyncio.run``.
That isolation makes it trivial to migrate to ``await self._send(...)`` from
an async caller later without another ripple through the auth chain.
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

    def _run_send(self, to: str, subject: str, body: str) -> None:
        """Synchronous bridge for sync callers (auth_service, sync routes)."""
        asyncio.run(self._send(to, subject, body))

    def send_verify_email(self, to: str, token: str) -> None:
        link = f"{self._app_url}/verify-email?token={token}"
        body = (
            f"Welcome. Please verify your email by clicking:\n{link}\n"
            "If you did not create an account, ignore this message."
        )
        self._run_send(to, "Verify your email", body)

    def send_password_reset(self, to: str, token: str) -> None:
        link = f"{self._app_url}/reset-password?token={token}"
        body = (
            f"A password reset was requested. Click to continue:\n{link}\n"
            "If you did not request this, you can safely ignore this message."
        )
        self._run_send(to, "Password reset request", body)


class FakeEmailService:
    def __init__(self) -> None:
        self.sent: list[tuple[Literal["verify", "reset"], str, str]] = []

    def send_verify_email(self, to: str, token: str) -> None:
        self.sent.append(("verify", to, token))

    def send_password_reset(self, to: str, token: str) -> None:
        self.sent.append(("reset", to, token))
