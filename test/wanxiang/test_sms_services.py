# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P2: SMS service abstractions (NoOp / Aliyun / Tencent) + factory."""
from __future__ import annotations

import asyncio

import pytest


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) \
        if False else asyncio.run(coro)


def test_noop_returns_ok_and_message_id(capsys):
    from wanxiang.api.sms import NoOpSmsService

    svc = NoOpSmsService()
    result = _run(svc.send_code("13800138000", "482917"))
    assert result.ok is True
    assert result.message_id is not None
    assert result.message_id.startswith("noop-")
    # Stdout visibility for dev
    out = capsys.readouterr().out
    assert "482917" in out
    assert "13800138000" in out


def test_make_sms_service_default_is_noop(monkeypatch):
    monkeypatch.delenv("WANXIANG_SMS_PROVIDER", raising=False)
    from wanxiang.api.sms import make_sms_service, NoOpSmsService

    svc = make_sms_service()
    assert isinstance(svc, NoOpSmsService)


def test_make_sms_service_aliyun(monkeypatch):
    monkeypatch.setenv("WANXIANG_SMS_PROVIDER", "aliyun")
    from wanxiang.api.sms import make_sms_service, AliyunSmsService

    svc = make_sms_service()
    assert isinstance(svc, AliyunSmsService)


def test_make_sms_service_tencent(monkeypatch):
    monkeypatch.setenv("WANXIANG_SMS_PROVIDER", "tencent")
    from wanxiang.api.sms import make_sms_service, TencentSmsService

    svc = make_sms_service()
    assert isinstance(svc, TencentSmsService)


def test_aliyun_returns_ok_stub():
    from wanxiang.api.sms import AliyunSmsService

    svc = AliyunSmsService()
    result = _run(svc.send_code("13800138000", "111111"))
    # stub: SDK missing -> error; SDK present -> ok stub
    assert result.ok is True or "SDK" in (result.error or "")


def test_tencent_returns_ok_stub():
    from wanxiang.api.sms import TencentSmsService

    svc = TencentSmsService()
    result = _run(svc.send_code("13800138000", "222222"))
    assert result.ok is True
    assert result.message_id is not None
    assert "tencent-stub" in result.message_id
