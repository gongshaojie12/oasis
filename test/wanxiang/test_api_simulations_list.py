# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""GET /v1/simulations history-list endpoint."""
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


def _body(n=5):
    return {
        "distribution_path": DIST, "n": n, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "rate"},
        "rounds": 0, "model": {"provider": "stub"}}


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c


def test_list_endpoint_returns_array(client):
    res = client.get("/v1/simulations")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_list_includes_recent_async_task(client):
    # 创一个
    cr = client.post("/v1/simulations/async", json=_body()).json()
    tid = cr["task_id"]
    # 立即列
    lst = client.get("/v1/simulations").json()
    ids = [t["task_id"] for t in lst]
    assert tid in ids


def test_list_pagination(client):
    # 创 3 个
    created = []
    for _ in range(3):
        cr = client.post("/v1/simulations/async", json=_body()).json()
        created.append(cr["task_id"])
        time.sleep(0.01)
    page = client.get("/v1/simulations?limit=2").json()
    assert len(page) <= 2


def test_list_requires_auth():
    app = create_app()
    c = TestClient(app)
    res = c.get("/v1/simulations")
    assert res.status_code == 401


def test_list_tenant_isolation(monkeypatch):
    monkeypatch.setenv("WANXIANG_TENANTS_JSON",
        '[{"tenant_id":"a","api_key":"sk-a","rpm_limit":60},'
        '{"tenant_id":"b","api_key":"sk-b","rpm_limit":60}]')
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    c.post("/v1/simulations/async", headers={"X-API-Key":"sk-a"}, json=_body())
    a_list = c.get("/v1/simulations", headers={"X-API-Key":"sk-a"}).json()
    b_list = c.get("/v1/simulations", headers={"X-API-Key":"sk-b"}).json()
    assert len(a_list) >= 1
    assert b_list == []


def test_sqlite_backed_app_via_env(tmp_path, monkeypatch):
    """WANXIANG_TASKS_DB env triggers Sqlite store; tasks survive a new TestClient."""
    db = str(tmp_path / "tasks.db")
    monkeypatch.setenv("WANXIANG_TASKS_DB", db)
    app1 = create_app()
    app1.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c1 = TestClient(app1)
    c1.headers.update({"X-API-Key": "demo-key"})
    cr = c1.post("/v1/simulations/async", json=_body()).json()
    tid = cr["task_id"]
    # 等任务完成
    for _ in range(50):
        d = c1.get(f"/v1/simulations/{tid}").json()
        if d["status"] in ("done", "failed"):
            break
        time.sleep(0.1)
    # "重启"——新建 app 对象，复用同一个 DB 文件
    app2 = create_app()
    app2.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c2 = TestClient(app2)
    c2.headers.update({"X-API-Key": "demo-key"})
    d = c2.get(f"/v1/simulations/{tid}").json()
    assert d["status"] == "done"
    assert d["result"]["n_valid"] == 5
