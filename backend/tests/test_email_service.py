from services.email_service import EmailService, FakeEmailService


def test_email_service_console_fallback_when_no_api_key(capsys, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("APP_URL", "http://localhost:3000")
    monkeypatch.setenv("EMAIL_FROM", "noreply@test.local")
    svc = EmailService()
    svc.send_verify_email("alice@example.com", "tok123")
    out = capsys.readouterr().out
    assert "EMAIL (console mode)" in out
    assert "alice@example.com" in out
    assert "tok123" in out


def test_email_service_reset_template_contains_reset_link(capsys, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("APP_URL", "http://localhost:3000")
    monkeypatch.setenv("EMAIL_FROM", "noreply@test.local")
    svc = EmailService()
    svc.send_password_reset("bob@example.com", "resettok")
    out = capsys.readouterr().out
    assert "reset-password?token=resettok" in out


def test_fake_email_service_records_calls():
    fake = FakeEmailService()
    fake.send_verify_email("x@example.com", "t1")
    fake.send_password_reset("y@example.com", "t2")
    assert len(fake.sent) == 2
    assert fake.sent[0] == ("verify", "x@example.com", "t1")
    assert fake.sent[1] == ("reset", "y@example.com", "t2")
