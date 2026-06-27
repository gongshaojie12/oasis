# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/causal & /v1/counterfactual 端点。"""
import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "test", "wanxiang", "fixtures",
                    "cn_z_generation_v1.yaml")


def _smart_factory():
    def factory(cfg):
        async def call(messages):
            m = messages[1]["content"]
            if "卖点" in m and "渠道" in m: return '{"score": 9}'
            if "卖点" in m: return '{"score": 7}'
            if "渠道" in m: return '{"score": 6}'
            return '{"score": 4}'
        return call
    return factory


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _smart_factory()
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c


def test_causal_endpoint_returns_ranked_contributions(client):
    body = {
        "baseline": {
            "distribution_path": DIST, "n": 10, "seed": 1,
            "scenario": {"material": "卖点 + 渠道",
                          "question": "0-10 评分", "kind": "rate"},
            "rounds": 0, "model": {"provider": "stub"},
        },
        "factors": [
            {"id": "value_prop", "label": "卖点", "snippet": "卖点"},
            {"id": "channel", "label": "渠道", "snippet": "渠道"},
        ],
    }
    res = client.post("/v1/causal", json=body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["contributions"]) == 2
    assert data["contributions"][0]["rank"] == 1


def test_counterfactual_endpoint_returns_outcomes(client):
    body = {
        "baseline": {
            "distribution_path": DIST, "n": 10, "seed": 1,
            "scenario": {"material": "卖点 + 渠道",
                          "question": "0-10 评分", "kind": "rate"},
            "rounds": 0, "model": {"provider": "stub"},
        },
        "baseline_label": "原方案",
        "alternatives": [
            {"id": "only_prop", "label": "去掉渠道",
             "material_override": "卖点"},
            {"id": "only_chan", "label": "去掉卖点",
             "material_override": "渠道"},
        ],
    }
    res = client.post("/v1/counterfactual", json=body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["baseline_label"] == "原方案"
    assert len(data["outcomes"]) == 2


def test_causal_requires_auth():
    app = create_app()
    c = TestClient(app)
    res = c.post("/v1/causal", json={"baseline": {}, "factors": []})
    assert res.status_code == 401


def test_counterfactual_requires_auth():
    app = create_app()
    c = TestClient(app)
    res = c.post("/v1/counterfactual",
                 json={"baseline": {}, "alternatives": []})
    assert res.status_code == 401
