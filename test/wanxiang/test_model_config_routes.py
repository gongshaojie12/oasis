# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Tests for model config routes."""
from fastapi.testclient import TestClient
from wanxiang.api.app import create_app


def _client():
    return TestClient(create_app())


def _register(c, email):
    r = c.post("/v1/auth/register", json={
        "email": email, "password": "Test1234!",
        "display_name": email.split("@")[0], "locale": "zh"})
    assert r.status_code == 200, r.text
    d = r.json()
    slug = (d.get("default_workspace") or d["workspaces"][0])["slug"]
    return d["access_token"], slug


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_presets_requires_login():
    c = _client()
    assert c.get("/v1/model-presets").status_code == 401


def test_presets_listed_when_logged_in():
    c = _client()
    tok, _ = _register(c, "p1@example.com")
    r = c.get("/v1/model-presets", headers=_auth(tok))
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["presets"]}
    assert "deepseek" in ids and "custom" in ids


def test_get_config_default_when_unset():
    c = _client()
    tok, slug = _register(c, "p2@example.com")
    r = c.get(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok))
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "stub"
    assert body["has_key"] is False


def test_put_then_get_masks_key():
    c = _client()
    tok, slug = _register(c, "p3@example.com")
    r = c.put(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok),
              json={"provider": "deepseek", "api_key": "sk-abcdef1234"})
    assert r.status_code == 200, r.text
    g = c.get(f"/v1/workspaces/{slug}/model-config",
              headers=_auth(tok)).json()
    assert g["provider"] == "deepseek"
    assert g["has_key"] is True
    assert g["api_key_masked"] == "sk-…1234"
    assert "api_key" not in g  # 完整 key 绝不出现


def test_put_blank_key_keeps_existing():
    c = _client()
    tok, slug = _register(c, "p4@example.com")
    c.put(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok),
          json={"provider": "deepseek", "api_key": "sk-keep0001"})
    # 第二次只改 model_name,不传 key
    r = c.put(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok),
              json={"provider": "deepseek", "model_name": "deepseek-chat"})
    assert r.status_code == 200, r.text
    g = c.get(f"/v1/workspaces/{slug}/model-config",
              headers=_auth(tok)).json()
    assert g["api_key_masked"] == "sk-…0001"  # 旧 key 仍在
    assert g["model_name"] == "deepseek-chat"


def test_put_invalid_provider_400():
    c = _client()
    tok, slug = _register(c, "p5@example.com")
    r = c.put(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok),
              json={"provider": "nope", "api_key": "x"})
    assert r.status_code == 400


def test_put_deepseek_without_key_400_when_none_stored():
    c = _client()
    tok, slug = _register(c, "p6@example.com")
    r = c.put(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok),
              json={"provider": "deepseek"})
    assert r.status_code == 400


def test_put_custom_without_base_url_400():
    c = _client()
    tok, slug = _register(c, "p7@example.com")
    r = c.put(f"/v1/workspaces/{slug}/model-config", headers=_auth(tok),
              json={"provider": "custom", "api_key": "sk-x"})
    assert r.status_code == 400
