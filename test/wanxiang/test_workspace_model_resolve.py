# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from datetime import datetime, timezone
from wanxiang.api.model_config import (ModelConfigRecord,
                                        make_model_config_store)
from wanxiang.api.model_resolve import resolve_workspace_model
from wanxiang.api.schemas import ModelConfig


def _store_with(ws, **kw):
    s = make_model_config_store(None)
    s.upsert(ModelConfigRecord(
        workspace_id=ws, provider=kw.get("provider", "deepseek"),
        api_key=kw.get("api_key", "sk-x"),
        base_url=kw.get("base_url"), model_name=kw.get("model_name"),
        updated_at=datetime.now(timezone.utc), updated_by_user_id="u"))
    return s


def test_request_model_wins():
    s = _store_with("ws1", provider="deepseek", api_key="sk-store")
    req = ModelConfig(provider="stub")
    out = resolve_workspace_model(req, "ws1", s)
    assert out.provider == "stub"


def test_falls_back_to_workspace_config():
    s = _store_with("ws1", provider="deepseek", api_key="sk-store")
    out = resolve_workspace_model(None, "ws1", s)
    assert out.provider == "deepseek"
    assert out.api_key == "sk-store"


def test_falls_back_to_stub_when_unset():
    s = make_model_config_store(None)
    out = resolve_workspace_model(None, "ws-none", s)
    assert out.provider == "stub"
