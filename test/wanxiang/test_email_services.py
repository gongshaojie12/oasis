# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P2: Email service abstractions (NoOp / SMTP) + factory."""
from __future__ import annotations

import asyncio


def _run(coro):
    return asyncio.run(coro)


def test_noop_email_returns_ok(capsys):
    from wanxiang.api.email import NoOpEmailService

    svc = NoOpEmailService()
    result = _run(svc.send("alice@example.com", "Test", "<p>hello 123456</p>",
                            body_text="hello 123456"))
    assert result.ok is True
    assert result.message_id == "noop"
    out = capsys.readouterr().out
    assert "alice@example.com" in out
    assert "Test" in out


def test_make_email_service_default_is_noop(monkeypatch):
    monkeypatch.delenv("WANXIANG_EMAIL_PROVIDER", raising=False)
    from wanxiang.api.email import make_email_service, NoOpEmailService

    svc = make_email_service()
    assert isinstance(svc, NoOpEmailService)


def test_make_email_service_smtp(monkeypatch):
    monkeypatch.setenv("WANXIANG_EMAIL_PROVIDER", "smtp")
    from wanxiang.api.email import make_email_service, SmtpEmailService

    svc = make_email_service()
    assert isinstance(svc, SmtpEmailService)


def test_smtp_unreachable_returns_error(monkeypatch):
    """Smtp pointed at a closed port returns ok=False rather than raising."""
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    # Port 1 unlikely to be listening as SMTP locally.
    monkeypatch.setenv("SMTP_PORT", "1")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    from wanxiang.api.email import SmtpEmailService

    svc = SmtpEmailService()
    result = _run(svc.send("a@b.com", "x", "<p>x</p>"))
    assert result.ok is False
    assert result.error
