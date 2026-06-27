# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""HTTP integration: middleware writes audit events, GET endpoint reads them."""
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
    async def call(m):
        return '{"score": 5}'
    return call


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c


def _body(n=3):
    return {"distribution_path": DIST, "n": n, "seed": 1,
            "scenario": {"material": "x", "question": "?", "kind": "rate"},
            "rounds": 0, "model": {"provider": "stub"}}


def test_audit_empty_for_new_tenant(client):
    r = client.get("/v1/audit/events")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_post_simulate_creates_audit_record(client):
    r = client.post("/v1/simulate", json=_body())
    assert r.status_code == 200
    a = client.get("/v1/audit/events").json()
    assert a["total"] >= 1
    assert any(e["path"] == "/v1/simulate" for e in a["events"])


def test_audit_action_filter(client):
    client.post("/v1/simulate", json=_body())
    a = client.get("/v1/audit/events?action=api_call").json()
    assert a["total"] >= 1
    assert all(e["action"] == "api_call" for e in a["events"])


def test_audit_records_status(client):
    """A 4xx response is also audited with the right status code."""
    client.post("/v1/simulate", json={"bad": "request"})
    a = client.get("/v1/audit/events").json()
    # at least one event with status 4xx
    assert any(e["status"] and e["status"] >= 400 for e in a["events"])


def test_audit_requires_auth():
    app = create_app()
    c = TestClient(app)
    r = c.get("/v1/audit/events")
    assert r.status_code == 401


def test_audit_tenant_isolation(monkeypatch):
    monkeypatch.setenv(
        "WANXIANG_TENANTS_JSON",
        '[{"tenant_id":"a","api_key":"sk-a","rpm_limit":60},'
        '{"tenant_id":"b","api_key":"sk-b","rpm_limit":60}]')
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    c.post("/v1/simulate", headers={"X-API-Key": "sk-a"}, json=_body())
    a = c.get("/v1/audit/events", headers={"X-API-Key": "sk-a"}).json()
    b = c.get("/v1/audit/events", headers={"X-API-Key": "sk-b"}).json()
    assert a["total"] >= 1
    assert b["total"] == 0
