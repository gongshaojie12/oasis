# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""测试 FastAPI 的静态资源挂载.

P8 起 `/` 由 React SPA 接管 (frontend_dist/index.html 或 frontend/dist/index.html
fallback). 旧的 chat.html 原型仍然通过 /prototype/* 访问 (backward compat).
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
    """GET / 应返回 React SPA 的 index.html (含 #root 容器 + bundle 脚本)."""
    client = TestClient(create_app())
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text
    # React SPA 关键元素
    assert '<div id="root">' in body
    # 应引用 hashed 资源
    assert "/assets/index-" in body
    # 品牌字仍在 head 里
    assert "万象" in body or "WANXIANG" in body


@pytest.mark.skipif(not _FRONTEND_BUILT,
                    reason="frontend 未构建 — assets 不存在")
def test_spa_catch_all_returns_index_for_unknown_route():
    """任意未知路径 (如 /login, /dashboard) 都应返回 index.html — React Router 处理客户端路由."""
    client = TestClient(create_app())
    for path in ("/login", "/dashboard", "/workspaces/demo"):
        res = client.get(path)
        assert res.status_code == 200, f"{path} should serve SPA"
        assert "text/html" in res.headers["content-type"]
        assert '<div id="root">' in res.text


def test_spa_catch_all_does_not_intercept_v1_routes():
    """SPA catch-all 不应吞掉 /v1/* — 未知 /v1/foo 应是 404 (而不是返回 HTML)."""
    client = TestClient(create_app())
    res = client.get("/v1/this-route-does-not-exist")
    assert res.status_code == 404
    # 显式确认不是 HTML
    assert "text/html" not in res.headers.get("content-type", "")


def test_prototype_index_still_served():
    """旧 /prototype/index.html 仍可访问 (backward compat)."""
    client = TestClient(create_app())
    res = client.get("/prototype/index.html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_prototype_chat_html_still_served():
    """旧 /prototype/chat.html 仍可访问 — P6 demo 原型 backward compat."""
    client = TestClient(create_app())
    res = client.get("/prototype/chat.html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text
    # chat.html 内嵌 /v1/simulate fetch
    assert "/v1/simulate" in body
    assert "fetch(" in body or "fetch (" in body


def test_healthz_still_returns_json():
    """/healthz 不应被 SPA catch-all 拦截."""
    client = TestClient(create_app())
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/json")
    assert res.json().get("status") == "ok"
