# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""测试 FastAPI 的静态资源挂载.

P9b 起 `/` 重新由 React SPA 接管 (LandingPage 复刻 chat.html 视觉,
匿名用户可见 demo, 输入即弹注册).
旧的 chat.html 仍可在 `/prototype/chat.html` 访问 (backward compat reference).
所有 SPA 路由 (/login, /register, /dashboard, /w/:slug/*, /admin/*) 都在根路径.
"""
import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app


_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
_FRONTEND_BUILT = (
    os.path.isdir(os.path.join(_REPO_ROOT, "frontend_dist")) or
    os.path.isdir(os.path.join(_REPO_ROOT, "frontend", "dist"))
)


@pytest.mark.skipif(not _FRONTEND_BUILT,
                    reason="frontend 未构建 (npm run build) — SPA 路由跳过")
def test_root_serves_react_spa_index_html():
    """P9b: GET / 应返回 React SPA 的 index.html (LandingPage 在客户端渲染)."""
    client = TestClient(create_app())
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text
    # React SPA 关键元素 — base='/' 后 hashed asset path 是 /assets/...
    assert '<div id="root">' in body
    assert "/assets/index-" in body


@pytest.mark.skipif(not _FRONTEND_BUILT,
                    reason="frontend 未构建 — assets 不存在")
def test_spa_catch_all_returns_index_for_unknown_route():
    """SPA 内部任意未知路径都应返回 index.html — React Router 处理客户端路由."""
    client = TestClient(create_app())
    for path in ("/login", "/register", "/dashboard",
                 "/workspaces", "/w/demo", "/admin/users"):
        res = client.get(path)
        assert res.status_code == 200, f"{path} should serve SPA"
        assert "text/html" in res.headers["content-type"]
        assert '<div id="root">' in res.text


def test_spa_catch_all_does_not_intercept_v1_routes():
    """SPA catch-all 不应吞掉 /v1/* — 未知 /v1/foo 应是 404 (而不是 HTML)."""
    client = TestClient(create_app())
    res = client.get("/v1/this-route-does-not-exist")
    assert res.status_code == 404
    # 显式确认不是 HTML
    assert "text/html" not in res.headers.get("content-type", "")


@pytest.mark.skipif(not _FRONTEND_BUILT,
                    reason="frontend 未构建 — assets 不存在")
def test_spa_assets_served_at_root():
    """vite base='/' → bundled assets 在 /assets/* 下被 StaticFiles 提供."""
    client = TestClient(create_app())
    # index.html references /assets/index-*.js — fetch it via HEAD probe
    res = client.get("/")
    body = res.text
    # Pull the first /assets/... path reference and verify it serves
    import re
    m = re.search(r'/assets/[A-Za-z0-9._-]+\.js', body)
    assert m, "index.html should reference /assets/*.js"
    asset_res = client.get(m.group(0))
    assert asset_res.status_code == 200, f"asset {m.group(0)} should serve"


def test_prototype_index_still_served():
    """旧 /prototype/index.html 仍可访问 (backward compat)."""
    client = TestClient(create_app())
    res = client.get("/prototype/index.html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_prototype_chat_html_still_served():
    """旧 /prototype/chat.html 仍可访问 — backward compat reference."""
    client = TestClient(create_app())
    res = client.get("/prototype/chat.html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text
    # chat.html 内嵌 /v1/simulate fetch
    assert "/v1/simulate" in body
    assert "fetch(" in body or "fetch (" in body
    # P9b: gate redirects 已改回根路径 (无 /app 前缀)
    assert "/app/login" not in body
    assert "/app/register" not in body


def test_healthz_still_returns_json():
    """/healthz 不应被 SPA catch-all 拦截."""
    client = TestClient(create_app())
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/json")
    assert res.json().get("status") == "ok"
