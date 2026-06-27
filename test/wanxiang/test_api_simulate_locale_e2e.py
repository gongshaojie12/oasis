# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""End-to-end: locale flows from request → report markdown."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory

DIST = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..",
    "test", "wanxiang", "fixtures", "cn_z_generation_v1.yaml",
))


def _stub_factory(cfg):
    async def call(messages):
        return '{"score": 7}'
    return call


def _body(locale=None):
    b = {
        "distribution_path": DIST, "n": 3, "seed": 1,
        "scenario": {"material": "广告", "question": "买吗？",
                      "kind": "rate"},
        "rounds": 0, "model": {"provider": "stub"},
    }
    if locale:
        b["locale"] = locale
    return b


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c


def test_default_simulate_returns_zh_report(client):
    r = client.post("/v1/simulate", json=_body())
    assert r.status_code == 200, r.text
    md = r.json().get("markdown") or ""
    assert "万象" in md


def test_body_locale_en_returns_english_report(client):
    r = client.post("/v1/simulate", json=_body(locale="en"))
    assert r.status_code == 200, r.text
    md = r.json().get("markdown") or ""
    assert "WANXIANG" in md
    assert "Recommendation" in md or "Aggregate" in md


def test_header_accept_language_en_returns_english(client):
    r = client.post("/v1/simulate",
                     headers={"X-API-Key": "demo-key",
                              "accept-language": "en"},
                     json=_body())
    assert r.status_code == 200, r.text
    md = r.json().get("markdown") or ""
    assert "WANXIANG" in md
    assert "Recommendation" in md or "Aggregate" in md


def test_body_locale_overrides_header(client):
    r = client.post("/v1/simulate",
                     headers={"X-API-Key": "demo-key",
                              "accept-language": "zh"},
                     json=_body(locale="en"))
    assert r.status_code == 200, r.text
    md = r.json().get("markdown") or ""
    assert "Recommendation" in md or "Aggregate" in md


def test_report_locale_field_persisted(client):
    r = client.post("/v1/simulate", json=_body(locale="en"))
    assert r.status_code == 200, r.text
    body = r.json()
    rep = body.get("report") or {}
    # report dict should carry the locale field
    assert rep.get("locale") == "en"
    md = body.get("markdown") or ""
    assert "WANXIANG" in md
