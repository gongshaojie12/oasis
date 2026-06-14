# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""GET /v1/simulations/{task_id}/events SSE endpoint (M3-11)."""
import os
import time

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


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c


def _body(n=5):
    return {
        "distribution_path": DIST, "n": n, "seed": 1,
        "scenario": {"material": "x", "question": "?", "kind": "rate"},
        "rounds": 0, "model": {"provider": "stub"},
    }


def _wait_done(c, tid, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        s = c.get(f"/v1/simulations/{tid}").json()["status"]
        if s in ("done", "failed"):
            return s
        time.sleep(0.05)
    return None


def test_sse_unknown_task_returns_404(client):
    r = client.get("/v1/simulations/does-not-exist/events")
    assert r.status_code == 404


def test_sse_requires_auth():
    app = create_app()
    c = TestClient(app)
    r = c.get("/v1/simulations/some-id/events")
    assert r.status_code == 401


def test_sse_streams_for_completed_task(client):
    """After async task completes, SSE replay should yield 'started' + 'done'."""
    cr = client.post("/v1/simulations/async", json=_body()).json()
    tid = cr["task_id"]
    status = _wait_done(client, tid)
    assert status in ("done", "failed")

    with client.stream("GET", f"/v1/simulations/{tid}/events") as s:
        chunks = []
        deadline = time.time() + 2.0
        for line in s.iter_lines():
            chunks.append(line)
            joined = "\n".join(chunks)
            if "event: done" in joined or "event: error" in joined:
                break
            if time.time() > deadline:
                break
        joined = "\n".join(chunks)
    assert "event: started" in joined
    assert ("event: done" in joined) or ("event: error" in joined)


def test_sse_tenant_isolation(monkeypatch):
    """Tenant A cannot subscribe to Tenant B's task."""
    monkeypatch.setenv(
        "WANXIANG_TENANTS_JSON",
        '[{"tenant_id":"a","api_key":"sk-a","rpm_limit":60},'
        '{"tenant_id":"b","api_key":"sk-b","rpm_limit":60}]')
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    cr = c.post("/v1/simulations/async",
                headers={"X-API-Key": "sk-a"},
                json=_body()).json()
    tid = cr["task_id"]
    r = c.get(f"/v1/simulations/{tid}/events",
              headers={"X-API-Key": "sk-b"})
    assert r.status_code == 404


def test_sse_correct_content_type(client):
    cr = client.post("/v1/simulations/async", json=_body()).json()
    tid = cr["task_id"]
    _wait_done(client, tid)
    with client.stream("GET", f"/v1/simulations/{tid}/events") as s:
        # consume one line to materialize headers
        for _ in s.iter_lines():
            break
        assert "text/event-stream" in s.headers.get("content-type", "")
