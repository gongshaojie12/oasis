# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""文档上传端点:解析+提炼成 material;鉴权/超大/格式错误。"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory


def _factory_returns(text: str):
    def factory(cfg):
        async def call(messages):
            return text
        return call
    return factory


def _client(distill_text="提炼素材:气泡水新品"):
    app = create_app()
    app.dependency_overrides[get_model_factory] = (
        lambda: _factory_returns(distill_text))
    return TestClient(app)


def _register(client, email):
    r = client.post("/v1/auth/register", json={
        "email": email, "password": "Hello123!",
        "display_name": "U", "locale": "zh"})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


def _setup(client, email):
    reg = _register(client, email)
    h = _auth(reg["access_token"])
    ws = client.post("/v1/workspaces", headers=h,
                     json={"name": "T", "type": "team"}).json()
    sb = client.post(f"/v1/workspaces/{ws['slug']}/sandboxes", headers=h,
                     json={"name": "Box"}).json()
    return h, ws, sb


def test_upload_txt_returns_material():
    client = _client()
    h, ws, sb = _setup(client, "doc1@x.com")
    files = {"file": ("product.txt", io.BytesIO("气泡水产品资料".encode("utf-8")),
                      "text/plain")}
    r = client.post(
        f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}/documents",
        headers=h, files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "text"
    assert "气泡水" in body["material"]
    assert body["filename"] == "product.txt"


def test_upload_unsupported_format_400():
    client = _client()
    h, ws, sb = _setup(client, "doc2@x.com")
    files = {"file": ("x.zip", io.BytesIO(b"PK\x03\x04"), "application/zip")}
    r = client.post(
        f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}/documents",
        headers=h, files=files)
    assert r.status_code == 400


def test_upload_empty_400():
    client = _client()
    h, ws, sb = _setup(client, "doc3@x.com")
    files = {"file": ("a.txt", io.BytesIO(b""), "text/plain")}
    r = client.post(
        f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}/documents",
        headers=h, files=files)
    assert r.status_code == 400


def test_upload_requires_auth_401():
    client = _client()
    files = {"file": ("a.txt", io.BytesIO(b"hi"), "text/plain")}
    r = client.post(
        "/v1/workspaces/none/sandboxes/none/documents", files=files)
    assert r.status_code == 401


def test_document_context_flows_into_chat():
    """document_context 应拼进意图解析(走 chat 流程)。"""
    intent = (
        '{"intent":"simulate","fields":{"material":"气泡水新品",'
        '"question":"购买意愿","kind":"rate","options":null,"n":20,'
        '"rounds":0},"missing":[],"explanation":"ok","confidence":0.9}'
    )
    app = create_app()

    def factory(cfg):
        async def call(messages):
            sys = next((m["content"] for m in messages
                        if m.get("role") == "system"), "")
            if "首席模拟官" in sys or "Simulation Officer" in sys:
                # 断言资料确实进入了意图解析的用户文本
                user = next((m["content"] for m in messages
                             if m.get("role") == "user"), "")
                assert "附带资料" in user
                return intent
            return '{"score": 7}'
        return call
    app.dependency_overrides[get_model_factory] = lambda: factory
    client = TestClient(app)
    h, ws, sb = _setup(client, "doc4@x.com")
    r = client.post(
        f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}/chat",
        headers=h,
        json={"text": "测一下", "document_context": "气泡水,定价6元,主打0糖"})
    assert r.status_code == 200, r.text
