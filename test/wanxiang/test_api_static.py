# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""测试 FastAPI 的静态资源挂载.

P9 起 `/` 重新由 chat.html 接管 (营销 demo 着陆页),
React SPA 移到 `/app/*` 下 (登录后实际产品入口).
旧的 `/prototype/*` 路径仍保留 (backward compat).
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


def test_root_serves_chat_html_landing():
    """P9: GET / 应返回 chat.html 营销着陆页 (含 万象 品牌 + /v1/simulate 调用)."""
    client = TestClient(create_app())
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text
    # chat.html 标志: 万象 品牌, 内嵌 /v1/simulate fetch, composer textarea
    assert "万象" in body or "WANXIANG" in body
    assert "/v1/simulate" in body
    # chat.html 专属 DOM (区别于 React SPA — React 是 <div id="root">)
    assert "comp-send" in body or "composer" in body


@pytest.mark.skipif(not _FRONTEND_BUILT,
                    reason="frontend 未构建 (npm run build) — SPA 路由跳过")
def test_app_root_serves_react_spa_index_html():
    """GET /app 应返回 React SPA 的 index.html (含 #root 容器 + bundle 脚本)."""
    client = TestClient(create_app())
    res = client.get("/app")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text
    # React SPA 关键元素
    assert '<div id="root">' in body
    # vite base='/app/' 后 hashed asset path 应是 /app/assets/...
    assert "/app/assets/index-" in body


@pytest.mark.skipif(not _FRONTEND_BUILT,
                    reason="frontend 未构建 — assets 不存在")
def test_app_spa_catch_all_returns_index_for_unknown_route():
    """SPA 内部任意未知路径都应返回 index.html — React Router 处理客户端路由."""
    client = TestClient(create_app())
    for path in ("/app/login", "/app/register", "/app/dashboard",
                 "/app/workspaces/demo"):
        res = client.get(path)
        assert res.status_code == 200, f"{path} should serve SPA"
        assert "text/html" in res.headers["content-type"]
        assert '<div id="root">' in res.text


def test_spa_catch_all_does_not_intercept_v1_routes():
    """SPA catch-all (/app/*) 不应吞掉 /v1/* — 未知 /v1/foo 应是 404 (而不是 HTML)."""
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
    """旧 /prototype/chat.html 仍可访问 — backward compat 即使 `/` 已经服务它."""
    client = TestClient(create_app())
    res = client.get("/prototype/chat.html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text
    # chat.html 内嵌 /v1/simulate fetch
    assert "/v1/simulate" in body
    assert "fetch(" in body or "fetch (" in body


def test_chat_html_landing_has_auth_gate():
    """P9: `/` chat.html 应注入 auth gate (wxRequireAuth, /app/login redirect)."""
    client = TestClient(create_app())
    res = client.get("/")
    assert res.status_code == 200
    body = res.text
    # auth gate 关键符号
    assert "wxRequireAuth" in body
    assert "wanxiang.access_token" in body
    assert "/app/login" in body
    assert "/app/register" in body


def test_healthz_still_returns_json():
    """/healthz 不应被 SPA catch-all 拦截."""
    client = TestClient(create_app())
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/json")
    assert res.json().get("status") == "ok"
