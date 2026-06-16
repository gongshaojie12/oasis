# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P1: SqliteWorkspaceStore persistence tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from wanxiang.api.workspaces import (
    Workspace,
    WorkspaceInvite,
    WorkspaceMember,
    make_workspace_store,
)


def _ws(slug="ws", type="personal", owner="u1", name="WS"):
    return Workspace(workspace_id="auto", slug=slug, name=name,
                      type=type, owner_user_id=owner)


def test_sqlite_create_workspace_roundtrip(tmp_path):
    db = str(tmp_path / "ws.db")
    store = make_workspace_store(db)
    ws = store.create_workspace(_ws(slug="alice", owner="u1"))
    assert ws.workspace_id
    got = store.get_workspace(ws.workspace_id)
    assert got is not None and got.slug == "alice"


def test_sqlite_persistence_across_reopen(tmp_path):
    db = str(tmp_path / "ws.db")
    s1 = make_workspace_store(db)
    ws = s1.create_workspace(_ws(slug="persist", type="team", owner="u1"))
    s1.add_member(WorkspaceMember(workspace_id=ws.workspace_id,
                                    user_id="u1", role="owner"))
    s2 = make_workspace_store(db)
    got = s2.get_by_slug("persist")
    assert got is not None
    m = s2.get_member(got.workspace_id, "u1")
    assert m is not None and m.role == "owner"


def test_sqlite_slug_unique_constraint(tmp_path):
    db = str(tmp_path / "ws.db")
    store = make_workspace_store(db)
    store.create_workspace(_ws(slug="dup", owner="u1"))
    with pytest.raises(Exception):
        store.create_workspace(_ws(slug="dup", owner="u2"))


def test_sqlite_list_for_user(tmp_path):
    db = str(tmp_path / "ws.db")
    store = make_workspace_store(db)
    w1 = store.create_workspace(_ws(slug="ow", owner="u1"))
    w2 = store.create_workspace(_ws(slug="mb", type="team", owner="u2"))
    store.add_member(WorkspaceMember(workspace_id=w1.workspace_id,
                                       user_id="u1", role="owner"))
    store.add_member(WorkspaceMember(workspace_id=w2.workspace_id,
                                       user_id="u2", role="owner"))
    store.add_member(WorkspaceMember(workspace_id=w2.workspace_id,
                                       user_id="u1", role="member"))
    wss = store.list_for_user("u1")
    assert {w.slug for w in wss} == {"ow", "mb"}


def test_sqlite_invite_create_consume(tmp_path):
    db = str(tmp_path / "ws.db")
    store = make_workspace_store(db)
    ws = store.create_workspace(_ws(slug="inv", type="team", owner="u1"))
    expires = datetime.now(timezone.utc) + timedelta(days=1)
    store.create_invite(WorkspaceInvite(
        invite_id="auto", workspace_id=ws.workspace_id,
        invited_email="x@x.com", role="member",
        token="tok-pg", expires_at=expires, invited_by_user_id="u1"))
    inv = store.get_invite_by_token("tok-pg")
    assert inv is not None
    consumed = store.consume_invite("tok-pg")
    assert consumed is not None and consumed.accepted_at is not None
    assert store.consume_invite("tok-pg") is None
