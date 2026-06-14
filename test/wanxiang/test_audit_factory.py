# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""make_audit_store factory (M3-13)."""
from wanxiang.api.audit import InMemoryAuditStore, make_audit_store
from wanxiang.api.audit_store_sqlite import SqliteAuditStore


def test_none_returns_in_memory():
    assert isinstance(make_audit_store(None), InMemoryAuditStore)


def test_plain_path_returns_sqlite(tmp_path):
    assert isinstance(make_audit_store(str(tmp_path / "a.db")),
                      SqliteAuditStore)


def test_sqlite_dsn(tmp_path):
    dsn = f"sqlite:///{(tmp_path / 'a.db').as_posix()}"
    assert isinstance(make_audit_store(dsn), SqliteAuditStore)


def test_postgres_dsn():
    from wanxiang.api.audit_store_pg import PgAuditStore
    s = make_audit_store("postgresql://x:y@h:1/d", eager_init=False)
    assert isinstance(s, PgAuditStore)
