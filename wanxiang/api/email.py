# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Email service abstraction. MVP: NoOp logs to stdout.

For production:
- ``WANXIANG_EMAIL_PROVIDER=smtp`` — generic SMTP (Aliyun / Tencent /
  SendGrid all support).
- env: ``SMTP_HOST``, ``SMTP_PORT``, ``SMTP_USER``, ``SMTP_PASSWORD``,
  ``SMTP_FROM``, ``SMTP_USE_TLS``.
"""
from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.utils import formatdate
from typing import Protocol

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailResult:
    ok: bool
    message_id: str | None = None
    error: str | None = None


class EmailService(Protocol):
    async def send(self, to: str, subject: str, body_html: str,
                    *, body_text: str | None = None) -> EmailResult: ...


class NoOpEmailService:
    async def send(self, to, subject, body_html, *, body_text=None):
        log.warning("[EMAIL-NOOP] to=%s subject=%s", to, subject)
        # Print first 200 chars of body for dev visibility
        preview = (body_text or body_html)[:200]
        print(f"[EMAIL-NOOP] to={to} subject={subject}\n  body={preview}",
               flush=True)
        return EmailResult(ok=True, message_id="noop")


class SmtpEmailService:
    def __init__(self):
        self.host = os.environ.get("SMTP_HOST", "localhost")
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASSWORD", "")
        self.from_addr = os.environ.get("SMTP_FROM",
                                          "noreply@wanxiang.local")
        self.use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() \
            == "true"

    async def send(self, to, subject, body_html, *, body_text=None):
        try:
            msg = MIMEText(body_html, "html", "utf-8")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = to
            msg["Date"] = formatdate(localtime=True)
            if self.use_tls:
                server = smtplib.SMTP(self.host, self.port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
            if self.user:
                server.login(self.user, self.password)
            server.sendmail(self.from_addr, [to], msg.as_string())
            server.quit()
            return EmailResult(ok=True,
                                message_id=msg["Message-ID"] or "smtp")
        except Exception as e:  # pragma: no cover - network errors
            log.error("[EMAIL-SMTP] failed: %s", e)
            return EmailResult(ok=False, error=str(e))


def make_email_service() -> EmailService:
    provider = os.environ.get("WANXIANG_EMAIL_PROVIDER", "noop").lower()
    if provider == "smtp":
        return SmtpEmailService()
    return NoOpEmailService()


__all__ = [
    "EmailResult", "EmailService", "NoOpEmailService",
    "SmtpEmailService", "make_email_service",
]
