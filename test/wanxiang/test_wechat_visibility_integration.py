# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""End-to-end: scenario.platform=wechat → SocialRoundsRunner uses FriendGraph."""
import asyncio
import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api import create_app
from wanxiang.api.deps import get_model_factory
from wanxiang.personas.persona import Persona
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig
from wanxiang.simulation.social import SocialRoundsRunner
from wanxiang.social_graph.graph import generate_small_world

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "wanxiang", "datasources", "distributions",
                    "cn_z_generation_v1.yaml")


@pytest.fixture
def captured_client():
    captured = {"user_msgs": []}

    def factory():
        def f(cfg):
            async def call(msgs):
                user = next((m for m in msgs if m["role"] == "user"), None)
                if user:
                    captured["user_msgs"].append(user["content"])
                return '{"score": 7}'
            return call
        return f

    app = create_app()
    app.dependency_overrides[get_model_factory] = factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    c.captured = captured  # type: ignore
    return c


def _body(platform=None, rounds=1, n=10):
    body = {
        "distribution_path": DIST, "n": n, "seed": 1,
        "scenario": {"material": "广告", "question": "买不买？", "kind": "rate"},
        "rounds": rounds, "model": {"provider": "stub"},
    }
    if platform:
        body["platform"] = platform
    return body


def test_wechat_runs_without_error(captured_client):
    r = captured_client.post("/v1/simulate", json=_body(platform="wechat"))
    assert r.status_code == 200, r.text


def test_xiaohongshu_runs_without_error(captured_client):
    r = captured_client.post("/v1/simulate", json=_body(platform="xiaohongshu"))
    assert r.status_code == 200, r.text


def test_wechat_with_n_below_k_works(captured_client):
    """n=3 < k=6 → complete graph → 仍然能跑通。"""
    r = captured_client.post("/v1/simulate", json=_body(platform="wechat", n=3))
    assert r.status_code == 200, r.text


def test_wechat_runner_uses_friend_graph_directly():
    """直接用 SocialRoundsRunner + friend_graph 跑 → 每个 focal 都跑了 2 轮。"""
    personas = [
        Persona(agent_id=i, name=f"p{i}",
                demographic={}, personality={}, media={})
        for i in range(8)
    ]
    ids = [f"agent_{i}" for i in range(8)]
    g = generate_small_world(ids, k=4, seed=7)

    captured = []

    async def call(messages):
        captured.append(messages[-1]["content"])
        return '{"score": 5}'

    runner = SocialRoundsRunner(
        rounds=1, decision_concurrency=4,
        friend_graph=g, persona_ids=ids,
    )
    final, history = asyncio.run(runner.run(
        personas,
        ScenarioConfig(material="m", question="0-10 评分",
                       decision_kind=DecisionKind.RATE),
        call,
    ))
    # 8 personas * 2 rounds = 16 调用
    assert len(captured) == 16
    # round 1 (after round 0) 的 user msg 含 【同辈参考】
    round1 = captured[8:]
    assert all("【同辈参考】" in m for m in round1)
    assert len(final) == 8
    assert len(history) == 2
