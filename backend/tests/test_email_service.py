import inspect

import pytest

from services.email_service import EmailService, FakeEmailService


def test_send_is_coroutine_function():
    """_send must be awaitable so the blocking Resend call runs off the loop.

    The public send_* helpers are also coroutines now; they ``await self._send``
    directly so async callers (the auth route handlers and the AuthService
    methods that send mail) get a non-blocking path on every auth email send.
    """
    assert inspect.iscoroutinefunction(EmailService._send)
    assert inspect.iscoroutinefunction(EmailService.send_verify_email)
    assert inspect.iscoroutinefunction(EmailService.send_password_reset)


def test_fake_email_service_send_methods_are_async():
    """FakeEmailService mirrors the public interface so swapping it into
    AuthService doesn't accidentally hide a non-awaitable .send_* call."""
    assert inspect.iscoroutinefunction(FakeEmailService.send_verify_email)
    assert inspect.iscoroutinefunction(FakeEmailService.send_password_reset)


@pytest.mark.asyncio
async def test_email_service_console_fallback_when_no_api_key(capsys, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("APP_URL", "http://localhost:3000")
    monkeypatch.setenv("EMAIL_FROM", "noreply@test.local")
    svc = EmailService()
    await svc.send_verify_email("alice@example.com", "tok123")
    out = capsys.readouterr().out
    assert "EMAIL (console mode)" in out
    assert "alice@example.com" in out
    assert "tok123" in out


@pytest.mark.asyncio
async def test_email_service_reset_template_contains_reset_link(capsys, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("APP_URL", "http://localhost:3000")
    monkeypatch.setenv("EMAIL_FROM", "noreply@test.local")
    svc = EmailService()
    await svc.send_password_reset("bob@example.com", "resettok")
    out = capsys.readouterr().out
    assert "reset-password?token=resettok" in out


@pytest.mark.asyncio
async def test_fake_email_service_records_calls():
    fake = FakeEmailService()
    await fake.send_verify_email("x@example.com", "t1")
    await fake.send_password_reset("y@example.com", "t2")
    assert len(fake.sent) == 2
    assert fake.sent[0] == ("verify", "x@example.com", "t1")
    assert fake.sent[1] == ("reset", "y@example.com", "t2")
