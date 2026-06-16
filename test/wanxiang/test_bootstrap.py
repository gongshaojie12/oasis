# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P3: ensure_demo_workspace_and_key bootstrap."""
from __future__ import annotations

import json

import pytest


def _new_stores():
    from wanxiang.api.users import InMemoryUserStore
    from wanxiang.api.workspaces import InMemoryWorkspaceStore
    from wanxiang.api.api_keys import InMemoryApiKeyStore
    return InMemoryUserStore(), InMemoryWorkspaceStore(), InMemoryApiKeyStore()


def test_ensure_demo_creates_workspace_and_key(monkeypatch):
    monkeypatch.delenv("WANXIANG_TENANTS_JSON", raising=False)
    from wanxiang.api.bootstrap import ensure_demo_workspace_and_key
    us, ws_s, ak_s = _new_stores()
    ws, ak = ensure_demo_workspace_and_key(
        user_store=us, workspace_store=ws_s, api_key_store=ak_s)
    assert ws is not None and ws.slug == "demo"
    assert ak is not None and ak.api_key == "demo-key"
    # Key resolves to workspace
    found = ak_s.lookup("demo-key")
    assert found is not None
    assert found.workspace_id == ws.workspace_id


def test_ensure_demo_idempotent(monkeypatch):
    monkeypatch.delenv("WANXIANG_TENANTS_JSON", raising=False)
    from wanxiang.api.bootstrap import ensure_demo_workspace_and_key
    us, ws_s, ak_s = _new_stores()
    ws1, ak1 = ensure_demo_workspace_and_key(
        user_store=us, workspace_store=ws_s, api_key_store=ak_s)
    ws2, ak2 = ensure_demo_workspace_and_key(
        user_store=us, workspace_store=ws_s, api_key_store=ak_s)
    assert ws1.workspace_id == ws2.workspace_id
    assert ak1.key_id == ak2.key_id


def test_demo_workspace_has_generous_balance(monkeypatch):
    monkeypatch.delenv("WANXIANG_TENANTS_JSON", raising=False)
    from wanxiang.api.bootstrap import ensure_demo_workspace_and_key
    us, ws_s, ak_s = _new_stores()
    ws, _ = ensure_demo_workspace_and_key(
        user_store=us, workspace_store=ws_s, api_key_store=ak_s)
    assert ws.balance_cost_units >= 100_000


def test_demo_user_is_not_super_admin(monkeypatch):
    monkeypatch.delenv("WANXIANG_TENANTS_JSON", raising=False)
    from wanxiang.api.bootstrap import ensure_demo_workspace_and_key
    us, ws_s, ak_s = _new_stores()
    ensure_demo_workspace_and_key(
        user_store=us, workspace_store=ws_s, api_key_store=ak_s)
    demo_user = us.get_by_email("demo@wanxiang.local")
    assert demo_user is not None
    assert demo_user.is_super_admin is False


def test_legacy_tenants_json_migrated(monkeypatch):
    monkeypatch.setenv(
        "WANXIANG_TENANTS_JSON",
        json.dumps([
            {"tenant_id": "acme", "api_key": "acme-key",
             "rpm_limit": 100, "default_locale": "en"}
        ]))
    from wanxiang.api.bootstrap import ensure_demo_workspace_and_key
    us, ws_s, ak_s = _new_stores()
    ensure_demo_workspace_and_key(
        user_store=us, workspace_store=ws_s, api_key_store=ak_s)
    legacy = ak_s.lookup("acme-key")
    assert legacy is not None
    legacy_ws = ws_s.get_workspace(legacy.workspace_id)
    assert legacy_ws is not None and legacy_ws.slug == "acme"


def test_custom_default_api_key_env(monkeypatch):
    monkeypatch.delenv("WANXIANG_TENANTS_JSON", raising=False)
    monkeypatch.setenv("WANXIANG_DEFAULT_API_KEY", "custom-secret")
    monkeypatch.setenv("WANXIANG_DEFAULT_WORKSPACE_SLUG", "custom-ws")
    from wanxiang.api.bootstrap import ensure_demo_workspace_and_key
    us, ws_s, ak_s = _new_stores()
    ws, ak = ensure_demo_workspace_and_key(
        user_store=us, workspace_store=ws_s, api_key_store=ak_s)
    assert ws.slug == "custom-ws"
    assert ak.api_key == "custom-secret"
