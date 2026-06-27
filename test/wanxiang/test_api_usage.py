# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""GET /v1/usage/{current,monthly} endpoints + usage recording integration."""
import os
import time

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


def _body(n=10, rounds=0, platform=None):
    b = {"distribution_path": DIST, "n": n, "seed": 1,
         "scenario": {"material": "m", "question": "q", "kind": "rate"},
         "rounds": rounds, "model": {"provider": "stub"}}
    if platform:
        b["platform"] = platform
    return b


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c


def test_usage_current_empty_for_new_tenant(client):
    res = client.get("/v1/usage/current")
    assert res.status_code == 200
    body = res.json()
    assert body["total_cost_units"] == 0
    assert body["events"] == []


def test_ws_usage_current_with_jwt():
    """Workspace-scoped JWT version of /usage/current (for SPA frontend)."""
    app = create_app()
    c = TestClient(app)
    # Register a user → returns JWT + default workspace
    r = c.post("/v1/auth/register", json={
        "email": "billtest@x.com", "password": "Hello123!",
        "display_name": "BillTest",
    })
    assert r.status_code == 200
    tok = r.json()["access_token"]
    slug = r.json()["default_workspace"]["slug"]
    # Brand-new workspace: usage MUST return empty, not error
    res = c.get(f"/v1/workspaces/{slug}/usage/current",
                 headers={"Authorization": f"Bearer {tok}"})
    assert res.status_code == 200
    body = res.json()
    assert body["total_cost_units"] == 0
    assert body["events"] == []


def test_ws_usage_current_404_for_unknown_workspace():
    app = create_app()
    c = TestClient(app)
    r = c.post("/v1/auth/register", json={
        "email": "billtest2@x.com", "password": "Hello123!",
        "display_name": "BillTest2",
    })
    tok = r.json()["access_token"]
    res = c.get("/v1/workspaces/nonexistent-slug/usage/current",
                 headers={"Authorization": f"Bearer {tok}"})
    assert res.status_code == 404


def test_ws_usage_current_403_for_non_member():
    app = create_app()
    c = TestClient(app)
    # User A creates workspace via register
    a = c.post("/v1/auth/register", json={
        "email": "alice_bill@x.com", "password": "Hello123!",
        "display_name": "Alice",
    }).json()
    a_slug = a["default_workspace"]["slug"]
    # User B tries to access A's usage
    b = c.post("/v1/auth/register", json={
        "email": "bob_bill@x.com", "password": "Hello123!",
        "display_name": "Bob",
    }).json()
    res = c.get(f"/v1/workspaces/{a_slug}/usage/current",
                 headers={"Authorization": f"Bearer {b['access_token']}"})
    assert res.status_code == 403


def test_sync_simulate_records_usage(client):
    r = client.post("/v1/simulate", json=_body(n=50))
    assert r.status_code == 200
    u = client.get("/v1/usage/current").json()
    assert u["total_cost_units"] == 50  # decision_only, n=50
    assert u["by_mode"]["decision_only"] == 50
    assert len(u["events"]) == 1


def test_social_mode_costs_more(client):
    client.post("/v1/simulate", json=_body(n=10, rounds=2))
    u = client.get("/v1/usage/current").json()
    # social: n * (rounds+1) = 10 * 3 = 30
    assert u["total_cost_units"] == 30
    assert u["by_mode"]["social"] == 30


def test_platform_mode_has_premium(client):
    client.post("/v1/simulate", json=_body(n=10, rounds=2, platform="wechat"))
    u = client.get("/v1/usage/current").json()
    # platform: 10 * 3 * 1.5 = 45
    assert u["total_cost_units"] == 45
    assert u["by_mode"]["platform"] == 45


def test_async_simulate_also_records_usage(client):
    cr = client.post("/v1/simulations/async", json=_body(n=20)).json()
    tid = cr["task_id"]
    for _ in range(50):
        d = client.get(f"/v1/simulations/{tid}").json()
        if d["status"] in ("done", "failed"):
            break
        time.sleep(0.05)
    u = client.get("/v1/usage/current").json()
    assert u["total_cost_units"] == 20


def test_usage_current_requires_auth():
    app = create_app()
    c = TestClient(app)
    assert c.get("/v1/usage/current").status_code == 401


def test_usage_monthly_endpoint(client):
    client.post("/v1/simulate", json=_body(n=5))
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    r = client.get(f"/v1/usage/monthly?year={now.year}&month={now.month}")
    assert r.status_code == 200
    assert r.json()["total_cost_units"] == 5


def test_usage_monthly_invalid_returns_422_or_400(client):
    r = client.get("/v1/usage/monthly?year=2026&month=13")
    assert r.status_code in (400, 422)


def test_tenant_cannot_see_others_usage(monkeypatch):
    monkeypatch.setenv("WANXIANG_TENANTS_JSON",
        '[{"tenant_id":"a","api_key":"sk-a","rpm_limit":60},'
        '{"tenant_id":"b","api_key":"sk-b","rpm_limit":60}]')
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    c.post("/v1/simulate", headers={"X-API-Key":"sk-a"}, json=_body(n=42))
    a_u = c.get("/v1/usage/current", headers={"X-API-Key":"sk-a"}).json()
    b_u = c.get("/v1/usage/current", headers={"X-API-Key":"sk-b"}).json()
    assert a_u["total_cost_units"] == 42
    assert b_u["total_cost_units"] == 0


def test_failed_simulate_also_records_usage(client):
    """模型抛错的失败任务也算账（compute cost 已经消耗）。"""
    app2 = create_app()
    def boom_factory():
        def f(cfg):
            async def call(messages):
                raise RuntimeError("boom")
            return call
        return f
    app2.dependency_overrides[get_model_factory] = boom_factory
    c2 = TestClient(app2)
    c2.headers.update({"X-API-Key": "demo-key"})
    # 走 async 路径（sync 会异常抛出，async 落到 task.error）
    cr = c2.post("/v1/simulations/async", json=_body(n=8)).json()
    tid = cr["task_id"]
    for _ in range(50):
        d = c2.get(f"/v1/simulations/{tid}").json()
        if d["status"] in ("done", "failed"):
            break
        time.sleep(0.05)
    u = c2.get("/v1/usage/current").json()
    # 即便 status=failed（model 抛错被 DecisionRunner 吞掉是 done with errors，
    # 真 failed 需要 pipeline 异常；这里 stub 抛 RuntimeError 被 dispatch_action
    # 包成 result.error，aggregate 仍跑 → done，n_valid=0），usage 仍记录
    assert u["total_cost_units"] == 8  # 8 agents
