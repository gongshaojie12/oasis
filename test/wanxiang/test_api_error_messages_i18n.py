# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""End-to-end: API errors are localized."""
import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app


def test_missing_api_key_en():
    app = create_app()
    c = TestClient(app)
    r = c.get("/v1/audit/events", headers={"accept-language":"en"})
    assert r.status_code == 401
    assert "API" in r.json()["detail"]
    # Must NOT contain Chinese
    assert "缺少" not in r.json()["detail"] and "无效" not in r.json()["detail"]


def test_invalid_api_key_zh_default():
    app = create_app()
    c = TestClient(app)
    r = c.get("/v1/audit/events", headers={"X-API-Key":"bogus"})
    assert r.status_code == 401
    # Chinese default
    assert any(ch in r.json()["detail"] for ch in ("无效","缺少","API"))


def test_invalid_api_key_en():
    app = create_app()
    c = TestClient(app)
    r = c.get("/v1/audit/events",
              headers={"X-API-Key":"bogus","accept-language":"en"})
    assert r.status_code == 401
    assert "Invalid" in r.json()["detail"] or "Missing" in r.json()["detail"]


def test_report_pdf_xor_error_en():
    app = create_app()
    c = TestClient(app)
    r = c.post("/v1/reports/pdf",
               headers={"X-API-Key":"demo-key","accept-language":"en"},
               json={})
    assert r.status_code == 400
    assert "markdown" in r.json()["detail"].lower() or "task_id" in r.json()["detail"].lower()
    # No Chinese
    assert "必须" not in r.json()["detail"]


def test_report_pdf_xor_error_zh():
    app = create_app()
    c = TestClient(app)
    r = c.post("/v1/reports/pdf",
               headers={"X-API-Key":"demo-key"},
               json={})
    assert r.status_code == 400
    assert any(ch in r.json()["detail"] for ch in ("必须","markdown","task_id"))


def test_audit_invalid_datetime_en():
    app = create_app()
    c = TestClient(app)
    r = c.get("/v1/audit/events?start=notadate",
              headers={"X-API-Key":"demo-key","accept-language":"en"})
    assert r.status_code == 400
    assert "iso" in r.json()["detail"].lower() or "datetime" in r.json()["detail"].lower()
