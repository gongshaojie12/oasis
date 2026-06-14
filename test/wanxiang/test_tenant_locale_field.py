# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""TenantInfo.default_locale field + JSON env loading."""
import json
import os

import pytest

from wanxiang.api.tenancy import TenantInfo, TenantStore


def test_tenant_info_default_locale_is_zh():
    t = TenantInfo(tenant_id="x", api_key="k", rpm_limit=60)
    assert t.default_locale == "zh"


def test_tenant_info_accepts_en_locale():
    t = TenantInfo(tenant_id="x", api_key="k", rpm_limit=60,
                    default_locale="en")
    assert t.default_locale == "en"


def test_tenant_store_loads_default_locale_from_env(monkeypatch):
    monkeypatch.setenv("WANXIANG_TENANTS_JSON", json.dumps([
        {"tenant_id":"a","api_key":"sk-a","rpm_limit":60,
         "default_locale":"en"},
    ]))
    store = TenantStore.from_env()
    t = store.lookup("sk-a")
    assert t.default_locale == "en"


def test_tenant_store_omitted_locale_defaults_to_zh(monkeypatch):
    monkeypatch.setenv("WANXIANG_TENANTS_JSON", json.dumps([
        {"tenant_id":"a","api_key":"sk-a","rpm_limit":60},
    ]))
    store = TenantStore.from_env()
    assert store.lookup("sk-a").default_locale == "zh"
