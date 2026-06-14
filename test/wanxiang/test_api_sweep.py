# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/simulations/sweep — sync grid expansion."""
import os
import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "wanxiang", "datasources", "distributions",
                    "cn_z_generation_v1.yaml")


def _stub_factory(cfg):
    async def call(messages):
        return '{"score": 7}'
    return call


def _body(n=10, grid=None, material="广告：{copy}", question="买不买？{channel}"):
    return {
        "distribution_path": DIST, "n": n, "seed": 1,
        "scenario": {"material": material, "question": question, "kind": "rate"},
        "rounds": 0, "model": {"provider": "stub"},
        "variable_grid": grid or {"copy": ["A", "B"], "channel": ["xhs", "douyin"]},
    }


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c


def test_sweep_2x2_returns_4_combos(client):
    r = client.post("/v1/simulations/sweep", json=_body())
    assert r.status_code == 200
    body = r.json()
    assert body["total_combos"] == 4
    assert len(body["combos"]) == 4


def test_sweep_each_combo_has_result(client):
    r = client.post("/v1/simulations/sweep", json=_body())
    for c in r.json()["combos"]:
        assert c["error"] is None
        assert c["result"] is not None
        assert "report" in c["result"]
        assert c["task_id"] is None  # sync mode


def test_sweep_combo_id_format(client):
    r = client.post("/v1/simulations/sweep", json=_body())
    ids = sorted(c["combo_id"] for c in r.json()["combos"])
    assert ids == [
        "channel=douyin|copy=A",
        "channel=douyin|copy=B",
        "channel=xhs|copy=A",
        "channel=xhs|copy=B",
    ]


def test_sweep_substitutes_into_material(client):
    """The combos with copy=A should have A baked into material, etc.
    Verify the report's material field round-trips back to us."""
    r = client.post("/v1/simulations/sweep", json=_body(
        material="测试：{copy}", question="多少分？"))
    combos = r.json()["combos"]
    # 4 combos but only 2 distinct copy values, so 2 distinct materials
    materials = {c["result"]["report"]["scenario"]["material"] for c in combos}
    assert materials == {"测试：A", "测试：B"}


def test_sweep_requires_auth():
    app = create_app()
    c = TestClient(app)
    r = c.post("/v1/simulations/sweep", json=_body())
    assert r.status_code == 401


def test_sweep_empty_grid_rejected(client):
    body = _body()
    body["variable_grid"] = {}
    r = client.post("/v1/simulations/sweep", json=body)
    assert r.status_code in (400, 422)


def test_sweep_empty_axis_rejected(client):
    body = _body()
    body["variable_grid"] = {"copy": []}
    r = client.post("/v1/simulations/sweep", json=body)
    assert r.status_code in (400, 422)


def test_sweep_too_many_combos_rejected(client):
    body = _body()
    # 11 × 11 = 121 > 100
    body["variable_grid"] = {
        "a": [f"v{i}" for i in range(11)],
        "b": [f"v{i}" for i in range(11)],
    }
    r = client.post("/v1/simulations/sweep", json=body)
    assert r.status_code == 400
    assert "100" in r.json()["detail"]


def test_sweep_at_exactly_100_combos_works(client):
    body = _body(n=2)  # n small to keep test fast
    body["variable_grid"] = {
        "a": [f"v{i}" for i in range(10)],
        "b": [f"v{i}" for i in range(10)],
    }
    r = client.post("/v1/simulations/sweep", json=body)
    assert r.status_code == 200
    assert r.json()["total_combos"] == 100


def test_sweep_records_usage_per_combo(client):
    """4 combos × n=10 decision_only = 40 cost units total."""
    client.post("/v1/simulations/sweep", json=_body(n=10))
    u = client.get("/v1/usage/current").json()
    # 4 combos × 10 agents (decision_only) = 40
    assert u["total_cost_units"] == 40
    # 4 distinct events recorded
    assert len([e for e in u["events"] if e["mode"] == "decision_only"]) == 4


def test_sweep_per_combo_failure_does_not_abort_rest():
    """One combo failing should not kill the others."""
    app = create_app()
    counter = {"n": 0}

    def factory():
        def f(cfg):
            async def call(msgs):
                counter["n"] += 1
                if counter["n"] <= 2:  # first 2 calls boom
                    raise RuntimeError("boom")
                return '{"score": 5}'
            return call
        return f
    app.dependency_overrides[get_model_factory] = factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    r = c.post("/v1/simulations/sweep", json=_body(n=3))
    assert r.status_code == 200
    body = r.json()
    assert body["total_combos"] == 4
    # at least 1 combo succeeded
    ok = [x for x in body["combos"] if x["result"] is not None]
    assert len(ok) >= 1
