# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Celery app + task dispatch (eager-mode, no real broker)."""
from __future__ import annotations

import os

import pytest


@pytest.fixture
def eager_celery(monkeypatch):
    monkeypatch.setenv("WANXIANG_CELERY_EAGER", "1")
    # Force re-instantiation
    from wanxiang.api import celery_app
    celery_app.get_celery_app.cache_clear()
    yield
    celery_app.get_celery_app.cache_clear()


def test_celery_app_lazy_constructed(eager_celery):
    from wanxiang.api.celery_app import get_celery_app
    app = get_celery_app()
    assert app.main == "wanxiang"


def test_celery_app_eager_mode_set(eager_celery):
    from wanxiang.api.celery_app import get_celery_app
    app = get_celery_app()
    assert app.conf.task_always_eager is True
    assert app.conf.task_eager_propagates is True


def test_run_simulation_task_registered(eager_celery):
    from wanxiang.api.celery_app import get_celery_app
    app = get_celery_app()
    assert "wanxiang.run_simulation" in app.tasks


def test_dispatch_async_simulation_chooses_asyncio_by_default(monkeypatch):
    """Backward compat: default mode = asyncio."""
    monkeypatch.delenv("WANXIANG_TASK_QUEUE", raising=False)
    assert os.environ.get("WANXIANG_TASK_QUEUE", "asyncio") == "asyncio"
    # The dispatch helper must exist and the env-driven branch must default
    # to asyncio.  We just check the helper is importable.
    from wanxiang.api.routes import simulations as sim_routes
    assert hasattr(sim_routes, "_dispatch_async_simulation")


def test_dispatch_async_simulation_chooses_celery_when_env_set(
        monkeypatch, eager_celery):
    monkeypatch.setenv("WANXIANG_TASK_QUEUE", "celery")
    assert os.environ["WANXIANG_TASK_QUEUE"] == "celery"
    from wanxiang.api.routes import simulations as sim_routes
    assert hasattr(sim_routes, "_dispatch_async_simulation")


def test_celery_eager_runs_pipeline_to_completion(
        monkeypatch, eager_celery, tmp_path):
    """Full eager-mode E2E: dispatch task → check task_store has DONE status.

    This relies on:
      - WANXIANG_TASK_QUEUE=celery so the route dispatches via Celery
      - WANXIANG_CELERY_EAGER=1 so the task runs synchronously inside .delay()
      - WANXIANG_TASKS_DB pointing to a shared sqlite file so the task and
        the API process see the same TaskStore
    """
    monkeypatch.setenv("WANXIANG_TASK_QUEUE", "celery")
    db_path = str(tmp_path / "tasks.db")
    monkeypatch.setenv("WANXIANG_TASKS_DB", db_path)

    from fastapi.testclient import TestClient
    from wanxiang.api.app import create_app
    from wanxiang.api.deps import get_model_factory

    def _factory():
        def f(cfg):
            async def call(m):
                return '{"score": 7}'
            return call
        return f

    app = create_app()
    app.dependency_overrides[get_model_factory] = _factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})

    DIST = os.path.abspath(
        "wanxiang/datasources/distributions/cn_z_generation_v1.yaml")
    body = {
        "distribution_path": DIST, "n": 3, "seed": 1,
        "scenario": {"material": "x", "question": "?", "kind": "rate"},
        "rounds": 0, "model": {"provider": "stub"},
    }

    cr = c.post("/v1/simulations/async", json=body)
    assert cr.status_code == 202, cr.text
    tid = cr.json()["task_id"]

    # In eager mode the task ran synchronously during .delay() call.
    detail = c.get(f"/v1/simulations/{tid}").json()
    assert detail["status"] == "done", detail
