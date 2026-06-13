# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Server settings & launcher loadability test (no real uvicorn boot)."""
import os
import sys

import pytest


def test_server_settings_defaults_no_env(monkeypatch):
    # 清掉所有 WANXIANG_ 环境变量，验证默认值
    for k in list(os.environ.keys()):
        if k.startswith("WANXIANG_"):
            monkeypatch.delenv(k, raising=False)
    from wanxiang.api.server import ServerSettings
    s = ServerSettings()
    assert s.host == "0.0.0.0"
    assert s.port == 8000
    assert s.workers == 1
    assert s.log_level == "info"


def test_server_settings_reads_env(monkeypatch):
    monkeypatch.setenv("WANXIANG_HOST", "127.0.0.1")
    monkeypatch.setenv("WANXIANG_PORT", "9090")
    monkeypatch.setenv("WANXIANG_WORKERS", "4")
    monkeypatch.setenv("WANXIANG_LOG_LEVEL", "debug")
    from wanxiang.api.server import ServerSettings
    s = ServerSettings()
    assert s.host == "127.0.0.1"
    assert s.port == 9090
    assert s.workers == 4
    assert s.log_level == "debug"


def test_server_settings_invalid_port_rejected(monkeypatch):
    monkeypatch.setenv("WANXIANG_PORT", "70000")  # out of range
    from wanxiang.api.server import ServerSettings
    with pytest.raises(Exception):
        ServerSettings()


def test_server_module_exposes_main_callable():
    from wanxiang.api import server
    assert callable(server.main)


def test_server_main_with_no_run_flag_does_not_block(monkeypatch):
    """main(['--print-config']) 应只打印配置并立即返回 0，不启动 uvicorn。"""
    from wanxiang.api import server
    rc = server.main(["--print-config"])
    assert rc == 0
