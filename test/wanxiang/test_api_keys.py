# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P3: ApiKey + InMemoryApiKeyStore + SQLite mirror."""
from __future__ import annotations

import pytest

from wanxiang.api.api_keys import (
    ApiKey,
    InMemoryApiKeyStore,
    make_api_key_store,
)


def _ak(api_key="k1", workspace_id="ws1", name="key1", role="member",
        rpm_limit=60):
    return ApiKey(
        key_id="auto", workspace_id=workspace_id, api_key=api_key,
        name=name, role=role, rpm_limit=rpm_limit,
    )


def test_inmemory_create_and_lookup():
    store = InMemoryApiKeyStore()
    ak = store.create(_ak(api_key="abc", workspace_id="ws-1"))
    assert ak.key_id and ak.key_id != "auto"
    got = store.lookup("abc")
    assert got is not None
    assert got.workspace_id == "ws-1"
    assert got.api_key == "abc"


def test_inmemory_duplicate_key_raises():
    store = InMemoryApiKeyStore()
    store.create(_ak(api_key="dup", workspace_id="ws-1"))
    with pytest.raises(ValueError):
        store.create(_ak(api_key="dup", workspace_id="ws-2"))


def test_list_for_workspace_filters_correctly():
    store = InMemoryApiKeyStore()
    store.create(_ak(api_key="a1", workspace_id="ws-A", name="A1"))
    store.create(_ak(api_key="a2", workspace_id="ws-A", name="A2"))
    store.create(_ak(api_key="b1", workspace_id="ws-B", name="B1"))
    a_keys = store.list_for_workspace("ws-A")
    assert {k.api_key for k in a_keys} == {"a1", "a2"}
    b_keys = store.list_for_workspace("ws-B")
    assert {k.api_key for k in b_keys} == {"b1"}


def test_revoke_marks_revoked_at():
    store = InMemoryApiKeyStore()
    ak = store.create(_ak(api_key="rev"))
    assert store.revoke(ak.key_id) is True
    # Second revoke of same key returns False
    assert store.revoke(ak.key_id) is False


def test_lookup_of_revoked_returns_none():
    store = InMemoryApiKeyStore()
    ak = store.create(_ak(api_key="dead"))
    store.revoke(ak.key_id)
    assert store.lookup("dead") is None
    # Also filtered from list_for_workspace
    assert store.list_for_workspace(ak.workspace_id) == []


def test_sqlite_persistence_roundtrip(tmp_path):
    db = str(tmp_path / "ak.db")
    s1 = make_api_key_store(db)
    ak = s1.create(_ak(api_key="persist", workspace_id="ws-X",
                        name="persisted", role="admin", rpm_limit=120))
    # Reopen
    s2 = make_api_key_store(db)
    got = s2.lookup("persist")
    assert got is not None
    assert got.workspace_id == "ws-X"
    assert got.role == "admin"
    assert got.rpm_limit == 120
