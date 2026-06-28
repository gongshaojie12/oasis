# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""预测任务分组(SandboxGroup):CRUD + 移动任务 + 删组解绑 + 跨工作区隔离。"""
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


def _mk_sandbox(client, h, slug, name):
    r = client.post(f"/v1/workspaces/{slug}/sandboxes", headers=h,
                     json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()


def test_group_crud(client):
    reg = _register(client, "grp1@x.com")
    h = _auth(reg["access_token"])
    ws = _make_team(client, h, "G1")
    slug = ws["slug"]

    # 建分组
    r = client.post(f"/v1/workspaces/{slug}/sandboxes/groups", headers=h,
                     json={"name": "饮料类"})
    assert r.status_code == 200, r.text
    g = r.json()
    assert g["name"] == "饮料类"
    assert g["workspace_id"] == ws["workspace_id"]

    # 列分组
    r = client.get(f"/v1/workspaces/{slug}/sandboxes/groups", headers=h)
    assert r.status_code == 200
    assert [x["name"] for x in r.json()["groups"]] == ["饮料类"]

    # 改名
    r = client.patch(
        f"/v1/workspaces/{slug}/sandboxes/groups/{g['group_id']}",
        headers=h, json={"name": "快消品"})
    assert r.status_code == 200
    assert r.json()["name"] == "快消品"

    # 删除
    r = client.delete(
        f"/v1/workspaces/{slug}/sandboxes/groups/{g['group_id']}", headers=h)
    assert r.status_code == 200
    r = client.get(f"/v1/workspaces/{slug}/sandboxes/groups", headers=h)
    assert r.json()["groups"] == []


def test_move_sandbox_into_and_out_of_group(client):
    reg = _register(client, "grp2@x.com")
    h = _auth(reg["access_token"])
    ws = _make_team(client, h, "G2")
    slug = ws["slug"]
    sb = _mk_sandbox(client, h, slug, "任务A")
    assert sb["group_id"] is None
    g = client.post(f"/v1/workspaces/{slug}/sandboxes/groups", headers=h,
                     json={"name": "分组X"}).json()

    # 移动到分组
    r = client.patch(
        f"/v1/workspaces/{slug}/sandboxes/{sb['sandbox_id']}",
        headers=h, json={"group_id": g["group_id"]})
    assert r.status_code == 200, r.text
    assert r.json()["group_id"] == g["group_id"]

    # 移出分组(显式 null)
    r = client.patch(
        f"/v1/workspaces/{slug}/sandboxes/{sb['sandbox_id']}",
        headers=h, json={"group_id": None})
    assert r.status_code == 200
    assert r.json()["group_id"] is None


def test_delete_group_unbinds_sandbox_not_deletes_it(client):
    reg = _register(client, "grp3@x.com")
    h = _auth(reg["access_token"])
    ws = _make_team(client, h, "G3")
    slug = ws["slug"]
    sb = _mk_sandbox(client, h, slug, "任务B")
    g = client.post(f"/v1/workspaces/{slug}/sandboxes/groups", headers=h,
                     json={"name": "临时组"}).json()
    client.patch(f"/v1/workspaces/{slug}/sandboxes/{sb['sandbox_id']}",
                 headers=h, json={"group_id": g["group_id"]})

    # 删分组
    client.delete(
        f"/v1/workspaces/{slug}/sandboxes/groups/{g['group_id']}", headers=h)

    # 任务仍在,且 group_id 变 null(没被删)
    r = client.get(
        f"/v1/workspaces/{slug}/sandboxes/{sb['sandbox_id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["group_id"] is None


def test_move_to_nonexistent_group_404(client):
    reg = _register(client, "grp4@x.com")
    h = _auth(reg["access_token"])
    ws = _make_team(client, h, "G4")
    slug = ws["slug"]
    sb = _mk_sandbox(client, h, slug, "任务C")
    r = client.patch(
        f"/v1/workspaces/{slug}/sandboxes/{sb['sandbox_id']}",
        headers=h, json={"group_id": "no-such-group"})
    assert r.status_code == 404


def test_group_cross_workspace_isolation(client):
    reg = _register(client, "grp5@x.com")
    h = _auth(reg["access_token"])
    ws_a = _make_team(client, h, "GA")
    ws_b = _make_team(client, h, "GB")
    g = client.post(f"/v1/workspaces/{ws_a['slug']}/sandboxes/groups",
                     headers=h, json={"name": "A组"}).json()
    # ws_b 里看不到 ws_a 的分组
    r = client.get(f"/v1/workspaces/{ws_b['slug']}/sandboxes/groups",
                    headers=h)
    assert r.json()["groups"] == []
    # 不能从 ws_b 改 ws_a 的分组
    r = client.patch(
        f"/v1/workspaces/{ws_b['slug']}/sandboxes/groups/{g['group_id']}",
        headers=h, json={"name": "黑客"})
    assert r.status_code == 404
