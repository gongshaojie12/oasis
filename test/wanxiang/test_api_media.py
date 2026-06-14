# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""HTTP: ScenarioPayload accepts media_pool + feed_k; flows through pipeline."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "wanxiang", "datasources", "distributions",
                    "cn_z_generation_v1.yaml")


@pytest.fixture
def client():
    captured = {"sys_msgs": []}

    def factory(cfg):
        async def call(messages):
            sys = next(m for m in messages
                       if m["role"] == "system")["content"]
            captured["sys_msgs"].append(sys)
            return '{"score": 7}'
        return call

    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    c.captured = captured  # type: ignore[attr-defined]
    return c


def _body(media_pool=None, feed_k=0):
    return {
        "distribution_path": DIST, "n": 3, "seed": 1,
        "scenario": {
            "material": "广告 X", "question": "买不买？", "kind": "rate",
            "media_pool": media_pool or [], "feed_k": feed_k,
        },
        "rounds": 0,
        "model": {"provider": "stub"},
    }


def test_scenario_without_media_pool_works(client):
    r = client.post("/v1/simulate", json=_body())
    assert r.status_code == 200, r.text


def test_scenario_with_media_pool_and_feed_k_works(client):
    body = _body(media_pool=[
        {"item_id": "a", "title": "精选好物", "channel": "xhs",
         "tags": ["coffee"]},
        {"item_id": "b", "title": "爆款", "channel": "douyin",
         "tags": ["fashion"]},
    ], feed_k=2)
    r = client.post("/v1/simulate", json=body)
    assert r.status_code == 200, r.text


def test_media_pool_flows_into_prompts(client):
    body = _body(media_pool=[
        {"item_id": "a", "title": "独家爆款必看", "channel": "xhs"},
    ], feed_k=1)
    r = client.post("/v1/simulate", json=body)
    assert r.status_code == 200, r.text
    joined = "\n".join(client.captured["sys_msgs"])
    assert "独家爆款必看" in joined
    assert "信息流" in joined


def test_feed_k_zero_with_pool_means_no_injection(client):
    body = _body(media_pool=[
        {"item_id": "a", "title": "独家爆款必看", "channel": "xhs"},
    ], feed_k=0)
    r = client.post("/v1/simulate", json=body)
    assert r.status_code == 200
    joined = "\n".join(client.captured["sys_msgs"])
    assert "独家爆款必看" not in joined


def test_invalid_media_item_rejected(client):
    body = _body()
    body["scenario"]["media_pool"] = [{"channel": "xhs"}]  # missing id+title
    r = client.post("/v1/simulate", json=body)
    assert r.status_code in (400, 422)
