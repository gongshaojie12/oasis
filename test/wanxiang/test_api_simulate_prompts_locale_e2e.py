# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4 e2e: POST /v1/simulate locale flows to system + user prompts."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory

DIST = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..",
    "wanxiang", "datasources", "distributions", "cn_z_generation_v1.yaml",
))


def _captured_factory(captured: list):
    def factory(cfg):
        async def call(messages):
            sys = next((x for x in messages if x["role"] == "system"), None)
            usr = next((x for x in messages if x["role"] == "user"), None)
            captured.append({
                "sys": sys["content"] if sys else "",
                "usr": usr["content"] if usr else "",
            })
            return '{"score": 7}'

        return call

    return factory


def _body(locale=None):
    b = {
        "distribution_path": DIST, "n": 1, "seed": 1,
        "scenario": {"material": "广告", "question": "买吗？",
                      "kind": "rate"},
        "rounds": 0, "model": {"provider": "stub"},
    }
    if locale:
        b["locale"] = locale
    return b


@pytest.fixture
def app_and_captured():
    captured: list = []
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _captured_factory(
        captured)
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c, captured


def test_default_locale_yields_chinese_system_prompt(app_and_captured):
    c, captured = app_and_captured
    r = c.post("/v1/simulate", json=_body())
    assert r.status_code == 200, r.text
    assert captured, "model should have been called at least once"
    sys = captured[0]["sys"]
    assert "【人口特征】" in sys
    assert "[Demographics]" not in sys


def test_locale_en_body_yields_english_system_and_user_prompts(
        app_and_captured):
    c, captured = app_and_captured
    r = c.post("/v1/simulate", json=_body(locale="en"))
    assert r.status_code == 200, r.text
    assert captured
    sys = captured[0]["sys"]
    usr = captured[0]["usr"]
    assert "[Demographics]" in sys
    assert "【人口特征】" not in sys
    # User msg labels: Material / Question (not 【材料】/【问题】)
    assert "Material" in usr or "Question" in usr
    assert "【材料】" not in usr


def test_locale_en_threaded_via_scenario_config(app_and_captured):
    """Independent of report markdown: prompt itself is EN."""
    c, captured = app_and_captured
    r = c.post("/v1/simulate", json=_body(locale="en"))
    assert r.status_code == 200, r.text
    # decision_kind echoes back
    assert r.json()["decision_kind"] == "rate"
    # Verify prompt language end-to-end
    sys = captured[0]["sys"]
    assert "Personality" in sys or "Demographics" in sys
