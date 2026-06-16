# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Workspace dual-mode (personal/team) + members + invites (P1).

Mirrors ``users.py`` factory pattern.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Literal
from urllib.parse import urlparse


@dataclass
class Workspace:
    workspace_id: str
    slug: str
    name: str
    type: Literal["personal", "team"]
    owner_user_id: str
    locale: str = "zh"
    balance_cost_units: int = 0
    monthly_budget: int | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "slug": self.slug,
            "name": self.name,
            "type": self.type,
            "owner_user_id": self.owner_user_id,
            "locale": self.locale,
            "balance_cost_units": self.balance_cost_units,
            "monthly_budget": self.monthly_budget,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class WorkspaceMember:
    workspace_id: str
    user_id: str
    role: Literal["owner", "admin", "member"]
    joined_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "role": self.role,
            "joined_at": self.joined_at.isoformat(),
        }


@dataclass
class WorkspaceInvite:
    invite_id: str
    workspace_id: str
    invited_email: str
    role: Literal["admin", "member"]
    token: str
    expires_at: datetime
    invited_by_user_id: str
    accepted_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "invite_id": self.invite_id,
            "workspace_id": self.workspace_id,
            "invited_email": self.invited_email,
            "role": self.role,
            "token": self.token,
            "expires_at": self.expires_at.isoformat(),
            "accepted_at": (self.accepted_at.isoformat()
                              if self.accepted_at else None),
            "invited_by_user_id": self.invited_by_user_id,
        }


# ---- In-memory store ----

class InMemoryWorkspaceStore:
    def __init__(self):
        self._ws: dict[str, Workspace] = {}
        self._by_slug: dict[str, str] = {}
        self._members: list[WorkspaceMember] = []
        self._invites: dict[str, WorkspaceInvite] = {}
        self._lock = Lock()

    def create_workspace(self, ws: Workspace) -> Workspace:
        if ws.workspace_id == "auto":
            ws.workspace_id = uuid.uuid4().hex
        with self._lock:
            if ws.slug in self._by_slug:
                raise ValueError(f"slug already exists: {ws.slug}")
            self._ws[ws.workspace_id] = ws
            self._by_slug[ws.slug] = ws.workspace_id
        return ws

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        return self._ws.get(workspace_id)

    def get_by_slug(self, slug: str) -> Workspace | None:
        wid = self._by_slug.get(slug)
        return self._ws.get(wid) if wid else None

    def list_for_user(self, user_id: str) -> list[Workspace]:
        with self._lock:
            ids = {m.workspace_id for m in self._members
                   if m.user_id == user_id}
        return [self._ws[i] for i in ids if i in self._ws]

    def add_member(self, member: WorkspaceMember) -> None:
        with self._lock:
            # Replace if exists (idempotent)
            self._members = [m for m in self._members
                              if not (m.workspace_id == member.workspace_id
                                       and m.user_id == member.user_id)]
            self._members.append(member)

    def get_member(self, workspace_id: str,
                    user_id: str) -> WorkspaceMember | None:
        for m in self._members:
            if m.workspace_id == workspace_id and m.user_id == user_id:
                return m
        return None

    def list_members(self, workspace_id: str) -> list[WorkspaceMember]:
        return [m for m in self._members if m.workspace_id == workspace_id]

    def create_invite(self, inv: WorkspaceInvite) -> WorkspaceInvite:
        if inv.invite_id == "auto":
            inv.invite_id = uuid.uuid4().hex
        with self._lock:
            self._invites[inv.token] = inv
        return inv

    def get_invite_by_token(self, token: str) -> WorkspaceInvite | None:
        return self._invites.get(token)

    def consume_invite(self, token: str) -> WorkspaceInvite | None:
        with self._lock:
            inv = self._invites.get(token)
            if not inv:
                return None
            if inv.accepted_at is not None:
                return None
            now = datetime.now(timezone.utc)
            if inv.expires_at < now:
                return None
            inv.accepted_at = now
            return inv


def make_workspace_store(dsn: str | None, *, eager_init: bool = True):
    if not dsn:
        return InMemoryWorkspaceStore()
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()
    if len(scheme) == 1 and scheme.isalpha():
        scheme = ""
    if scheme in ("postgresql", "postgres"):
        from wanxiang.api.workspace_store_pg import PgWorkspaceStore
        return PgWorkspaceStore(dsn, eager_init=eager_init)
    if scheme == "sqlite":
        path = parsed.path or dsn[len("sqlite:"):]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        from wanxiang.api.workspace_store_sqlite import SqliteWorkspaceStore
        return SqliteWorkspaceStore(path)
    if not scheme:
        from wanxiang.api.workspace_store_sqlite import SqliteWorkspaceStore
        return SqliteWorkspaceStore(dsn)
    raise ValueError(f"unsupported workspace store DSN scheme: {scheme!r}")


__all__ = [
    "Workspace", "WorkspaceMember", "WorkspaceInvite",
    "InMemoryWorkspaceStore", "make_workspace_store",
]
