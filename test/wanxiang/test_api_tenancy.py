# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""API key auth + tenant + RPM quota."""
import os
import time

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory
from wanxiang.api.tenancy import TenantInfo, TenantStore, TokenBucket

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "test", "wanxiang", "fixtures",
                    "cn_z_generation_v1.yaml")


def _smart_factory(cfg):
    async def call(messages):
        return '{"score": 7}'
    return call


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _smart_factory
    return TestClient(app)


# ---- TenantStore ----

def test_tenant_store_default_has_demo_key():
    store = TenantStore.default()
    info = store.lookup("demo-key")
    assert info is not None
    assert info.tenant_id == "demo"


def test_tenant_store_returns_none_for_unknown_key():
    store = TenantStore.default()
    assert store.lookup("nonexistent-xxx") is None


def test_tenant_store_loads_from_env_json(monkeypatch):
    monkeypatch.setenv("WANXIANG_TENANTS_JSON",
                       '[{"tenant_id":"acme","api_key":"sk-acme","rpm_limit":100}]')
    store = TenantStore.from_env()
    info = store.lookup("sk-acme")
    assert info is not None
    assert info.tenant_id == "acme"
    assert info.rpm_limit == 100
    # demo key should NOT be present when env JSON is set explicitly
    assert store.lookup("demo-key") is None


# ---- TokenBucket ----

def test_token_bucket_allows_within_limit():
    b = TokenBucket(rpm=60)
    for _ in range(5):
        assert b.consume() is True


def test_token_bucket_rejects_over_limit():
    b = TokenBucket(rpm=3)  # 3 / 60s
    assert b.consume() is True
    assert b.consume() is True
    assert b.consume() is True
    assert b.consume() is False  # 4th in same window rejected


def test_token_bucket_refills_over_time():
    b = TokenBucket(rpm=60)  # 1 token per sec
    for _ in range(60):
        b.consume()
    assert b.consume() is False
    time.sleep(1.1)
    assert b.consume() is True  # refilled


# ---- HTTP integration ----

def test_simulate_without_api_key_returns_401(client):
    res = client.post("/v1/simulate", json={
        "distribution_path": DIST, "n": 5, "seed": 1,
        "scenario": {"material":"m","question":"q","kind":"rate"},
        "rounds": 0, "model": {"provider":"stub"}})
    assert res.status_code == 401


def test_simulate_with_unknown_api_key_returns_401(client):
    res = client.post("/v1/simulate",
        headers={"X-API-Key": "definitely-not-valid"},
        json={"distribution_path": DIST, "n": 5, "seed": 1,
              "scenario": {"material":"m","question":"q","kind":"rate"},
              "rounds": 0, "model": {"provider":"stub"}})
    assert res.status_code == 401


def test_simulate_with_demo_key_succeeds(client):
    res = client.post("/v1/simulate",
        headers={"X-API-Key": "demo-key"},
        json={"distribution_path": DIST, "n": 5, "seed": 1,
              "scenario": {"material":"m","question":"q","kind":"rate"},
              "rounds": 0, "model": {"provider":"stub"}})
    assert res.status_code == 200
    # P3: tenant_id is now the demo workspace_id (UUID hex from PG bootstrap).
    # Authoritative source is the api_key lookup; the header is echoed back.
    echoed = res.headers.get("x-tenant-id")
    assert echoed, "x-tenant-id header must be echoed back"
    demo_ws = client.app.state.workspace_store.get_by_slug("demo")
    assert demo_ws is not None
    assert echoed == demo_ws.workspace_id


def test_healthz_does_not_require_auth(client):
    res = client.get("/healthz")
    assert res.status_code == 200


def test_root_chat_does_not_require_auth(client):
    res = client.get("/")
    # Root may not exist if prototype dir missing, but should NOT be 401
    assert res.status_code in (200, 404)


def test_tenant_rpm_quota_returns_429_when_exceeded(monkeypatch):
    """Custom tenant with rpm=2; 3rd call within window → 429."""
    monkeypatch.setenv("WANXIANG_TENANTS_JSON",
                       '[{"tenant_id":"tight","api_key":"sk-tight","rpm_limit":2}]')
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _smart_factory
    c = TestClient(app)
    body = {"distribution_path": DIST, "n": 5, "seed": 1,
            "scenario": {"material":"m","question":"q","kind":"rate"},
            "rounds": 0, "model": {"provider":"stub"}}
    h = {"X-API-Key": "sk-tight"}
    assert c.post("/v1/simulate", headers=h, json=body).status_code == 200
    assert c.post("/v1/simulate", headers=h, json=body).status_code == 200
    third = c.post("/v1/simulate", headers=h, json=body)
    assert third.status_code == 429
    assert "retry-after" in {k.lower() for k in third.headers.keys()}


def test_tenant_id_header_from_client_is_ignored_when_authenticated(client):
    """Client cannot spoof tenant via X-Tenant-Id; authoritative source is API key."""
    res = client.post("/v1/simulate",
        headers={"X-API-Key": "demo-key", "X-Tenant-Id": "spoofed-evil"},
        json={"distribution_path": DIST, "n": 5, "seed": 1,
              "scenario": {"material":"m","question":"q","kind":"rate"},
              "rounds": 0, "model": {"provider":"stub"}})
    assert res.status_code == 200
    # P3: tenant_id is now demo workspace_id, definitely NOT 'spoofed-evil'
    echoed = res.headers.get("x-tenant-id")
    assert echoed != "spoofed-evil"
    demo_ws = client.app.state.workspace_store.get_by_slug("demo")
    assert demo_ws is not None
    assert echoed == demo_ws.workspace_id
