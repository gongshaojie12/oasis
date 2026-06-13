# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""测试 FastAPI 是否正确挂载了 chat.html / prototype 静态资源。"""
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app


def test_root_serves_chat_html():
    client = TestClient(create_app())
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    body = res.text
    # 关键内容存在
    assert "万象" in body
    assert "WANXIANG" in body
    # 新增的"试跑真实模拟"按钮
    assert "run-real-sim" in body  # 我们将给按钮 id="run-real-sim"


def test_prototype_index_also_served():
    client = TestClient(create_app())
    res = client.get("/prototype/index.html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_root_chat_includes_simulate_fetch_call():
    """chat.html 的内联 JS 应包含调 /v1/simulate 的代码。"""
    client = TestClient(create_app())
    body = client.get("/").text
    assert "/v1/simulate" in body
    assert "fetch(" in body or "fetch (" in body
