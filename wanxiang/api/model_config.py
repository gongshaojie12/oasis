# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""每工作区一份大模型配置(provider + key + base_url + model_name)。

DSN 分发同 api_keys.py:None→InMemory;sqlite/路径→SQLite;postgresql→PG。
key 以明文存储(MVP,与 api_keys 一致),对外响应由路由层脱敏。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from urllib.parse import urlparse


@dataclass
class ModelConfigRecord:
    workspace_id: str
    provider: str
    api_key: str | None
    base_url: str | None
    model_name: str | None
    updated_at: datetime
    updated_by_user_id: str | None


class InMemoryModelConfigStore:
    def __init__(self):
        self._by_ws: dict[str, ModelConfigRecord] = {}
        self._lock = Lock()

    def get(self, workspace_id: str) -> ModelConfigRecord | None:
        return self._by_ws.get(workspace_id)

    def upsert(self, rec: ModelConfigRecord) -> ModelConfigRecord:
        with self._lock:
            self._by_ws[rec.workspace_id] = rec
        return rec


def make_model_config_store(dsn: str | None, *, eager_init: bool = True):
    if not dsn:
        return InMemoryModelConfigStore()
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()
    if len(scheme) == 1 and scheme.isalpha():
        scheme = ""
    if scheme in ("postgresql", "postgres"):
        from wanxiang.api.model_config_store_pg import PgModelConfigStore
        return PgModelConfigStore(dsn, eager_init=eager_init)
    if scheme == "sqlite":
        path = parsed.path or dsn[len("sqlite:"):]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        from wanxiang.api.model_config_store_sqlite import (
            SqliteModelConfigStore)
        return SqliteModelConfigStore(path)
    if not scheme:
        from wanxiang.api.model_config_store_sqlite import (
            SqliteModelConfigStore)
        return SqliteModelConfigStore(dsn)
    raise ValueError(f"unsupported model_config store DSN scheme: {scheme!r}")


__all__ = ["ModelConfigRecord", "InMemoryModelConfigStore",
           "make_model_config_store"]
