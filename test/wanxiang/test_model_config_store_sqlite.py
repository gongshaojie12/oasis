# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import os
import tempfile
from datetime import datetime, timezone
from wanxiang.api.model_config import ModelConfigRecord
from wanxiang.api.model_config_store_sqlite import SqliteModelConfigStore


def _store():
    d = tempfile.mkdtemp()
    return SqliteModelConfigStore(os.path.join(d, "mc.db"))


def _rec(**kw):
    base = dict(workspace_id="ws1", provider="deepseek",
               api_key="sk-abc1234", base_url=None, model_name=None,
               updated_at=datetime.now(timezone.utc),
               updated_by_user_id="u1")
    base.update(kw)
    return ModelConfigRecord(**base)


def test_get_missing_none():
    assert _store().get("ws1") is None


def test_upsert_get_roundtrip():
    s = _store()
    s.upsert(_rec(base_url="https://x/v1", model_name="deepseek-chat"))
    got = s.get("ws1")
    assert got.provider == "deepseek"
    assert got.base_url == "https://x/v1"
    assert got.model_name == "deepseek-chat"
    assert got.updated_by_user_id == "u1"


def test_upsert_overwrites():
    s = _store()
    s.upsert(_rec(api_key="sk-old0001"))
    s.upsert(_rec(provider="openai", api_key="sk-new0002"))
    got = s.get("ws1")
    assert got.provider == "openai"
    assert got.api_key == "sk-new0002"


def test_persists_across_instances():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "mc.db")
    SqliteModelConfigStore(p).upsert(_rec())
    assert SqliteModelConfigStore(p).get("ws1").api_key == "sk-abc1234"
