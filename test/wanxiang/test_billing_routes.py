# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: Workspace-scoped billing routes (members can see own ws balance/tx)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from wanxiang.api import create_app
    app = create_app()
    return TestClient(app)


def _register(client, email, display_name=None):
    r = client.post("/v1/auth/register", json={
        "email": email, "password": "Hello123!",
        "display_name": display_name or email.split("@")[0],
        "locale": "zh",
    })
    assert r.status_code == 200, r.text
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _make_admin(client, email):
    reg = _register(client, email, "Admin")
    user_store = client.app.state.user_store
    u = user_store.get_by_email(email)
    user_store.update(u.user_id, is_super_admin=True)
    return reg


def test_get_workspace_balance_as_member(client):
    bob = _register(client, "bob100@example.com")
    slug = bob["default_workspace"]["slug"]
    r = client.get(f"/v1/workspaces/{slug}/balance",
                    headers=_auth(bob["access_token"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == slug
    assert "balance_cost_units" in body


def test_get_workspace_balance_non_member_403(client):
    a = _register(client, "alice100@example.com")
    b = _register(client, "bob200@example.com")
    slug_a = a["default_workspace"]["slug"]
    r = client.get(f"/v1/workspaces/{slug_a}/balance",
                    headers=_auth(b["access_token"]))
    assert r.status_code == 403


def test_balance_reflects_topup_and_admin_credit_chain(client):
    admin = _make_admin(client, "admin100@example.com")
    bob = _register(client, "bob300@example.com")
    bob_ws = bob["default_workspace"]
    slug = bob_ws["slug"]
    before = bob_ws["balance_cost_units"]
    client.post("/v1/admin/topup", headers=_auth(admin["access_token"]),
                 json={"workspace_id": bob_ws["workspace_id"],
                       "amount": 500, "note": "gift"})
    r = client.get(f"/v1/workspaces/{slug}/balance",
                    headers=_auth(bob["access_token"]))
    assert r.json()["balance_cost_units"] == before + 500


def test_workspace_transactions_list_for_member(client):
    admin = _make_admin(client, "admin200@example.com")
    bob = _register(client, "bob400@example.com")
    bob_ws = bob["default_workspace"]
    slug = bob_ws["slug"]
    client.post("/v1/admin/topup", headers=_auth(admin["access_token"]),
                 json={"workspace_id": bob_ws["workspace_id"], "amount": 100})
    r = client.get(f"/v1/workspaces/{slug}/transactions",
                    headers=_auth(bob["access_token"]))
    assert r.status_code == 200, r.text
    txs = r.json()["transactions"]
    assert len(txs) == 1
    assert txs[0]["kind"] == "topup"


def test_cross_workspace_isolation(client):
    admin = _make_admin(client, "admin300@example.com")
    a = _register(client, "alice300@example.com")
    b = _register(client, "bob500@example.com")
    # Top up A only
    client.post("/v1/admin/topup", headers=_auth(admin["access_token"]),
                 json={"workspace_id": a["default_workspace"]["workspace_id"],
                       "amount": 100})
    # B's transactions should be empty
    r = client.get(
        f"/v1/workspaces/{b['default_workspace']['slug']}/transactions",
        headers=_auth(b["access_token"]))
    assert r.status_code == 200
    assert r.json()["transactions"] == []


def test_filter_by_kind_for_workspace_transactions(client):
    admin = _make_admin(client, "admin400@example.com")
    bob = _register(client, "bob600@example.com")
    ws_id = bob["default_workspace"]["workspace_id"]
    slug = bob["default_workspace"]["slug"]
    client.post("/v1/admin/topup", headers=_auth(admin["access_token"]),
                 json={"workspace_id": ws_id, "amount": 100})
    client.post("/v1/admin/refund", headers=_auth(admin["access_token"]),
                 json={"workspace_id": ws_id, "amount": 50})
    r = client.get(
        f"/v1/workspaces/{slug}/transactions?kind=refund",
        headers=_auth(bob["access_token"]))
    txs = r.json()["transactions"]
    assert len(txs) == 1
    assert txs[0]["kind"] == "refund"
