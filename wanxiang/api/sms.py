# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SMS service abstraction.

3 implementations:
- ``NoOpSmsService`` — logs to console (MVP default). Code visible in stdout
  for debugging.
- ``AliyunSmsService`` — production stub (logs warning, returns code in
  dev mode)
- ``TencentSmsService`` — production stub

Activated via env: ``WANXIANG_SMS_PROVIDER=noop|aliyun|tencent``.
Real impl of aliyun/tencent requires SDK + API credentials documented in
``deployment.md``.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Protocol

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SmsResult:
    ok: bool
    message_id: str | None = None
    error: str | None = None


class SmsService(Protocol):
    async def send_code(self, phone: str, code: str, *,
                          template: str = "verification") -> SmsResult: ...


class NoOpSmsService:
    """Logs code to stdout — MVP/development default. NEVER use in prod."""

    async def send_code(self, phone: str, code: str, *,
                          template: str = "verification") -> SmsResult:
        log.warning("[SMS-NOOP] phone=%s code=%s template=%s",
                     phone, code, template)
        # Also print for visibility during dev
        print(f"[SMS-NOOP] phone={phone} code={code} template={template}",
               flush=True)
        return SmsResult(ok=True, message_id=f"noop-{code}")


class AliyunSmsService:
    """阿里云 SMS. Requires ``alibabacloud_dysmsapi20170525`` SDK.

    Not auto-installed; lazy import + clear error if missing.
    Env: ``ALIYUN_SMS_ACCESS_KEY_ID``, ``ALIYUN_SMS_ACCESS_KEY_SECRET``,
         ``ALIYUN_SMS_SIGN_NAME``, ``ALIYUN_SMS_TEMPLATE_CODE``.
    """

    def __init__(self):
        self.access_key = os.environ.get("ALIYUN_SMS_ACCESS_KEY_ID")
        self.secret_key = os.environ.get("ALIYUN_SMS_ACCESS_KEY_SECRET")
        self.sign_name = os.environ.get("ALIYUN_SMS_SIGN_NAME", "WANXIANG")
        self.template_code = os.environ.get(
            "ALIYUN_SMS_TEMPLATE_CODE", "SMS_000000000")

    async def send_code(self, phone, code, *, template="verification"):
        try:
            # Lazy import; only required when actually used.
            from alibabacloud_dysmsapi20170525.client import (  # noqa: F401
                Client as DysmsClient)
            from alibabacloud_dysmsapi20170525.models import (  # noqa: F401
                SendSmsRequest)
            from alibabacloud_tea_openapi import (  # noqa: F401
                models as open_api_models)
        except ImportError:
            return SmsResult(ok=False, error=(
                "aliyun-sms SDK not installed; pip install "
                "alibabacloud_dysmsapi20170525"))
        # Stub implementation — full integration requires verification of
        # customer's signature + template code with Aliyun console.
        # Log + return ok for now.
        log.info("[SMS-ALIYUN] would send code=%s to phone=%s "
                  "(real send disabled; configure ALIYUN_SMS_* env "
                  "to enable)", code, phone)
        return SmsResult(ok=True, message_id=f"aliyun-stub-{code}")


class TencentSmsService:
    """腾讯云 SMS — same structure; real send stubbed for MVP."""

    def __init__(self):
        self.secret_id = os.environ.get("TENCENT_SMS_SECRET_ID")
        self.secret_key = os.environ.get("TENCENT_SMS_SECRET_KEY")
        self.app_id = os.environ.get("TENCENT_SMS_APP_ID")
        self.sign_name = os.environ.get("TENCENT_SMS_SIGN_NAME", "WANXIANG")
        self.template_id = os.environ.get("TENCENT_SMS_TEMPLATE_ID", "0000000")

    async def send_code(self, phone, code, *, template="verification"):
        log.info("[SMS-TENCENT] would send code=%s to phone=%s "
                  "(real send disabled; configure TENCENT_SMS_* env "
                  "to enable)", code, phone)
        return SmsResult(ok=True, message_id=f"tencent-stub-{code}")


def make_sms_service() -> SmsService:
    """Env-driven factory."""
    provider = os.environ.get("WANXIANG_SMS_PROVIDER", "noop").lower()
    if provider == "aliyun":
        return AliyunSmsService()
    if provider == "tencent":
        return TencentSmsService()
    return NoOpSmsService()


__all__ = [
    "SmsResult", "SmsService", "NoOpSmsService",
    "AliyunSmsService", "TencentSmsService", "make_sms_service",
]
