# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""make_task_store(dsn) DSN dispatch."""
import os
import pytest

from wanxiang.api.tasks import TaskStore, make_task_store
from wanxiang.api.task_store_sqlite import SqliteTaskStore


def test_none_returns_in_memory():
    s = make_task_store(None)
    assert isinstance(s, TaskStore)


def test_empty_string_returns_in_memory():
    s = make_task_store("")
    assert isinstance(s, TaskStore)


def test_plain_path_returns_sqlite_backwards_compat(tmp_path):
    p = str(tmp_path / "x.db")
    s = make_task_store(p)
    assert isinstance(s, SqliteTaskStore)
    # 真能写入
    assert os.path.exists(p)


def test_sqlite_scheme_with_three_slashes_absolute(tmp_path):
    p = (tmp_path / "y.db").as_posix()
    dsn = f"sqlite:///{p}"
    s = make_task_store(dsn)
    assert isinstance(s, SqliteTaskStore)


def test_sqlite_scheme_relative(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = make_task_store("sqlite:relative.db")
    assert isinstance(s, SqliteTaskStore)
    assert os.path.exists("relative.db")


def test_postgresql_scheme_returns_pg_store():
    """Without a real PG, we only assert the factory dispatches to the right class
    without actually connecting. PgTaskStore.__init__ should lazily connect."""
    from wanxiang.api.task_store_pg import PgTaskStore
    # Use a clearly-fake DSN; PgTaskStore must NOT eagerly connect at construction
    s = make_task_store("postgresql://nobody:nopass@127.0.0.1:1/nodb",
                        eager_init=False)
    assert isinstance(s, PgTaskStore)


def test_postgres_alias_scheme():
    from wanxiang.api.task_store_pg import PgTaskStore
    s = make_task_store("postgres://x:y@h:1/d", eager_init=False)
    assert isinstance(s, PgTaskStore)


def test_unknown_scheme_raises():
    with pytest.raises(ValueError, match="unsupported"):
        make_task_store("mongodb://x/y")


def test_factory_eager_init_default_true_initializes_schema(tmp_path):
    """默认 eager_init=True：sqlite 应建好 schema。"""
    p = str(tmp_path / "z.db")
    make_task_store(p)
    # 复用同一文件再开一个 store 能直接 get 不报"无表"
    import sqlite3
    conn = sqlite3.connect(p)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    conn.close()
    assert any("simulation_tasks" in r[0] for r in rows)
