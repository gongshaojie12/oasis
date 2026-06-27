# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SimulateRequest.platform: API 接收平台名，路由到 SocialRoundsRunner with dialect."""
import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory

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


def test_simulate_accepts_platform_field(client):
    body = {
        "distribution_path": DIST, "n": 5, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "rate"},
        "rounds": 1,
        "platform": "wechat",
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["decision_kind"] == "rate"


def test_simulate_rejects_unknown_platform(client):
    body = {
        "distribution_path": DIST, "n": 5, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "rate"},
        "rounds": 1, "platform": "totally_unknown_platform",
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    # 400 (业务层抛) 或 422 (schema 拒) 都可接受
    assert res.status_code in (400, 422)


def test_simulate_without_platform_still_works(client):
    """back-compat: 旧客户端不传 platform，行为不变。"""
    body = {
        "distribution_path": DIST, "n": 5, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "rate"},
        "rounds": 1,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 200


def test_simulate_platform_ignored_in_decision_only(client):
    """rounds=0 时 platform 无意义；不应报错。"""
    body = {
        "distribution_path": DIST, "n": 5, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "rate"},
        "rounds": 0,
        "platform": "wechat",
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 200
