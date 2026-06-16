# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Verification code flow routes.

POST /v1/auth/send-email-code     body: {identifier, purpose}
POST /v1/auth/verify-email-code   body: {identifier, code, purpose}
POST /v1/auth/send-sms-code       body: {identifier, purpose}
POST /v1/auth/verify-sms-code     body: {identifier, code, purpose}

For ``purpose="verify"``: marks ``user.email_verified`` or
``phone_verified`` true.
For ``purpose="login"``: (future) login without password using code.
For ``purpose="reset_password"``: (future) issues a reset token.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from wanxiang.api.i18n import get_request_locale, t
from wanxiang.api.users import EMAIL_RE, PHONE_CN_RE
from wanxiang.api.verification import (
    MAX_ATTEMPTS_PER_CODE,
    MAX_SENDS_PER_HOUR,
    TTL_MINUTES,
    VerificationCode,
    generate_code,
    hash_code,
    verify_code,
)

router = APIRouter()


class SendCodeReq(BaseModel):
    identifier: str
    purpose: Literal["verify", "login", "reset_password"] = "verify"


class VerifyCodeReq(BaseModel):
    identifier: str
    code: str = Field(min_length=4, max_length=8)
    purpose: Literal["verify", "login", "reset_password"] = "verify"


def _send_internal(channel: str, identifier: str, purpose: str,
                    request: Request) -> str:
    """Shared send logic for email + sms. Returns the raw code."""
    locale = get_request_locale(request)
    vs = request.app.state.verification_store
    # Rate limit
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    n_recent = vs.count_recent_sends(channel, identifier, since=since)
    if n_recent >= MAX_SENDS_PER_HOUR:
        raise HTTPException(
            429,
            t("auth.verification_rate_limit", locale=locale, n=n_recent))
    # Issue code
    code = generate_code()
    vc = VerificationCode(
        code_id="auto", channel=channel, identifier=identifier,
        purpose=purpose, code_hash=hash_code(code),
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=TTL_MINUTES),
    )
    vs.create(vc)
    return code


@router.post("/auth/send-email-code")
async def send_email_code(req: SendCodeReq, request: Request):
    locale = get_request_locale(request)
    if not EMAIL_RE.match(req.identifier):
        raise HTTPException(
            400, t("auth.invalid_email_format", locale=locale))
    code = _send_internal("email", req.identifier, req.purpose, request)
    es = request.app.state.email_service
    subject_zh = "万象 WANXIANG 验证码"
    subject_en = "WANXIANG verification code"
    title = {"zh": "万象验证码",
              "en": "WANXIANG verification code"}[locale]
    intro = {"zh": "您的验证码是",
              "en": "Your verification code is"}[locale]
    footer = {"zh": f"{TTL_MINUTES} 分钟内有效。如非本人操作，请忽略。",
               "en": (f"Valid for {TTL_MINUTES} minutes. "
                       "Ignore if not requested by you.")}[locale]
    body = (
        "<html><body>"
        f"<h2>{title}</h2>"
        f"<p>{intro}: "
        f"<b style=\"font-size:24px;letter-spacing:4px\">{code}</b></p>"
        f"<p>{footer}</p>"
        "</body></html>"
    )
    await es.send(
        req.identifier,
        subject_zh if locale == "zh" else subject_en,
        body)
    return {"ok": True, "expires_in_seconds": TTL_MINUTES * 60}


@router.post("/auth/verify-email-code")
def verify_email_code(req: VerifyCodeReq, request: Request):
    return _verify_internal("email", req, request)


@router.post("/auth/send-sms-code")
async def send_sms_code(req: SendCodeReq, request: Request):
    locale = get_request_locale(request)
    if not PHONE_CN_RE.match(req.identifier):
        raise HTTPException(
            400, t("auth.invalid_phone_format", locale=locale))
    code = _send_internal("phone", req.identifier, req.purpose, request)
    ss = request.app.state.sms_service
    await ss.send_code(req.identifier, code, template=req.purpose)
    return {"ok": True, "expires_in_seconds": TTL_MINUTES * 60}


@router.post("/auth/verify-sms-code")
def verify_sms_code(req: VerifyCodeReq, request: Request):
    return _verify_internal("phone", req, request)


def _verify_internal(channel: str, req: VerifyCodeReq, request: Request):
    locale = get_request_locale(request)
    vs = request.app.state.verification_store
    vc = vs.latest_active(channel, req.identifier, req.purpose)
    if not vc:
        raise HTTPException(400, t("auth.no_active_code", locale=locale))
    # Check attempts
    if vc.attempts >= MAX_ATTEMPTS_PER_CODE:
        raise HTTPException(
            429, t("auth.too_many_attempts", locale=locale))
    if not verify_code(req.code, vc.code_hash):
        attempts = vs.increment_attempts(vc.code_id)
        remaining = max(0, MAX_ATTEMPTS_PER_CODE - attempts)
        raise HTTPException(
            400,
            t("auth.invalid_code", locale=locale, remaining=remaining))
    # Success: consume
    vs.consume(vc.code_id)
    # If purpose is "verify", mark the user verified
    if req.purpose == "verify":
        us = request.app.state.user_store
        if channel == "email":
            user = us.get_by_email(req.identifier)
            if user:
                us.update(user.user_id, email_verified=True)
        elif channel == "phone":
            user = us.get_by_phone(req.identifier)
            if user:
                us.update(user.user_id, phone_verified=True)
    return {"ok": True, "purpose": req.purpose,
             "verified": (req.purpose == "verify")}
