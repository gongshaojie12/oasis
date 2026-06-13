# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/simulate 端点测试。

用 dependency_override 注入一个"参考 user prompt schema 关键字"的可控
smart stub，避免依赖 camel STUB 的 'Lorem Ipsum' 输出（那会导致全部
DecisionResult.error 非空，n_valid=0，造成报告无法生成）。
"""
import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "wanxiang", "datasources", "distributions",
                    "cn_z_generation_v1.yaml")


def _smart_stub_factory(cfg):
    """忽略 cfg；按 user prompt 中的 schema 关键字返回合规 JSON。"""

    async def call(messages):
        user = messages[-1]["content"]
        if "score" in user.lower():
            return '{"score": 7}'
        if "option" in user.lower() or "选项" in user:
            return '{"option": "青提"}'
        if "polarity" in user.lower():
            return '{"polarity": 0.5}'
        if "probability" in user.lower():
            return '{"probability": 0.6}'
        if "price" in user.lower():
            return '{"price": 8}'
        return '{"score": 5}'

    return call


@pytest.fixture
def client():
    app = create_app()
    # 把工厂自身替换：路由 Depends(get_model_factory) 收到的应是一个会被
    # 当成"工厂函数"调用的对象，调用结果是 ModelCall。
    app.dependency_overrides[get_model_factory] = lambda: _smart_stub_factory
    c = TestClient(app)
    # M3-3: /v1/* 现在需要 X-API-Key；用默认 demo 租户跑测试
    c.headers.update({"X-API-Key": "demo-key"})
    return c


def test_simulate_rate_returns_full_report(client):
    body = {
        "distribution_path": DIST, "n": 30, "seed": 1,
        "scenario": {"material": "m", "question": "0-10 评分", "kind": "rate"},
        "rounds": 0, "concurrency": 8,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["decision_kind"] == "rate"
    assert data["n_total"] == 30
    assert data["n_valid"] >= 25
    assert data["error_count"] <= 5
    assert "万象模拟报告" in data["markdown"]
    assert data["report"]["recommendation"]["mean"] is not None


def test_simulate_choose_returns_recommendation(client):
    body = {
        "distribution_path": DIST, "n": 20, "seed": 2,
        "scenario": {"material": "m", "question": "挑一个", "kind": "choose",
                     "options": ["青提", "白桃", "海盐荔枝"]},
        "rounds": 0, "concurrency": 8,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["decision_kind"] == "choose"
    assert data["report"]["recommendation"]["top"] in {"青提", "白桃", "海盐荔枝"}


def test_simulate_validation_error_returns_422(client):
    body = {
        "distribution_path": DIST, "n": 5, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "choose"},
        "rounds": 0,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 422


def test_simulate_missing_distribution_file_returns_400(client):
    body = {
        "distribution_path": "/nonexistent/xxx.yaml", "n": 5, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "rate"},
        "rounds": 0,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 400
    body = res.json()
    assert "detail" in body
    assert "not found" in body["detail"].lower() or "找不到" in body["detail"]


def test_simulate_with_social_rounds(client):
    body = {
        "distribution_path": DIST, "n": 10, "seed": 1,
        "scenario": {"material": "m", "question": "0-10 评分", "kind": "rate"},
        "rounds": 1, "concurrency": 4,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["n_total"] == 10


def test_simulate_returns_elapsed_ms(client):
    body = {
        "distribution_path": DIST, "n": 5, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "rate"},
        "rounds": 0,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["elapsed_ms"], int)
    assert data["elapsed_ms"] >= 0
