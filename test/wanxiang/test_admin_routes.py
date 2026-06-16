# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: Super-admin routes (/v1/admin/*) tests."""
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


def _make_super_admin(client, email):
    """Register a user, then flip is_super_admin via store (back door)."""
    reg = _register(client, email, "Admin")
    user_store = client.app.state.user_store
    u = user_store.get_by_email(email)
    user_store.update(u.user_id, is_super_admin=True)
    return reg


def test_get_admin_users_without_super_admin_403(client):
    reg = _register(client, "bob1@example.com")
    r = client.get("/v1/admin/users", headers=_auth(reg["access_token"]))
    assert r.status_code == 403


def test_get_admin_users_with_super_admin_returns_list(client):
    reg = _make_super_admin(client, "admin1@example.com")
    _register(client, "carol@example.com")
    r = client.get("/v1/admin/users", headers=_auth(reg["access_token"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "users" in body
    emails = [u["email"] for u in body["users"] if u.get("email")]
    assert "admin1@example.com" in emails
    assert "carol@example.com" in emails


def test_get_admin_workspaces_with_super_admin(client):
    reg = _make_super_admin(client, "admin2@example.com")
    r = client.get("/v1/admin/workspaces",
                    headers=_auth(reg["access_token"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "workspaces" in body
    # demo workspace is created by bootstrap
    slugs = [w["slug"] for w in body["workspaces"]]
    assert "demo" in slugs


def test_post_admin_topup_positive_amount_updates_balance(client):
    admin = _make_super_admin(client, "admin3@example.com")
    bob = _register(client, "bob3@example.com")
    bob_ws_id = bob["default_workspace"]["workspace_id"]
    before = bob["default_workspace"]["balance_cost_units"]
    r = client.post("/v1/admin/topup", headers=_auth(admin["access_token"]),
                     json={"workspace_id": bob_ws_id, "amount": 500,
                           "note": "gift"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "topup"
    assert body["delta_cost_units"] == 500
    assert body["balance_after"] == before + 500


def test_post_admin_topup_zero_amount_422(client):
    admin = _make_super_admin(client, "admin4@example.com")
    bob = _register(client, "bob4@example.com")
    r = client.post("/v1/admin/topup", headers=_auth(admin["access_token"]),
                     json={"workspace_id":
                            bob["default_workspace"]["workspace_id"],
                            "amount": 0})
    # Pydantic Field(gt=0) → 422
    assert r.status_code in (400, 422)


def test_post_admin_topup_non_admin_403(client):
    bob = _register(client, "bob5@example.com")
    r = client.post("/v1/admin/topup", headers=_auth(bob["access_token"]),
                     json={"workspace_id":
                            bob["default_workspace"]["workspace_id"],
                            "amount": 100})
    assert r.status_code == 403


def test_post_admin_refund_records_refund_tx(client):
    admin = _make_super_admin(client, "admin5@example.com")
    bob = _register(client, "bob6@example.com")
    bob_ws_id = bob["default_workspace"]["workspace_id"]
    r = client.post("/v1/admin/refund", headers=_auth(admin["access_token"]),
                     json={"workspace_id": bob_ws_id, "amount": 30,
                           "note": "refund-x"})
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "refund"
    assert r.json()["delta_cost_units"] == 30


def test_get_admin_transactions_filter_by_workspace(client):
    admin = _make_super_admin(client, "admin6@example.com")
    bob = _register(client, "bob7@example.com")
    bob_ws = bob["default_workspace"]["workspace_id"]
    client.post("/v1/admin/topup", headers=_auth(admin["access_token"]),
                 json={"workspace_id": bob_ws, "amount": 100})
    client.post("/v1/admin/topup", headers=_auth(admin["access_token"]),
                 json={"workspace_id": bob_ws, "amount": 50})
    r = client.get(f"/v1/admin/transactions?workspace_id={bob_ws}",
                    headers=_auth(admin["access_token"]))
    assert r.status_code == 200, r.text
    txs = r.json()["transactions"]
    assert len(txs) == 2
    assert all(t["workspace_id"] == bob_ws for t in txs)


def test_get_admin_transactions_filter_by_kind(client):
    admin = _make_super_admin(client, "admin7@example.com")
    bob = _register(client, "bob8@example.com")
    bob_ws = bob["default_workspace"]["workspace_id"]
    client.post("/v1/admin/topup", headers=_auth(admin["access_token"]),
                 json={"workspace_id": bob_ws, "amount": 100})
    client.post("/v1/admin/refund", headers=_auth(admin["access_token"]),
                 json={"workspace_id": bob_ws, "amount": 25})
    r = client.get(
        f"/v1/admin/transactions?workspace_id={bob_ws}&kind=refund",
        headers=_auth(admin["access_token"]))
    assert r.status_code == 200, r.text
    txs = r.json()["transactions"]
    assert len(txs) == 1
    assert txs[0]["kind"] == "refund"


def test_get_admin_transactions_orders_desc(client):
    admin = _make_super_admin(client, "admin8@example.com")
    bob = _register(client, "bob9@example.com")
    bob_ws = bob["default_workspace"]["workspace_id"]
    client.post("/v1/admin/topup", headers=_auth(admin["access_token"]),
                 json={"workspace_id": bob_ws, "amount": 1})
    client.post("/v1/admin/topup", headers=_auth(admin["access_token"]),
                 json={"workspace_id": bob_ws, "amount": 2})
    r = client.get(f"/v1/admin/transactions?workspace_id={bob_ws}",
                    headers=_auth(admin["access_token"]))
    txs = r.json()["transactions"]
    assert txs[0]["created_at"] >= txs[1]["created_at"]


def test_patch_super_admin_toggles_flag(client):
    admin = _make_super_admin(client, "admin9@example.com")
    bob = _register(client, "bob10@example.com")
    bob_uid = bob["user"]["user_id"]
    r = client.patch(f"/v1/admin/users/{bob_uid}/super-admin",
                      headers=_auth(admin["access_token"]),
                      json={"user_id": bob_uid, "is_super_admin": True})
    assert r.status_code == 200, r.text
    assert r.json()["is_super_admin"] is True
    # toggle off
    r2 = client.patch(f"/v1/admin/users/{bob_uid}/super-admin",
                       headers=_auth(admin["access_token"]),
                       json={"user_id": bob_uid, "is_super_admin": False})
    assert r2.status_code == 200
    assert r2.json()["is_super_admin"] is False


def test_patch_super_admin_non_admin_403(client):
    bob = _register(client, "bob11@example.com")
    r = client.patch(f"/v1/admin/users/{bob['user']['user_id']}/super-admin",
                      headers=_auth(bob["access_token"]),
                      json={"user_id": bob["user"]["user_id"],
                            "is_super_admin": True})
    assert r.status_code == 403
