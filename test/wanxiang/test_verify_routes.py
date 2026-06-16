# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P2: /v1/auth/{send,verify}-{email,sms}-code routes."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_fakes():
    from wanxiang.api import create_app
    from wanxiang.api.email import EmailResult
    from wanxiang.api.sms import SmsResult

    sent_emails: list[dict] = []
    sent_sms: list[dict] = []

    class FakeEmail:
        async def send(self, to, subject, body_html, *, body_text=None):
            import re
            m = re.search(r"(\d{6})", body_html)
            sent_emails.append({
                "to": to, "subject": subject,
                "code": m.group(1) if m else None,
                "body": body_html,
            })
            return EmailResult(ok=True, message_id="fake")

    class FakeSms:
        async def send_code(self, phone, code, *, template="verification"):
            sent_sms.append({"phone": phone, "code": code,
                              "template": template})
            return SmsResult(ok=True, message_id=f"fake-{code}")

    app = create_app()
    app.state.email_service = FakeEmail()
    app.state.sms_service = FakeSms()
    client = TestClient(app)
    return client, sent_emails, sent_sms, app


def test_send_email_bad_format_400(app_with_fakes):
    client, *_ = app_with_fakes
    r = client.post("/v1/auth/send-email-code",
                     json={"identifier": "not-an-email"})
    assert r.status_code == 400


def test_send_email_ok_returns_expiry(app_with_fakes):
    client, sent_emails, _, _ = app_with_fakes
    r = client.post("/v1/auth/send-email-code",
                     json={"identifier": "alice@example.com"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["expires_in_seconds"] == 600
    assert sent_emails and sent_emails[-1]["to"] == "alice@example.com"
    assert sent_emails[-1]["code"] is not None
    assert len(sent_emails[-1]["code"]) == 6


def test_send_email_rate_limit_after_5(app_with_fakes):
    client, *_ = app_with_fakes
    for _ in range(5):
        r = client.post("/v1/auth/send-email-code",
                         json={"identifier": "rate@example.com"})
        assert r.status_code == 200
    r = client.post("/v1/auth/send-email-code",
                     json={"identifier": "rate@example.com"})
    assert r.status_code == 429


def test_verify_email_no_active_code_400(app_with_fakes):
    client, *_ = app_with_fakes
    r = client.post("/v1/auth/verify-email-code",
                     json={"identifier": "none@example.com",
                           "code": "123456"})
    assert r.status_code == 400


def test_verify_email_wrong_code_returns_remaining(app_with_fakes):
    client, sent_emails, _, _ = app_with_fakes
    client.post("/v1/auth/send-email-code",
                 json={"identifier": "wrong@example.com"})
    r = client.post("/v1/auth/verify-email-code",
                     json={"identifier": "wrong@example.com",
                           "code": "000000"})
    assert r.status_code == 400
    # message mentions remaining count somewhere
    detail = r.json()["detail"]
    assert "4" in detail or "remaining" in detail or "剩余" in detail


def test_verify_email_correct_code_returns_verified(app_with_fakes):
    client, sent_emails, _, _ = app_with_fakes
    client.post("/v1/auth/send-email-code",
                 json={"identifier": "ok@example.com"})
    code = sent_emails[-1]["code"]
    r = client.post("/v1/auth/verify-email-code",
                     json={"identifier": "ok@example.com", "code": code})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["verified"] is True
    assert body["purpose"] == "verify"


def test_verify_email_after_5_wrong_attempts_429(app_with_fakes):
    client, sent_emails, _, _ = app_with_fakes
    client.post("/v1/auth/send-email-code",
                 json={"identifier": "attempts@example.com"})
    for _ in range(5):
        client.post("/v1/auth/verify-email-code",
                     json={"identifier": "attempts@example.com",
                           "code": "000000"})
    r = client.post("/v1/auth/verify-email-code",
                     json={"identifier": "attempts@example.com",
                           "code": "000000"})
    # After 5 attempts the code is exhausted - returns 400 (no active) or 429
    assert r.status_code in (400, 429)


def test_send_sms_bad_phone_400(app_with_fakes):
    client, *_ = app_with_fakes
    r = client.post("/v1/auth/send-sms-code",
                     json={"identifier": "not-a-phone"})
    assert r.status_code == 400


def test_send_sms_ok_invokes_sms_service(app_with_fakes):
    client, _, sent_sms, _ = app_with_fakes
    r = client.post("/v1/auth/send-sms-code",
                     json={"identifier": "13800138000"})
    assert r.status_code == 200, r.text
    assert sent_sms and sent_sms[-1]["phone"] == "13800138000"
    assert len(sent_sms[-1]["code"]) == 6


def test_verify_sms_success_path(app_with_fakes):
    client, _, sent_sms, _ = app_with_fakes
    client.post("/v1/auth/send-sms-code",
                 json={"identifier": "13800138001"})
    code = sent_sms[-1]["code"]
    r = client.post("/v1/auth/verify-sms-code",
                     json={"identifier": "13800138001", "code": code})
    assert r.status_code == 200, r.text
    assert r.json()["verified"] is True


def test_verify_email_marks_user_email_verified(app_with_fakes):
    """If a user exists with this email, success flips email_verified true."""
    client, sent_emails, _, app = app_with_fakes
    # Register a user via P1 register route
    reg = client.post("/v1/auth/register", json={
        "email": "user2verify@example.com", "password": "Hello123!",
        "display_name": "V",
    })
    assert reg.status_code == 200, reg.text
    user_store = app.state.user_store
    u = user_store.get_by_email("user2verify@example.com")
    assert u is not None and u.email_verified is False

    # Send + verify
    client.post("/v1/auth/send-email-code",
                 json={"identifier": "user2verify@example.com"})
    code = sent_emails[-1]["code"]
    r = client.post("/v1/auth/verify-email-code",
                     json={"identifier": "user2verify@example.com",
                           "code": code})
    assert r.status_code == 200

    u2 = user_store.get_by_email("user2verify@example.com")
    assert u2.email_verified is True


def test_noop_email_captures_code_in_stdout(capsys):
    """Default app uses NoOpEmailService — code shows in stdout for dev."""
    from wanxiang.api import create_app

    app = create_app()
    client = TestClient(app)
    r = client.post("/v1/auth/send-email-code",
                     json={"identifier": "stdout@example.com"})
    assert r.status_code == 200
    out = capsys.readouterr().out
    # NoOp prints subject + body preview; the 6-digit code is in there
    import re
    assert re.search(r"\d{6}", out) is not None
