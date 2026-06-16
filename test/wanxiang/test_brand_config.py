# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P1: Brand config in ServerSettings + GET /v1/brand."""
from __future__ import annotations

import importlib

import pytest


def _fresh_settings():
    """Re-import to pick up env overrides."""
    from wanxiang.api import server as srv_mod
    importlib.reload(srv_mod)
    return srv_mod.ServerSettings()


def test_server_settings_default_brand_fields():
    from wanxiang.api.server import ServerSettings
    s = ServerSettings()
    assert s.brand_name_zh == "万象 WANXIANG"
    assert s.brand_name_en == "WANXIANG"
    assert s.brand_short == "WANXIANG"
    assert s.brand_avatar_zh == "象"
    assert s.brand_avatar_en == "W"
    assert s.brand_tagline_zh
    assert s.brand_tagline_en


def test_server_settings_jwt_defaults():
    from wanxiang.api.server import ServerSettings
    s = ServerSettings()
    assert s.jwt_alg == "HS256"
    assert s.jwt_access_ttl_minutes == 15
    assert s.jwt_refresh_ttl_days == 7
    assert isinstance(s.jwt_secret, str) and len(s.jwt_secret) >= 16


def test_brand_name_zh_env_override(monkeypatch):
    monkeypatch.setenv("WANXIANG_BRAND_NAME_ZH", "测试品牌")
    s = _fresh_settings()
    assert s.brand_name_zh == "测试品牌"


def test_brand_avatar_en_env_override(monkeypatch):
    monkeypatch.setenv("WANXIANG_BRAND_AVATAR_EN", "X")
    s = _fresh_settings()
    assert s.brand_avatar_en == "X"
