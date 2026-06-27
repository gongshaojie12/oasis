# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/reports/pdf —— markdown / task_id → PDF bytes."""
from __future__ import annotations

import asyncio
import os
import time

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory
from wanxiang.reporting import pdf as pdf_module

_has_reportlab = pdf_module.REPORTLAB_AVAILABLE

pytestmark = pytest.mark.skipif(
    not _has_reportlab, reason="reportlab not installed")

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "test", "wanxiang", "fixtures",
                    "cn_z_generation_v1.yaml")


def _stub_factory(cfg):
    async def call(messages):
        return '{"score": 7}'
    return call


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c


def test_pdf_from_markdown_returns_pdf(client):
    res = client.post("/v1/reports/pdf",
                      json={"markdown": "# 测试报告\n\n正文内容"})
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")


def test_pdf_without_markdown_or_task_id_returns_400(client):
    res = client.post("/v1/reports/pdf", json={})
    assert res.status_code == 400


def test_pdf_with_both_markdown_and_task_id_returns_400(client):
    res = client.post("/v1/reports/pdf",
                      json={"markdown": "x", "task_id": "abc"})
    assert res.status_code == 400


def test_pdf_with_nonexistent_task_id_returns_404(client):
    res = client.post("/v1/reports/pdf",
                      json={"task_id": "nonexistent-id-12345"})
    assert res.status_code == 404


def test_pdf_without_auth_returns_401():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    # no X-API-Key header
    res = c.post("/v1/reports/pdf", json={"markdown": "x"})
    assert res.status_code == 401
