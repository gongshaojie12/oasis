# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P1: Workspace + InMemoryWorkspaceStore unit tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from wanxiang.api.workspaces import (
    InMemoryWorkspaceStore,
    Workspace,
    WorkspaceInvite,
    WorkspaceMember,
)


def _ws(slug="ws", type="personal", owner="u1", name="WS"):
    return Workspace(workspace_id="auto", slug=slug, name=name,
                      type=type, owner_user_id=owner)


def test_create_personal_workspace():
    store = InMemoryWorkspaceStore()
    ws = store.create_workspace(_ws(slug="alice", type="personal", owner="u1"))
    assert ws.workspace_id and ws.workspace_id != "auto"
    assert ws.type == "personal"
    assert ws.balance_cost_units == 0


def test_create_team_workspace():
    store = InMemoryWorkspaceStore()
    ws = store.create_workspace(_ws(slug="acme", type="team", owner="u1"))
    assert ws.type == "team"


def test_slug_uniqueness():
    store = InMemoryWorkspaceStore()
    store.create_workspace(_ws(slug="dup", owner="u1"))
    with pytest.raises(ValueError):
        store.create_workspace(_ws(slug="dup", owner="u2"))


def test_add_member_and_get():
    store = InMemoryWorkspaceStore()
    ws = store.create_workspace(_ws(slug="t", type="team", owner="u1"))
    store.add_member(WorkspaceMember(workspace_id=ws.workspace_id,
                                       user_id="u1", role="owner"))
    store.add_member(WorkspaceMember(workspace_id=ws.workspace_id,
                                       user_id="u2", role="member"))
    m = store.get_member(ws.workspace_id, "u2")
    assert m is not None and m.role == "member"
    assert store.get_member(ws.workspace_id, "u404") is None


def test_list_for_user_returns_owned_and_member_of():
    store = InMemoryWorkspaceStore()
    ws1 = store.create_workspace(_ws(slug="p1", owner="u1"))
    ws2 = store.create_workspace(_ws(slug="t1", type="team", owner="u2"))
    store.add_member(WorkspaceMember(workspace_id=ws1.workspace_id,
                                       user_id="u1", role="owner"))
    store.add_member(WorkspaceMember(workspace_id=ws2.workspace_id,
                                       user_id="u2", role="owner"))
    store.add_member(WorkspaceMember(workspace_id=ws2.workspace_id,
                                       user_id="u1", role="member"))
    wss = store.list_for_user("u1")
    slugs = {w.slug for w in wss}
    assert slugs == {"p1", "t1"}


def test_list_members():
    store = InMemoryWorkspaceStore()
    ws = store.create_workspace(_ws(slug="lm", type="team", owner="u1"))
    store.add_member(WorkspaceMember(workspace_id=ws.workspace_id,
                                       user_id="u1", role="owner"))
    store.add_member(WorkspaceMember(workspace_id=ws.workspace_id,
                                       user_id="u2", role="member"))
    members = store.list_members(ws.workspace_id)
    assert len(members) == 2
    assert {m.user_id for m in members} == {"u1", "u2"}


def test_get_workspace_by_id_and_by_slug():
    store = InMemoryWorkspaceStore()
    ws = store.create_workspace(_ws(slug="findme", owner="u1"))
    assert store.get_workspace(ws.workspace_id) is not None
    by_slug = store.get_by_slug("findme")
    assert by_slug is not None and by_slug.workspace_id == ws.workspace_id
    assert store.get_by_slug("no-such-slug") is None


def test_create_invite_and_lookup_by_token():
    store = InMemoryWorkspaceStore()
    ws = store.create_workspace(_ws(slug="inv", type="team", owner="u1"))
    expires = datetime.now(timezone.utc) + timedelta(days=1)
    inv = WorkspaceInvite(invite_id="auto", workspace_id=ws.workspace_id,
                           invited_email="new@x.com", role="member",
                           token="tok-abc", expires_at=expires,
                           invited_by_user_id="u1")
    saved = store.create_invite(inv)
    assert saved.invite_id and saved.invite_id != "auto"
    got = store.get_invite_by_token("tok-abc")
    assert got is not None and got.invited_email == "new@x.com"


def test_consume_invite_marks_accepted():
    store = InMemoryWorkspaceStore()
    ws = store.create_workspace(_ws(slug="ci", type="team", owner="u1"))
    expires = datetime.now(timezone.utc) + timedelta(days=1)
    store.create_invite(WorkspaceInvite(
        invite_id="auto", workspace_id=ws.workspace_id,
        invited_email="x@x.com", role="member",
        token="ctok", expires_at=expires, invited_by_user_id="u1"))
    consumed = store.consume_invite("ctok")
    assert consumed is not None
    assert consumed.accepted_at is not None
    # consuming again returns None
    assert store.consume_invite("ctok") is None


def test_expired_invite_returns_none_on_consume():
    store = InMemoryWorkspaceStore()
    ws = store.create_workspace(_ws(slug="ex", type="team", owner="u1"))
    past = datetime.now(timezone.utc) - timedelta(days=1)
    store.create_invite(WorkspaceInvite(
        invite_id="auto", workspace_id=ws.workspace_id,
        invited_email="old@x.com", role="member",
        token="old-tok", expires_at=past, invited_by_user_id="u1"))
    assert store.consume_invite("old-tok") is None


def test_workspace_to_dict_has_keys():
    ws = Workspace(workspace_id="w1", slug="s", name="n",
                    type="personal", owner_user_id="u")
    d = ws.to_dict()
    for k in ("workspace_id", "slug", "name", "type", "owner_user_id",
              "balance_cost_units", "created_at"):
        assert k in d


def test_invite_unknown_token_returns_none():
    store = InMemoryWorkspaceStore()
    assert store.get_invite_by_token("nope") is None
    assert store.consume_invite("nope") is None
