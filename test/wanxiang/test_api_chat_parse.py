# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/chat/parse endpoint."""
import json
import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "test", "wanxiang", "fixtures",
                    "cn_z_generation_v1.yaml")


def _factory_returning(text):
    def factory(cfg):
        async def call(messages):
            return text
        return call
    return factory


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _factory_returning(
        json.dumps({
            "intent": "simulate",
            "fields": {"material": "新品 ¥6", "question": "0-10 评分",
                        "kind": "rate", "options": None, "n": 100,
                        "rounds": 0},
            "missing": [],
            "explanation": "识别为购买意愿评分",
            "confidence": 0.91
        }))
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c


def test_chat_parse_requires_auth():
    app = create_app()
    c = TestClient(app)
    res = c.post("/v1/chat/parse", json={"user_text": "x"})
    assert res.status_code == 401


def test_chat_parse_happy_path(client):
    res = client.post("/v1/chat/parse",
                      json={"user_text": "测一线 Z 世代对新品 ¥6 的购买意愿",
                            "default_distribution_path": DIST})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["intent"] == "simulate"
    assert body["request"] is not None
    assert body["request"]["scenario"]["kind"] == "rate"
    assert body["request"]["distribution_path"].endswith(
        "cn_z_generation_v1.yaml")


def test_chat_parse_with_explicit_default_distribution(client):
    res = client.post("/v1/chat/parse",
                      json={"user_text": "随便", "default_distribution_path": "/abs/x.yaml"})
    assert res.status_code == 200
    body = res.json()
    if body["request"] is not None:
        assert body["request"]["distribution_path"] == "/abs/x.yaml"


def test_chat_parse_uses_bundled_default_when_not_provided(client):
    """没传 default_distribution_path → 用内置默认 cn_national_joint_2020。"""
    res = client.post("/v1/chat/parse", json={"user_text": "测一下"})
    assert res.status_code == 200
    body = res.json()
    if body["request"] is not None:
        assert "cn_national_joint_2020" in body["request"]["distribution_path"]


def test_chat_parse_then_simulate_chain(client):
    """parse → 拿到 request → 直接喂给 /v1/simulate（端到端）。"""
    p = client.post("/v1/chat/parse",
                    json={"user_text": "测购买意愿",
                          "default_distribution_path": DIST}).json()
    assert p["request"] is not None
    sim = client.post("/v1/simulate", json=p["request"])
    assert sim.status_code == 200, sim.text
    assert sim.json()["decision_kind"] == "rate"
