# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P6: Sandbox + ChatMessage model + InMemoryStore unit tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from wanxiang.api.sandboxes import (
    ChatMessage,
    InMemorySandboxStore,
    Sandbox,
)


def _sb(workspace_id="ws1", name="Box A", emoji="🥤",
         population_size=100):
    return Sandbox(sandbox_id="auto", workspace_id=workspace_id,
                    name=name, emoji=emoji,
                    population_size=population_size)


def test_create_sandbox_assigns_id():
    store = InMemorySandboxStore()
    sb = store.create_sandbox(_sb())
    assert sb.sandbox_id and sb.sandbox_id != "auto"
    assert sb.workspace_id == "ws1"
    assert sb.name == "Box A"
    got = store.get_sandbox(sb.sandbox_id)
    assert got is not None and got.sandbox_id == sb.sandbox_id


def test_sandbox_to_dict_has_all_keys():
    sb = _sb()
    d = sb.to_dict()
    for k in ("sandbox_id", "workspace_id", "name", "emoji", "description",
              "distribution_path", "population_size", "created_by_user_id",
              "created_at", "last_active_at", "archived"):
        assert k in d


def test_list_for_workspace_only_includes_owned():
    store = InMemorySandboxStore()
    store.create_sandbox(_sb(workspace_id="ws1", name="A"))
    store.create_sandbox(_sb(workspace_id="ws2", name="B"))
    store.create_sandbox(_sb(workspace_id="ws1", name="C"))
    items = store.list_for_workspace("ws1")
    names = sorted([s.name for s in items])
    assert names == ["A", "C"]


def test_list_for_workspace_excludes_archived_by_default():
    store = InMemorySandboxStore()
    sb1 = store.create_sandbox(_sb(name="A"))
    store.create_sandbox(_sb(name="B"))
    store.update_sandbox(sb1.sandbox_id, archived=True)
    items = store.list_for_workspace("ws1")
    assert [s.name for s in items] == ["B"]
    items_all = store.list_for_workspace("ws1", include_archived=True)
    assert {s.name for s in items_all} == {"A", "B"}


def test_update_sandbox_changes_fields():
    store = InMemorySandboxStore()
    sb = store.create_sandbox(_sb(name="Old"))
    updated = store.update_sandbox(sb.sandbox_id, name="New",
                                     population_size=500)
    assert updated is not None
    assert updated.name == "New"
    assert updated.population_size == 500


def test_delete_sandbox_returns_true_and_removes_messages():
    store = InMemorySandboxStore()
    sb = store.create_sandbox(_sb())
    store.add_message(ChatMessage(message_id="auto",
                                    sandbox_id=sb.sandbox_id,
                                    role="user", content="hi"))
    assert store.delete_sandbox(sb.sandbox_id) is True
    assert store.get_sandbox(sb.sandbox_id) is None
    assert store.list_messages(sb.sandbox_id) == []
    # idempotent
    assert store.delete_sandbox(sb.sandbox_id) is False


def test_add_message_bumps_last_active_at():
    store = InMemorySandboxStore()
    sb = store.create_sandbox(_sb())
    older = sb.last_active_at - timedelta(hours=1)
    store.update_sandbox(sb.sandbox_id, last_active_at=older)
    later = datetime.now(timezone.utc)
    store.add_message(ChatMessage(message_id="auto",
                                    sandbox_id=sb.sandbox_id,
                                    role="user", content="hi",
                                    created_at=later))
    sb2 = store.get_sandbox(sb.sandbox_id)
    assert sb2.last_active_at == later


def test_list_messages_orders_and_supports_after():
    store = InMemorySandboxStore()
    sb = store.create_sandbox(_sb())
    base = datetime.now(timezone.utc)
    m1 = store.add_message(ChatMessage(
        message_id="auto", sandbox_id=sb.sandbox_id,
        role="user", content="1", created_at=base))
    m2 = store.add_message(ChatMessage(
        message_id="auto", sandbox_id=sb.sandbox_id,
        role="assistant", content="2",
        created_at=base + timedelta(seconds=1)))
    m3 = store.add_message(ChatMessage(
        message_id="auto", sandbox_id=sb.sandbox_id,
        role="user", content="3",
        created_at=base + timedelta(seconds=2)))
    msgs = store.list_messages(sb.sandbox_id)
    assert [m.content for m in msgs] == ["1", "2", "3"]
    msgs_after = store.list_messages(sb.sandbox_id,
                                       after_message_id=m1.message_id)
    assert [m.content for m in msgs_after] == ["2", "3"]
    # ensure stored ids return cleanly
    assert m2.message_id and m3.message_id


def test_chat_message_to_dict_has_all_keys():
    m = ChatMessage(message_id="m1", sandbox_id="s1", role="assistant",
                     content="hello", kind="report_card",
                     metadata={"x": 1})
    d = m.to_dict()
    for k in ("message_id", "sandbox_id", "role", "content", "kind",
              "metadata", "user_id", "created_at"):
        assert k in d
    assert d["metadata"] == {"x": 1}
