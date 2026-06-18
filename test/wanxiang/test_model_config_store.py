from datetime import datetime, timezone
from wanxiang.api.model_config import (ModelConfigRecord,
                                        make_model_config_store)


def _rec(ws="ws1", provider="deepseek", key="sk-abc1234",
         base_url=None, model_name=None, by="u1"):
    return ModelConfigRecord(
        workspace_id=ws, provider=provider, api_key=key,
        base_url=base_url, model_name=model_name,
        updated_at=datetime.now(timezone.utc), updated_by_user_id=by)


def test_get_missing_returns_none():
    store = make_model_config_store(None)
    assert store.get("nope") is None


def test_upsert_then_get():
    store = make_model_config_store(None)
    store.upsert(_rec())
    got = store.get("ws1")
    assert got.provider == "deepseek"
    assert got.api_key == "sk-abc1234"
    assert got.updated_by_user_id == "u1"


def test_upsert_overwrites_same_workspace():
    store = make_model_config_store(None)
    store.upsert(_rec(provider="deepseek", key="sk-old0001"))
    store.upsert(_rec(provider="openai", key="sk-new0002",
                      model_name="gpt-4o-mini"))
    got = store.get("ws1")
    assert got.provider == "openai"
    assert got.api_key == "sk-new0002"
    assert got.model_name == "gpt-4o-mini"
