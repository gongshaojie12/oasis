# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteWorkspaceStore (P1)."""
from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from threading import Lock

from wanxiang.api.workspaces import (
    Workspace,
    WorkspaceInvite,
    WorkspaceMember,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('personal','team')),
    owner_user_id TEXT NOT NULL,
    locale TEXT NOT NULL DEFAULT 'zh',
    balance_cost_units INTEGER NOT NULL DEFAULT 0,
    monthly_budget INTEGER,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('owner','admin','member')),
    joined_at TEXT NOT NULL,
    PRIMARY KEY (workspace_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_members_user
    ON workspace_members(user_id);
CREATE TABLE IF NOT EXISTS workspace_invites (
    invite_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    invited_email TEXT NOT NULL,
    role TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    accepted_at TEXT,
    invited_by_user_id TEXT NOT NULL
);
"""


def _row_to_ws(row: sqlite3.Row) -> Workspace:
    return Workspace(
        workspace_id=row["workspace_id"],
        slug=row["slug"],
        name=row["name"],
        type=row["type"],
        owner_user_id=row["owner_user_id"],
        locale=row["locale"] or "zh",
        balance_cost_units=row["balance_cost_units"] or 0,
        monthly_budget=row["monthly_budget"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_member(row: sqlite3.Row) -> WorkspaceMember:
    return WorkspaceMember(
        workspace_id=row["workspace_id"],
        user_id=row["user_id"],
        role=row["role"],
        joined_at=datetime.fromisoformat(row["joined_at"]),
    )


def _row_to_invite(row: sqlite3.Row) -> WorkspaceInvite:
    return WorkspaceInvite(
        invite_id=row["invite_id"],
        workspace_id=row["workspace_id"],
        invited_email=row["invited_email"],
        role=row["role"],
        token=row["token"],
        expires_at=datetime.fromisoformat(row["expires_at"]),
        accepted_at=(datetime.fromisoformat(row["accepted_at"])
                       if row["accepted_at"] else None),
        invited_by_user_id=row["invited_by_user_id"],
    )


class SqliteWorkspaceStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._lock = Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False,
                                isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def create_workspace(self, ws: Workspace) -> Workspace:
        if ws.workspace_id == "auto":
            ws.workspace_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO workspaces "
                "(workspace_id, slug, name, type, owner_user_id, locale, "
                " balance_cost_units, monthly_budget, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ws.workspace_id, ws.slug, ws.name, ws.type,
                 ws.owner_user_id, ws.locale, ws.balance_cost_units,
                 ws.monthly_budget, ws.created_at.isoformat()))
        return ws

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workspaces WHERE workspace_id = ?",
                (workspace_id,)).fetchone()
        return _row_to_ws(row) if row else None

    def get_by_slug(self, slug: str) -> Workspace | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workspaces WHERE slug = ?",
                (slug,)).fetchone()
        return _row_to_ws(row) if row else None

    def list_for_user(self, user_id: str) -> list[Workspace]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT w.* FROM workspaces w "
                "JOIN workspace_members m ON m.workspace_id = w.workspace_id "
                "WHERE m.user_id = ? "
                "ORDER BY w.created_at ASC",
                (user_id,)).fetchall()
        return [_row_to_ws(r) for r in rows]

    def add_member(self, member: WorkspaceMember) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO workspace_members "
                "(workspace_id, user_id, role, joined_at) "
                "VALUES (?, ?, ?, ?)",
                (member.workspace_id, member.user_id, member.role,
                 member.joined_at.isoformat()))

    def get_member(self, workspace_id: str,
                    user_id: str) -> WorkspaceMember | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workspace_members "
                "WHERE workspace_id = ? AND user_id = ?",
                (workspace_id, user_id)).fetchone()
        return _row_to_member(row) if row else None

    def list_members(self, workspace_id: str) -> list[WorkspaceMember]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM workspace_members WHERE workspace_id = ? "
                "ORDER BY joined_at ASC",
                (workspace_id,)).fetchall()
        return [_row_to_member(r) for r in rows]

    def create_invite(self, inv: WorkspaceInvite) -> WorkspaceInvite:
        if inv.invite_id == "auto":
            inv.invite_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO workspace_invites "
                "(invite_id, workspace_id, invited_email, role, token, "
                " expires_at, accepted_at, invited_by_user_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (inv.invite_id, inv.workspace_id, inv.invited_email,
                 inv.role, inv.token, inv.expires_at.isoformat(),
                 inv.accepted_at.isoformat() if inv.accepted_at else None,
                 inv.invited_by_user_id))
        return inv

    def get_invite_by_token(self, token: str) -> WorkspaceInvite | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workspace_invites WHERE token = ?",
                (token,)).fetchone()
        return _row_to_invite(row) if row else None

    def consume_invite(self, token: str) -> WorkspaceInvite | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workspace_invites WHERE token = ?",
                (token,)).fetchone()
            if not row:
                return None
            inv = _row_to_invite(row)
            if inv.accepted_at is not None:
                return None
            now = datetime.now(timezone.utc)
            if inv.expires_at < now:
                return None
            conn.execute(
                "UPDATE workspace_invites SET accepted_at = ? WHERE token = ?",
                (now.isoformat(), token))
            inv.accepted_at = now
            return inv
