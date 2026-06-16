# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P6: SqliteSandboxStore persistence tests."""
from __future__ import annotations

from datetime import datetime, timezone

from wanxiang.api.sandboxes import (
    ChatMessage,
    Sandbox,
    make_sandbox_store,
)


def _sb(workspace_id="ws1", name="Box A"):
    return Sandbox(sandbox_id="auto", workspace_id=workspace_id, name=name)


def test_sqlite_create_sandbox_roundtrip(tmp_path):
    db = str(tmp_path / "sb.db")
    store = make_sandbox_store(db)
    sb = store.create_sandbox(_sb(name="Round"))
    got = store.get_sandbox(sb.sandbox_id)
    assert got is not None and got.name == "Round"
    assert got.population_size == 1000  # default
    assert got.emoji == "🥤"


def test_sqlite_persistence_across_reopen(tmp_path):
    db = str(tmp_path / "sb.db")
    s1 = make_sandbox_store(db)
    sb = s1.create_sandbox(_sb(name="Persist"))
    s1.add_message(ChatMessage(message_id="auto", sandbox_id=sb.sandbox_id,
                                role="user", content="hello",
                                metadata={"k": "v"}))
    s2 = make_sandbox_store(db)
    got = s2.get_sandbox(sb.sandbox_id)
    assert got is not None and got.name == "Persist"
    msgs = s2.list_messages(sb.sandbox_id)
    assert len(msgs) == 1
    assert msgs[0].content == "hello"
    assert msgs[0].metadata == {"k": "v"}


def test_sqlite_list_for_workspace_orders_desc(tmp_path):
    db = str(tmp_path / "sb.db")
    store = make_sandbox_store(db)
    a = store.create_sandbox(_sb(name="A"))
    store.create_sandbox(_sb(name="B"))
    # Touch A by sending a newer message so it should sort to the top
    store.add_message(ChatMessage(message_id="auto", sandbox_id=a.sandbox_id,
                                    role="user", content="bump",
                                    created_at=datetime.now(timezone.utc)))
    items = store.list_for_workspace("ws1")
    assert items[0].sandbox_id == a.sandbox_id


def test_sqlite_archived_filter(tmp_path):
    db = str(tmp_path / "sb.db")
    store = make_sandbox_store(db)
    a = store.create_sandbox(_sb(name="A"))
    store.create_sandbox(_sb(name="B"))
    store.update_sandbox(a.sandbox_id, archived=True)
    items = store.list_for_workspace("ws1")
    assert [s.name for s in items] == ["B"]
    items_all = store.list_for_workspace("ws1", include_archived=True)
    assert {s.name for s in items_all} == {"A", "B"}


def test_sqlite_delete_sandbox_cascades_messages(tmp_path):
    db = str(tmp_path / "sb.db")
    store = make_sandbox_store(db)
    sb = store.create_sandbox(_sb())
    store.add_message(ChatMessage(message_id="auto", sandbox_id=sb.sandbox_id,
                                    role="user", content="x"))
    assert store.delete_sandbox(sb.sandbox_id) is True
    assert store.get_sandbox(sb.sandbox_id) is None
    assert store.list_messages(sb.sandbox_id) == []
