# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P3: X-API-Key flow now resolves via api_key_store (PG-backed)."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from wanxiang.api import create_app
    app = create_app()
    return TestClient(app)


def _register(client, email):
    r = client.post("/v1/auth/register", json={
        "email": email, "password": "Hello123!",
        "display_name": "U", "locale": "zh",
    })
    assert r.status_code == 200, r.text
    return r.json()


def test_legacy_demo_key_still_works(client):
    """Bootstrap ensures demo-key is provisioned. /v1/audit/events accepts it."""
    r = client.get("/v1/audit/events", headers={"X-API-Key": "demo-key"})
    assert r.status_code != 401, r.text


def test_new_api_key_via_route_works_in_xapi(client):
    reg = _register(client, "newkeyflow@x.com")
    h = {"Authorization": f"Bearer {reg['access_token']}"}
    ws = client.post("/v1/workspaces", headers=h,
                      json={"name": "Flow", "type": "team"}).json()
    create_r = client.post(f"/v1/workspaces/{ws['slug']}/api-keys",
                            headers=h, json={"name": "k1"}).json()
    new_key = create_r["api_key"]
    r = client.get("/v1/audit/events", headers={"X-API-Key": new_key})
    assert r.status_code != 401


def test_revoked_key_returns_401(client):
    reg = _register(client, "revokeme@x.com")
    h = {"Authorization": f"Bearer {reg['access_token']}"}
    ws = client.post("/v1/workspaces", headers=h,
                      json={"name": "RevFlow", "type": "team"}).json()
    create_r = client.post(f"/v1/workspaces/{ws['slug']}/api-keys",
                            headers=h, json={"name": "rev"}).json()
    new_key = create_r["api_key"]
    key_id = create_r["key_id"]
    # Pre-revoke works
    r = client.get("/v1/audit/events", headers={"X-API-Key": new_key})
    assert r.status_code != 401
    # Revoke
    client.delete(f"/v1/workspaces/{ws['slug']}/api-keys/{key_id}", headers=h)
    # Post-revoke 401
    r2 = client.get("/v1/audit/events", headers={"X-API-Key": new_key})
    assert r2.status_code == 401


def test_legacy_tenants_json_env_seeds_api_keys(monkeypatch):
    """If WANXIANG_TENANTS_JSON is set, bootstrap migrates each tenant
    as an additional api_key. demo-key still wins, plus the env ones."""
    monkeypatch.setenv(
        "WANXIANG_TENANTS_JSON",
        json.dumps([
            {"tenant_id": "legacy-acme", "api_key": "legacy-acme-key",
             "rpm_limit": 60}
        ]))
    from wanxiang.api import create_app
    app = create_app()
    c = TestClient(app)
    r = c.get("/v1/audit/events", headers={"X-API-Key": "legacy-acme-key"})
    assert r.status_code != 401, r.text


def test_invalid_key_returns_401(client):
    r = client.get("/v1/audit/events", headers={"X-API-Key": "bogus-key-xyz"})
    assert r.status_code == 401
