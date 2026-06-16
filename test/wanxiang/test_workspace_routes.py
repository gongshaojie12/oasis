# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P3: Workspace routes (CRUD + members + invites)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from wanxiang.api import create_app
    app = create_app()
    return TestClient(app)


def _register_user(client, email, display_name="User"):
    r = client.post("/v1/auth/register", json={
        "email": email, "password": "Hello123!",
        "display_name": display_name, "locale": "zh",
    })
    assert r.status_code == 200, r.text
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---- Create / List / Get ----

def test_create_team_workspace_returns_workspace(client):
    reg = _register_user(client, "owner1@x.com", "Owner")
    h = _auth(reg["access_token"])
    r = client.post("/v1/workspaces", headers=h,
                     json={"name": "My Team", "type": "team"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "My Team"
    assert data["type"] == "team"
    assert data["slug"]


def test_create_workspace_duplicate_slug_409(client):
    reg = _register_user(client, "owner2@x.com", "Owner2")
    h = _auth(reg["access_token"])
    client.post("/v1/workspaces", headers=h,
                 json={"name": "Acme", "type": "team", "slug": "acme-team"})
    r = client.post("/v1/workspaces", headers=h,
                     json={"name": "Acme2", "type": "team",
                           "slug": "acme-team"})
    assert r.status_code == 409


def test_list_workspaces_includes_personal_and_team(client):
    reg = _register_user(client, "lister@x.com", "Lister")
    h = _auth(reg["access_token"])
    client.post("/v1/workspaces", headers=h,
                 json={"name": "T1", "type": "team"})
    r = client.get("/v1/workspaces", headers=h)
    assert r.status_code == 200, r.text
    types = [w["type"] for w in r.json()["workspaces"]]
    assert "personal" in types
    assert "team" in types


def test_get_workspace_as_member_ok(client):
    reg = _register_user(client, "getter@x.com", "Getter")
    h = _auth(reg["access_token"])
    create_resp = client.post("/v1/workspaces", headers=h,
                               json={"name": "G", "type": "team"}).json()
    slug = create_resp["slug"]
    r = client.get(f"/v1/workspaces/{slug}", headers=h)
    assert r.status_code == 200
    assert r.json()["slug"] == slug


def test_get_workspace_as_non_member_403(client):
    a = _register_user(client, "alpha@x.com", "Alpha")
    b = _register_user(client, "beta@x.com", "Beta")
    create_resp = client.post("/v1/workspaces", headers=_auth(a["access_token"]),
                               json={"name": "Private", "type": "team"}).json()
    r = client.get(f"/v1/workspaces/{create_resp['slug']}",
                    headers=_auth(b["access_token"]))
    assert r.status_code == 403


# ---- Update ----

def test_patch_workspace_as_admin_or_owner(client):
    reg = _register_user(client, "patcher@x.com", "Patcher")
    h = _auth(reg["access_token"])
    create_resp = client.post("/v1/workspaces", headers=h,
                               json={"name": "OldName", "type": "team"}).json()
    slug = create_resp["slug"]
    r = client.patch(f"/v1/workspaces/{slug}", headers=h,
                      json={"name": "NewName"})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "NewName"


def test_patch_workspace_as_plain_member_403(client):
    owner = _register_user(client, "ownerpatch@x.com", "OwnerP")
    member = _register_user(client, "memberpatch@x.com", "MemberP")
    ws = client.post("/v1/workspaces",
                      headers=_auth(owner["access_token"]),
                      json={"name": "Mod", "type": "team"}).json()
    # Owner invites member
    inv = client.post(f"/v1/workspaces/{ws['slug']}/invites",
                       headers=_auth(owner["access_token"]),
                       json={"invited_email": "memberpatch@x.com",
                             "role": "member"}).json()
    client.post("/v1/invites/accept",
                 headers=_auth(member["access_token"]),
                 json={"token": inv["token"]})
    # Member attempts PATCH
    r = client.patch(f"/v1/workspaces/{ws['slug']}",
                      headers=_auth(member["access_token"]),
                      json={"name": "Hacked"})
    assert r.status_code == 403


# ---- Delete ----

def test_delete_personal_workspace_400(client):
    reg = _register_user(client, "personalowner@x.com", "PO")
    h = _auth(reg["access_token"])
    # Get the auto-created personal workspace
    wsm = client.get("/v1/workspaces", headers=h).json()["workspaces"]
    personal = [w for w in wsm if w["type"] == "personal"][0]
    r = client.delete(f"/v1/workspaces/{personal['slug']}", headers=h)
    assert r.status_code == 400


def test_delete_team_as_non_owner_403(client):
    owner = _register_user(client, "deletownr@x.com", "DOwner")
    other = _register_user(client, "delotherone@x.com", "Other")
    ws = client.post("/v1/workspaces",
                      headers=_auth(owner["access_token"]),
                      json={"name": "Delete", "type": "team"}).json()
    inv = client.post(f"/v1/workspaces/{ws['slug']}/invites",
                       headers=_auth(owner["access_token"]),
                       json={"invited_email": "delotherone@x.com",
                             "role": "admin"}).json()
    client.post("/v1/invites/accept",
                 headers=_auth(other["access_token"]),
                 json={"token": inv["token"]})
    r = client.delete(f"/v1/workspaces/{ws['slug']}",
                       headers=_auth(other["access_token"]))
    assert r.status_code == 403


def test_delete_team_as_owner_ok(client):
    owner = _register_user(client, "delown2@x.com", "DOwner2")
    h = _auth(owner["access_token"])
    ws = client.post("/v1/workspaces", headers=h,
                     json={"name": "Doomed", "type": "team"}).json()
    r = client.delete(f"/v1/workspaces/{ws['slug']}", headers=h)
    assert r.status_code == 200
    # Subsequent GET 404
    r2 = client.get(f"/v1/workspaces/{ws['slug']}", headers=h)
    assert r2.status_code == 404


# ---- Members ----

def test_list_members_enriched(client):
    reg = _register_user(client, "memlister@x.com", "MemList")
    h = _auth(reg["access_token"])
    ws = client.post("/v1/workspaces", headers=h,
                     json={"name": "Members", "type": "team"}).json()
    r = client.get(f"/v1/workspaces/{ws['slug']}/members", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "members" in data
    assert len(data["members"]) == 1
    m = data["members"][0]
    assert m["role"] == "owner"
    assert m["email"] == "memlister@x.com"
    assert "password_hash" not in m


def test_remove_owner_forbidden_400(client):
    reg = _register_user(client, "rmown@x.com", "RmOwn")
    h = _auth(reg["access_token"])
    ws = client.post("/v1/workspaces", headers=h,
                     json={"name": "RmOwn", "type": "team"}).json()
    r = client.delete(
        f"/v1/workspaces/{ws['slug']}/members/{reg['user']['user_id']}",
        headers=h)
    assert r.status_code == 400


def test_remove_other_member_as_admin(client):
    owner = _register_user(client, "memowner@x.com", "MO")
    member = _register_user(client, "tobermd@x.com", "Removed")
    ws = client.post("/v1/workspaces",
                      headers=_auth(owner["access_token"]),
                      json={"name": "RemoveMe", "type": "team"}).json()
    inv = client.post(f"/v1/workspaces/{ws['slug']}/invites",
                       headers=_auth(owner["access_token"]),
                       json={"invited_email": "tobermd@x.com",
                             "role": "member"}).json()
    client.post("/v1/invites/accept",
                 headers=_auth(member["access_token"]),
                 json={"token": inv["token"]})
    r = client.delete(
        f"/v1/workspaces/{ws['slug']}/members/{member['user']['user_id']}",
        headers=_auth(owner["access_token"]))
    assert r.status_code == 200


# ---- Invites ----

def test_create_invite_returns_token(client):
    reg = _register_user(client, "invitr@x.com", "Inv")
    h = _auth(reg["access_token"])
    ws = client.post("/v1/workspaces", headers=h,
                     json={"name": "Inv", "type": "team"}).json()
    r = client.post(f"/v1/workspaces/{ws['slug']}/invites", headers=h,
                     json={"invited_email": "guest@x.com", "role": "member"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["token"]
    assert data["invited_email"] == "guest@x.com"
    assert data["role"] == "member"


def test_accept_invite_email_match_joins(client):
    owner = _register_user(client, "ownacc@x.com", "OwnAcc")
    guest = _register_user(client, "guest@x.com", "Guest")
    ws = client.post("/v1/workspaces",
                      headers=_auth(owner["access_token"]),
                      json={"name": "Joinit", "type": "team"}).json()
    inv = client.post(f"/v1/workspaces/{ws['slug']}/invites",
                       headers=_auth(owner["access_token"]),
                       json={"invited_email": "guest@x.com",
                             "role": "member"}).json()
    r = client.post("/v1/invites/accept",
                     headers=_auth(guest["access_token"]),
                     json={"token": inv["token"]})
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    # Guest now sees workspace
    listed = client.get("/v1/workspaces",
                         headers=_auth(guest["access_token"])).json()
    slugs = {w["slug"] for w in listed["workspaces"]}
    assert ws["slug"] in slugs


def test_accept_invite_email_mismatch_403(client):
    owner = _register_user(client, "ownmism@x.com", "Own")
    intruder = _register_user(client, "intruder@x.com", "Int")
    ws = client.post("/v1/workspaces",
                      headers=_auth(owner["access_token"]),
                      json={"name": "Mismatch", "type": "team"}).json()
    inv = client.post(f"/v1/workspaces/{ws['slug']}/invites",
                       headers=_auth(owner["access_token"]),
                       json={"invited_email": "different@x.com",
                             "role": "member"}).json()
    r = client.post("/v1/invites/accept",
                     headers=_auth(intruder["access_token"]),
                     json={"token": inv["token"]})
    assert r.status_code == 403


def test_accept_invite_expired_400(client):
    """Test expired invite by reaching into store."""
    owner = _register_user(client, "ownexp@x.com", "OwnExp")
    guest = _register_user(client, "expguest@x.com", "ExpGuest")
    ws = client.post("/v1/workspaces",
                      headers=_auth(owner["access_token"]),
                      json={"name": "Expire", "type": "team"}).json()
    inv = client.post(f"/v1/workspaces/{ws['slug']}/invites",
                       headers=_auth(owner["access_token"]),
                       json={"invited_email": "expguest@x.com",
                             "role": "member"}).json()
    # Force expire via store
    store = client.app.state.workspace_store
    inv_obj = store.get_invite_by_token(inv["token"])
    inv_obj.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    r = client.post("/v1/invites/accept",
                     headers=_auth(guest["access_token"]),
                     json={"token": inv["token"]})
    assert r.status_code == 400


def test_list_invites_for_workspace(client):
    reg = _register_user(client, "invlister@x.com", "InvLister")
    h = _auth(reg["access_token"])
    ws = client.post("/v1/workspaces", headers=h,
                     json={"name": "InvList", "type": "team"}).json()
    client.post(f"/v1/workspaces/{ws['slug']}/invites", headers=h,
                 json={"invited_email": "a@x.com", "role": "member"})
    client.post(f"/v1/workspaces/{ws['slug']}/invites", headers=h,
                 json={"invited_email": "b@x.com", "role": "admin"})
    r = client.get(f"/v1/workspaces/{ws['slug']}/invites", headers=h)
    assert r.status_code == 200
    invs = r.json()["invites"]
    assert len(invs) == 2
    emails = {i["invited_email"] for i in invs}
    assert emails == {"a@x.com", "b@x.com"}
