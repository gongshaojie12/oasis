# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P5: Full English end-to-end —
locale=en flows from data → persona → prompt → report → response."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory


DIST = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..",
    "wanxiang", "datasources", "distributions",
    "cn_z_generation_v1.yaml"))


@pytest.fixture
def captured_client():
    captured: list[dict] = []

    def factory():
        def f(cfg):
            async def call(messages):
                sys_m = next((x for x in messages if x.get("role") == "system"),
                              None)
                usr_m = next((x for x in messages if x.get("role") == "user"),
                              None)
                captured.append({
                    "sys": sys_m["content"] if sys_m else "",
                    "usr": usr_m["content"] if usr_m else "",
                })
                return '{"score": 7}'
            return call
        return f

    app = create_app()
    app.dependency_overrides[get_model_factory] = factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    c.captured = captured  # type: ignore[attr-defined]
    return c


def test_full_en_pipeline_no_chinese_leaks(captured_client):
    """Run a full simulation in en — verify no Chinese leaks into system prompt."""
    body = {
        "distribution_path": DIST,
        "n": 3,
        "seed": 42,
        "scenario": {
            "material": "Ad copy",
            "question": "buy?",
            "kind": "rate",
        },
        "rounds": 0,
        "model": {"provider": "stub"},
    }
    r = captured_client.post("/v1/simulate", json=body,
                              headers={"accept-language": "en"})
    assert r.status_code == 200, r.text
    sys = "\n".join(c["sys"] for c in captured_client.captured)
    # No CN trait labels / section markers
    for forbidden in ("城市", "性别", "年龄段",
                       "【人口特征】", "【个性向量】", "【媒体习惯】"):
        assert forbidden not in sys, (
            f"leaked zh in en sys prompt: {forbidden}")
    # Has EN labels
    assert "[Demographics]" in sys


def test_full_zh_pipeline_unchanged(captured_client):
    """Default zh path must work exactly as before."""
    body = {
        "distribution_path": DIST,
        "n": 3,
        "seed": 42,
        "scenario": {
            "material": "广告",
            "question": "买吗？",
            "kind": "rate",
        },
        "rounds": 0,
        "model": {"provider": "stub"},
    }
    r = captured_client.post("/v1/simulate", json=body)
    assert r.status_code == 200, r.text
    sys = captured_client.captured[0]["sys"]
    assert "城市" in sys
    assert "【人口特征】" in sys


def test_en_report_full_english(captured_client):
    body = {
        "distribution_path": DIST,
        "n": 3,
        "seed": 42,
        "scenario": {
            "material": "Ad",
            "question": "buy?",
            "kind": "rate",
        },
        "rounds": 0,
        "model": {"provider": "stub"},
    }
    r = captured_client.post("/v1/simulate", json=body,
                              headers={"accept-language": "en"})
    assert r.status_code == 200, r.text
    md = r.json().get("markdown", "")
    assert "WANXIANG" in md
    # Allow some brand chars, but bulk should be English
    cn_count = sum(1 for c in md if '一' <= c <= '鿿')
    assert cn_count < 20, (
        f"too many Chinese chars in en report (got {cn_count}): {md[:300]}")
