# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Async simulation task endpoints."""
import asyncio
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


def _slow_stub_factory(delay):
    def factory(cfg):
        async def call(messages):
            await asyncio.sleep(delay)
            return '{"score": 7}'
        return call
    return factory


def _body(n=5):
    return {
        "distribution_path": DIST, "n": n, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "rate"},
        "rounds": 0, "model": {"provider": "stub"}
    }


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c


# ---- POST /v1/simulations/async ----

def test_async_create_returns_202_with_task_id(client):
    res = client.post("/v1/simulations/async", json=_body())
    assert res.status_code == 202
    body = res.json()
    assert "task_id" in body
    assert body["status"] in {"pending", "running", "done"}


def test_async_requires_auth():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    res = c.post("/v1/simulations/async", json=_body())
    assert res.status_code == 401


# ---- GET /v1/simulations/{task_id} ----

def test_get_task_unknown_id_returns_404(client):
    res = client.get("/v1/simulations/nonexistent-id-xxx")
    assert res.status_code == 404


def test_get_task_eventually_returns_done_with_result(client):
    res = client.post("/v1/simulations/async", json=_body(n=10))
    task_id = res.json()["task_id"]
    # 轮询最多 5 秒
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        get = client.get(f"/v1/simulations/{task_id}")
        assert get.status_code == 200
        data = get.json()
        if data["status"] == "done":
            assert data["result"]["n_total"] == 10
            assert data["result"]["n_valid"] >= 8
            assert "markdown" in data["result"]
            return
        if data["status"] == "failed":
            pytest.fail(f"task failed: {data.get('error')}")
        time.sleep(0.05)
    pytest.fail("task did not complete within 5s")


def test_get_task_includes_timestamps(client):
    res = client.post("/v1/simulations/async", json=_body())
    task_id = res.json()["task_id"]
    # 等到 done
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        get = client.get(f"/v1/simulations/{task_id}").json()
        if get["status"] == "done":
            assert get["created_at"] is not None
            assert get["started_at"] is not None
            assert get["finished_at"] is not None
            return
        time.sleep(0.05)
    pytest.fail("task did not complete")


def test_task_status_progression(client):
    """新建后立即查 → 应是 pending 或 running（很快就会变 done）。"""
    res = client.post("/v1/simulations/async", json=_body())
    task_id = res.json()["task_id"]
    # 立即拿状态——可能 pending/running/done 都接受，但不应是 failed
    first = client.get(f"/v1/simulations/{task_id}").json()
    assert first["status"] in {"pending", "running", "done"}


def test_tenant_cannot_see_other_tenants_task(monkeypatch):
    """两个不同 api key 的 client，B 不能查 A 的 task。"""
    monkeypatch.setenv("WANXIANG_TENANTS_JSON",
        '[{"tenant_id":"a","api_key":"sk-a","rpm_limit":60},'
        '{"tenant_id":"b","api_key":"sk-b","rpm_limit":60}]')
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)

    # A 建 task
    res_a = c.post("/v1/simulations/async",
                   headers={"X-API-Key": "sk-a"}, json=_body())
    assert res_a.status_code == 202
    task_id = res_a.json()["task_id"]

    # B 查不到（404，不是 200 也不是 403）
    res_b = c.get(f"/v1/simulations/{task_id}",
                  headers={"X-API-Key": "sk-b"})
    assert res_b.status_code == 404

    # A 自己能查到
    res_a2 = c.get(f"/v1/simulations/{task_id}",
                   headers={"X-API-Key": "sk-a"})
    assert res_a2.status_code == 200


def test_failed_task_reports_error(monkeypatch):
    """模型工厂抛异常 → 任务标 failed + error 字段。"""
    app = create_app()

    def boom_factory():
        def factory(cfg):
            async def call(messages):
                raise RuntimeError("simulated failure for test")
            return call
        return factory

    app.dependency_overrides[get_model_factory] = boom_factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})

    res = c.post("/v1/simulations/async", json=_body(n=3))
    task_id = res.json()["task_id"]
    # 注意：模型抛错被 DecisionRunner 吞掉装到 result.error；
    # 整个任务仍会"成功完成"，n_valid=0。
    # 我们想测真正的任务级失败：构造一个会让 build_report 之前阶段崩的场景
    # 最稳的真失败：用一个不存在的 distribution path（会在 pipeline 早期 raise）
    res2 = c.post("/v1/simulations/async", json={
        **_body(), "distribution_path": "/totally/nonexistent.yaml"})
    bad_id = res2.json()["task_id"]
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        d = c.get(f"/v1/simulations/{bad_id}").json()
        if d["status"] == "failed":
            assert d["error"]
            assert "not found" in d["error"].lower() or \
                   "找不到" in d["error"]
            return
        time.sleep(0.05)
    pytest.fail("expected task to fail but it did not")
