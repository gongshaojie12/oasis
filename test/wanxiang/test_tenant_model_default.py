# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""spec D3: 租户级默认模型配置."""
import json
import os
import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory
from wanxiang.api.tenancy import TenantInfo, TenantStore

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "wanxiang", "datasources", "distributions",
                    "cn_z_generation_v1.yaml")


def _stub_factory(cfg):
    """Records what cfg the factory got."""
    _stub_factory.last_cfg = cfg
    async def call(m): return '{"score": 5}'
    return call


def _body_no_model():
    return {
        "distribution_path": DIST, "n": 3, "seed": 1,
        "scenario": {"material":"x","question":"?","kind":"rate"},
        "rounds": 0,
        # model intentionally omitted
    }


def test_tenant_info_has_default_model_field():
    """Optional default_model_config field exists."""
    t = TenantInfo(tenant_id="x", api_key="k", rpm_limit=60,
                    default_model_config={"provider":"deepseek",
                                          "api_key":"sk-x"})
    assert t.default_model_config["provider"] == "deepseek"


def test_tenant_info_default_is_none():
    t = TenantInfo(tenant_id="x", api_key="k", rpm_limit=60)
    assert t.default_model_config is None


def test_request_without_model_works_with_tenant_default(monkeypatch):
    monkeypatch.setenv("WANXIANG_TENANTS_JSON", json.dumps([{
        "tenant_id":"a","api_key":"sk-a","rpm_limit":60,
        "default_model_config":{"provider":"stub"},
    }]))
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app); c.headers.update({"X-API-Key":"sk-a"})
    r = c.post("/v1/simulate", json=_body_no_model())
    assert r.status_code == 200


def test_request_model_wins_over_tenant_default(monkeypatch):
    monkeypatch.setenv("WANXIANG_TENANTS_JSON", json.dumps([{
        "tenant_id":"a","api_key":"sk-a","rpm_limit":60,
        "default_model_config":{"provider":"deepseek","api_key":"sk-ds"},
    }]))
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app); c.headers.update({"X-API-Key":"sk-a"})
    body = _body_no_model()
    body["model"] = {"provider":"stub"}
    r = c.post("/v1/simulate", json=body)
    assert r.status_code == 200
    # The factory should have been called with provider=stub (request wins)
    assert _stub_factory.last_cfg.provider == "stub"


def test_request_without_model_and_no_tenant_default_uses_stub(monkeypatch):
    """Fallback to stub default when neither set."""
    monkeypatch.setenv("WANXIANG_TENANTS_JSON", json.dumps([{
        "tenant_id":"a","api_key":"sk-a","rpm_limit":60,
    }]))
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app); c.headers.update({"X-API-Key":"sk-a"})
    r = c.post("/v1/simulate", json=_body_no_model())
    assert r.status_code == 200
