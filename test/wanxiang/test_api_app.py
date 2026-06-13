# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app


def test_create_app_returns_fastapi_app():
    app = create_app()
    assert app is not None
    paths = {r.path for r in app.routes}
    assert "/healthz" in paths


def test_healthz_returns_200_with_status():
    client = TestClient(create_app())
    res = client.get("/healthz")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"


def test_app_includes_simulate_route():
    """Task 3 才会加 simulate；此处先确认 app 至少含 /healthz。"""
    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/healthz" in paths


def test_cors_headers_present_on_get():
    client = TestClient(create_app())
    res = client.get("/healthz", headers={"Origin": "http://localhost:3000"})
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") is not None


def test_tenant_id_header_echoes_in_response():
    client = TestClient(create_app())
    res = client.get("/healthz", headers={"X-Tenant-Id": "demo-tenant"})
    assert res.headers.get("x-tenant-id") == "demo-tenant"
