# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P1: auth routes integration tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from wanxiang.api import create_app
    app = create_app()
    return TestClient(app)


def _register(client, **overrides):
    body = {
        "email": "alice@example.com",
        "password": "Hello123!",
        "display_name": "Alice",
        "locale": "zh",
    }
    body.update(overrides)
    return client.post("/v1/auth/register", json=body)


def test_register_email_only(client):
    r = _register(client, email="email_only@x.com")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data and "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["user"]["email"] == "email_only@x.com"
    assert "password_hash" not in data["user"]
    assert data["default_workspace"]["type"] == "personal"
    assert data["default_workspace"]["slug"]


def test_register_phone_only(client):
    r = client.post("/v1/auth/register", json={
        "phone": "13800138000", "password": "Hello123!",
        "display_name": "Phone User", "locale": "zh",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"]["phone"] == "13800138000"
    assert data["user"]["email"] is None


def test_register_neither_400(client):
    r = client.post("/v1/auth/register", json={
        "password": "Hello123!", "display_name": "N", "locale": "zh",
    })
    assert r.status_code == 400
    # zh locale default
    assert "邮箱" in r.json()["detail"] or "手机" in r.json()["detail"]


def test_register_neither_en(client):
    r = client.post("/v1/auth/register",
                     json={"password": "Hello123!", "display_name": "N"},
                     headers={"Accept-Language": "en"})
    assert r.status_code == 400
    assert "Email" in r.json()["detail"] or "phone" in r.json()["detail"]


def test_register_weak_password_400(client):
    r = _register(client, email="weak@x.com", password="weakpass")
    assert r.status_code == 400


def test_register_duplicate_email_409(client):
    _register(client, email="dup@x.com")
    r = _register(client, email="dup@x.com")
    assert r.status_code == 409


def test_login_correct_password(client):
    _register(client, email="login@x.com")
    r = client.post("/v1/auth/login", json={
        "identifier": "login@x.com", "password": "Hello123!",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert isinstance(data["workspaces"], list)
    assert len(data["workspaces"]) >= 1


def test_login_wrong_password_401(client):
    _register(client, email="wrong@x.com")
    r = client.post("/v1/auth/login", json={
        "identifier": "wrong@x.com", "password": "WrongPass1",
    })
    assert r.status_code == 401


def test_login_en_locale_returns_english_error(client):
    r = client.post("/v1/auth/login",
                     json={"identifier": "nobody@x.com", "password": "Hello123!"},
                     headers={"Accept-Language": "en"})
    assert r.status_code == 401
    assert "Invalid" in r.json()["detail"] or "invalid" in r.json()["detail"]


def test_refresh_valid_returns_new_access(client):
    reg = _register(client, email="refresh@x.com").json()
    refresh = reg["refresh_token"]
    r = client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_refresh_with_access_token_401(client):
    reg = _register(client, email="badrefresh@x.com").json()
    access = reg["access_token"]
    r = client.post("/v1/auth/refresh", json={"refresh_token": access})
    assert r.status_code == 401


def test_me_without_token_401(client):
    r = client.get("/v1/me")
    assert r.status_code == 401


def test_me_with_valid_token(client):
    reg = _register(client, email="me@x.com").json()
    access = reg["access_token"]
    r = client.get("/v1/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["email"] == "me@x.com"
    assert isinstance(data["workspaces"], list) and len(data["workspaces"]) >= 1


def test_brand_endpoint(client):
    r = client.get("/v1/brand")
    assert r.status_code == 200
    data = r.json()
    assert "name" in data and "zh" in data["name"] and "en" in data["name"]
    assert "short" in data
    assert "avatar" in data and "zh" in data["avatar"] and "en" in data["avatar"]
    assert "tagline" in data and "zh" in data["tagline"]


def test_brand_endpoint_env_override(monkeypatch):
    monkeypatch.setenv("WANXIANG_BRAND_NAME_ZH", "测试品牌覆盖")
    # Need fresh app to pick up env
    from wanxiang.api import create_app
    app = create_app()
    c = TestClient(app)
    r = c.get("/v1/brand")
    assert r.status_code == 200
    assert r.json()["name"]["zh"] == "测试品牌覆盖"


def test_logout_returns_ok(client):
    r = client.post("/v1/auth/logout")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_existing_x_api_key_path_still_works(client):
    """Critical: regression guard for X-API-Key flow."""
    r = client.get("/v1/audit/events", headers={"X-API-Key": "demo-key"})
    # Either 200 (route exists & returns data) or some 4xx but NOT 401 unauthorized
    # We accept any non-auth-failure; the key shouldn't be rejected.
    assert r.status_code != 401, f"X-API-Key flow regressed: {r.text}"
