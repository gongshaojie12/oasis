# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""make_usage_store DSN dispatch (mirrors make_task_store)."""
import os

from wanxiang.api.usage import InMemoryUsageStore, make_usage_store
from wanxiang.api.usage_store_sqlite import SqliteUsageStore


def test_none_returns_in_memory():
    assert isinstance(make_usage_store(None), InMemoryUsageStore)


def test_plain_path_returns_sqlite(tmp_path):
    p = str(tmp_path / "u.db")
    assert isinstance(make_usage_store(p), SqliteUsageStore)


def test_sqlite_dsn_returns_sqlite(tmp_path):
    dsn = f"sqlite:///{(tmp_path / 'u.db').as_posix()}"
    assert isinstance(make_usage_store(dsn), SqliteUsageStore)


def test_postgres_dsn_returns_pg_store():
    from wanxiang.api.usage_store_pg import PgUsageStore
    s = make_usage_store("postgresql://x:y@h:1/d", eager_init=False)
    assert isinstance(s, PgUsageStore)
