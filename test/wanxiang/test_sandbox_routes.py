# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P6: Sandbox routes (CRUD + messages + cross-workspace isolation)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from wanxiang.api import create_app
    app = create_app()
    return TestClient(app)


def _register(client, email, display="User"):
    r = client.post("/v1/auth/register", json={
        "email": email, "password": "Hello123!",
        "display_name": display, "locale": "zh",
    })
    assert r.status_code == 200, r.text
    return r.json()


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


def _make_team(client, headers, name="Team"):
    r = client.post("/v1/workspaces", headers=headers,
                     json={"name": name, "type": "team"})
    assert r.status_code == 200, r.text
    return r.json()


# ---- CRUD ----

def test_create_sandbox_returns_payload(client):
    reg = _register(client, "sbown@x.com", "Owner")
    h = _auth(reg["access_token"])
    ws = _make_team(client, h, "WSA")
    r = client.post(f"/v1/workspaces/{ws['slug']}/sandboxes", headers=h,
                     json={"name": "Box1", "emoji": "🥤",
                           "population_size": 200})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "Box1"
    assert data["emoji"] == "🥤"
    assert data["population_size"] == 200
    assert data["workspace_id"] == ws["workspace_id"]


def test_list_sandboxes_only_shows_workspace_owned(client):
    reg = _register(client, "sblist@x.com", "L")
    h = _auth(reg["access_token"])
    ws_a = _make_team(client, h, "WSA")
    ws_b = _make_team(client, h, "WSB")
    client.post(f"/v1/workspaces/{ws_a['slug']}/sandboxes", headers=h,
                 json={"name": "A1"})
    client.post(f"/v1/workspaces/{ws_a['slug']}/sandboxes", headers=h,
                 json={"name": "A2"})
    client.post(f"/v1/workspaces/{ws_b['slug']}/sandboxes", headers=h,
                 json={"name": "B1"})
    r = client.get(f"/v1/workspaces/{ws_a['slug']}/sandboxes", headers=h)
    assert r.status_code == 200
    names = sorted([s["name"] for s in r.json()["sandboxes"]])
    assert names == ["A1", "A2"]


def test_get_sandbox_404_when_missing(client):
    reg = _register(client, "sb404@x.com", "X")
    h = _auth(reg["access_token"])
    ws = _make_team(client, h, "W404")
    r = client.get(f"/v1/workspaces/{ws['slug']}/sandboxes/nonexistent",
                    headers=h)
    assert r.status_code == 404


def test_patch_sandbox_updates_fields(client):
    reg = _register(client, "sbpatch@x.com", "P")
    h = _auth(reg["access_token"])
    ws = _make_team(client, h, "WP")
    sb = client.post(f"/v1/workspaces/{ws['slug']}/sandboxes", headers=h,
                      json={"name": "Old"}).json()
    r = client.patch(
        f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}",
        headers=h, json={"name": "New", "emoji": "🚀"})
    assert r.status_code == 200
    assert r.json()["name"] == "New"
    assert r.json()["emoji"] == "🚀"


def test_delete_sandbox_then_404(client):
    reg = _register(client, "sbdel@x.com", "D")
    h = _auth(reg["access_token"])
    ws = _make_team(client, h, "WD")
    sb = client.post(f"/v1/workspaces/{ws['slug']}/sandboxes", headers=h,
                      json={"name": "Goner"}).json()
    r = client.delete(
        f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}",
        headers=h)
    assert r.status_code == 200
    r2 = client.get(
        f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}",
        headers=h)
    assert r2.status_code == 404


# ---- Authz ----

def test_create_sandbox_unauth_401(client):
    r = client.post("/v1/workspaces/no-such/sandboxes", json={"name": "X"})
    assert r.status_code == 401


def test_sandbox_non_member_403(client):
    owner = _register(client, "sbowner@x.com", "O")
    intruder = _register(client, "sbintr@x.com", "I")
    ws = _make_team(client, _auth(owner["access_token"]), "PrivWS")
    r = client.post(f"/v1/workspaces/{ws['slug']}/sandboxes",
                     headers=_auth(intruder["access_token"]),
                     json={"name": "Sneak"})
    assert r.status_code == 403


def test_sandbox_cross_workspace_403_on_get(client):
    """Two team workspaces owned by the same user. A sandbox in WS A is
    not addressable via WS B's slug."""
    reg = _register(client, "sbcross@x.com", "C")
    h = _auth(reg["access_token"])
    ws_a = _make_team(client, h, "WSA")
    ws_b = _make_team(client, h, "WSB")
    sb = client.post(f"/v1/workspaces/{ws_a['slug']}/sandboxes",
                      headers=h, json={"name": "InA"}).json()
    r = client.get(
        f"/v1/workspaces/{ws_b['slug']}/sandboxes/{sb['sandbox_id']}",
        headers=h)
    assert r.status_code == 403


# ---- Messages ----

def test_add_message_and_list(client):
    reg = _register(client, "sbmsg@x.com", "M")
    h = _auth(reg["access_token"])
    ws = _make_team(client, h, "WM")
    sb = client.post(f"/v1/workspaces/{ws['slug']}/sandboxes", headers=h,
                      json={"name": "Talky"}).json()
    base = f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}"
    r1 = client.post(f"{base}/messages", headers=h,
                      json={"role": "user", "content": "hello"})
    assert r1.status_code == 200, r1.text
    assert r1.json()["role"] == "user"
    assert r1.json()["user_id"] == reg["user"]["user_id"]
    r2 = client.post(f"{base}/messages", headers=h,
                      json={"role": "assistant",
                            "content": "world", "kind": "text"})
    assert r2.status_code == 200
    # System-authored messages should not carry user_id
    assert r2.json()["user_id"] is None
    lst = client.get(f"{base}/messages", headers=h).json()
    assert len(lst["messages"]) == 2
    contents = [m["content"] for m in lst["messages"]]
    assert contents == ["hello", "world"]


def test_list_messages_after_filter(client):
    reg = _register(client, "sbafter@x.com", "A")
    h = _auth(reg["access_token"])
    ws = _make_team(client, h, "WAft")
    sb = client.post(f"/v1/workspaces/{ws['slug']}/sandboxes", headers=h,
                      json={"name": "Q"}).json()
    base = f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}"
    m1 = client.post(f"{base}/messages", headers=h,
                      json={"role": "user", "content": "1"}).json()
    client.post(f"{base}/messages", headers=h,
                 json={"role": "user", "content": "2"})
    client.post(f"{base}/messages", headers=h,
                 json={"role": "user", "content": "3"})
    r = client.get(f"{base}/messages?after={m1['message_id']}", headers=h)
    assert r.status_code == 200
    contents = [m["content"] for m in r.json()["messages"]]
    assert contents == ["2", "3"]


def test_messages_non_member_403(client):
    owner = _register(client, "msgown@x.com", "O")
    intruder = _register(client, "msgintr@x.com", "I")
    h_o = _auth(owner["access_token"])
    ws = _make_team(client, h_o, "MsgWS")
    sb = client.post(f"/v1/workspaces/{ws['slug']}/sandboxes", headers=h_o,
                      json={"name": "S"}).json()
    base = f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}"
    r = client.get(f"{base}/messages",
                    headers=_auth(intruder["access_token"]))
    assert r.status_code == 403
