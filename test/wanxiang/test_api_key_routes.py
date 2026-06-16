# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P3: Workspace-scoped API key management routes."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from wanxiang.api import create_app
    app = create_app()
    return TestClient(app)


def _register(client, email, display_name="User"):
    r = client.post("/v1/auth/register", json={
        "email": email, "password": "Hello123!",
        "display_name": display_name, "locale": "zh",
    })
    assert r.status_code == 200, r.text
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _make_ws(client, owner_token, name="Keys", slug=None):
    body = {"name": name, "type": "team"}
    if slug:
        body["slug"] = slug
    r = client.post("/v1/workspaces", headers=_auth(owner_token), json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_create_api_key_returns_full_key_once(client):
    reg = _register(client, "akcreator@x.com")
    ws = _make_ws(client, reg["access_token"], name="AKWS")
    r = client.post(f"/v1/workspaces/{ws['slug']}/api-keys",
                     headers=_auth(reg["access_token"]),
                     json={"name": "ci-runner", "role": "member",
                           "rpm_limit": 30})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["api_key"].startswith("wxk-")
    assert data["name"] == "ci-runner"
    assert data["rpm_limit"] == 30
    assert "warning" in data


def test_list_api_keys_only_shows_preview(client):
    reg = _register(client, "aklister@x.com")
    ws = _make_ws(client, reg["access_token"], name="ListAK")
    create_r = client.post(f"/v1/workspaces/{ws['slug']}/api-keys",
                            headers=_auth(reg["access_token"]),
                            json={"name": "key1"}).json()
    r = client.get(f"/v1/workspaces/{ws['slug']}/api-keys",
                    headers=_auth(reg["access_token"]))
    assert r.status_code == 200
    keys = r.json()["api_keys"]
    assert len(keys) == 1
    k = keys[0]
    assert "api_key" not in k
    assert k["api_key_preview"].endswith("...")
    assert k["name"] == "key1"


def test_revoke_api_key(client):
    reg = _register(client, "akrevoker@x.com")
    ws = _make_ws(client, reg["access_token"], name="RevokeAK")
    create_r = client.post(f"/v1/workspaces/{ws['slug']}/api-keys",
                            headers=_auth(reg["access_token"]),
                            json={"name": "dying"}).json()
    key_id = create_r["key_id"]
    raw_key = create_r["api_key"]
    r = client.delete(f"/v1/workspaces/{ws['slug']}/api-keys/{key_id}",
                       headers=_auth(reg["access_token"]))
    assert r.status_code == 200
    # Subsequent X-API-Key with revoked key fails
    r2 = client.get("/v1/audit/events", headers={"X-API-Key": raw_key})
    assert r2.status_code == 401


def test_new_key_works_in_xapi_flow(client):
    reg = _register(client, "akxapi@x.com")
    ws = _make_ws(client, reg["access_token"], name="XApi")
    create_r = client.post(f"/v1/workspaces/{ws['slug']}/api-keys",
                            headers=_auth(reg["access_token"]),
                            json={"name": "via-xapi"}).json()
    new_key = create_r["api_key"]
    r = client.get("/v1/audit/events", headers={"X-API-Key": new_key})
    assert r.status_code != 401, r.text


def test_non_admin_member_cannot_create(client):
    owner = _register(client, "akoo@x.com")
    member = _register(client, "akmm@x.com")
    ws = _make_ws(client, owner["access_token"], name="OnlyAdmin")
    inv = client.post(f"/v1/workspaces/{ws['slug']}/invites",
                       headers=_auth(owner["access_token"]),
                       json={"invited_email": "akmm@x.com",
                             "role": "member"}).json()
    client.post("/v1/invites/accept",
                 headers=_auth(member["access_token"]),
                 json={"token": inv["token"]})
    r = client.post(f"/v1/workspaces/{ws['slug']}/api-keys",
                     headers=_auth(member["access_token"]),
                     json={"name": "nope"})
    assert r.status_code == 403


def test_cross_workspace_isolation(client):
    a = _register(client, "wsa@x.com", "Wa")
    b = _register(client, "wsb@x.com", "Wb")
    ws_a = _make_ws(client, a["access_token"], name="A-ws", slug="ws-iso-a")
    ws_b = _make_ws(client, b["access_token"], name="B-ws", slug="ws-iso-b")
    client.post(f"/v1/workspaces/{ws_a['slug']}/api-keys",
                 headers=_auth(a["access_token"]),
                 json={"name": "secret-a"})
    # B lists A's keys → 403 (not a member)
    r = client.get(f"/v1/workspaces/{ws_a['slug']}/api-keys",
                    headers=_auth(b["access_token"]))
    assert r.status_code in (403, 404)
    # B lists their own ws → empty
    r2 = client.get(f"/v1/workspaces/{ws_b['slug']}/api-keys",
                     headers=_auth(b["access_token"]))
    assert r2.status_code == 200
    assert r2.json()["api_keys"] == []
