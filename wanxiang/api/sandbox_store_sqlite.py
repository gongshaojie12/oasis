# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteSandboxStore (P6)."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from threading import Lock

from wanxiang.api.sandboxes import ChatMessage, Sandbox

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sandboxes (
    sandbox_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    emoji TEXT NOT NULL DEFAULT '🥤',
    description TEXT NOT NULL DEFAULT '',
    distribution_path TEXT NOT NULL,
    population_size INTEGER NOT NULL DEFAULT 1000,
    created_by_user_id TEXT,
    created_at TEXT NOT NULL,
    last_active_at TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sandboxes_workspace
    ON sandboxes(workspace_id, last_active_at DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id TEXT PRIMARY KEY,
    sandbox_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'text',
    metadata TEXT,
    user_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_sandbox_time
    ON chat_messages(sandbox_id, created_at);
"""


def _row_to_sandbox(row: sqlite3.Row) -> Sandbox:
    return Sandbox(
        sandbox_id=row["sandbox_id"],
        workspace_id=row["workspace_id"],
        name=row["name"],
        emoji=row["emoji"] or "🥤",
        description=row["description"] or "",
        distribution_path=row["distribution_path"],
        population_size=int(row["population_size"] or 1000),
        created_by_user_id=row["created_by_user_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_active_at=datetime.fromisoformat(row["last_active_at"]),
        archived=bool(row["archived"]),
    )


def _row_to_msg(row: sqlite3.Row) -> ChatMessage:
    metadata_raw = row["metadata"]
    try:
        metadata = json.loads(metadata_raw) if metadata_raw else {}
    except (ValueError, TypeError):
        metadata = {}
    return ChatMessage(
        message_id=row["message_id"],
        sandbox_id=row["sandbox_id"],
        role=row["role"],
        content=row["content"],
        kind=row["kind"] or "text",
        metadata=metadata if isinstance(metadata, dict) else {},
        user_id=row["user_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class SqliteSandboxStore:
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

    def create_sandbox(self, sb: Sandbox) -> Sandbox:
        if sb.sandbox_id == "auto":
            sb.sandbox_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO sandboxes "
                "(sandbox_id, workspace_id, name, emoji, description, "
                " distribution_path, population_size, created_by_user_id, "
                " created_at, last_active_at, archived) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sb.sandbox_id, sb.workspace_id, sb.name, sb.emoji,
                 sb.description, sb.distribution_path, sb.population_size,
                 sb.created_by_user_id, sb.created_at.isoformat(),
                 sb.last_active_at.isoformat(),
                 1 if sb.archived else 0))
        return sb

    def get_sandbox(self, sandbox_id: str) -> Sandbox | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sandboxes WHERE sandbox_id = ?",
                (sandbox_id,)).fetchone()
        return _row_to_sandbox(row) if row else None

    def list_for_workspace(self, workspace_id: str,
                            *, include_archived: bool = False
                            ) -> list[Sandbox]:
        sql = ("SELECT * FROM sandboxes WHERE workspace_id = ? "
               + ("" if include_archived else "AND archived = 0 ")
               + "ORDER BY last_active_at DESC")
        with self._connect() as conn:
            rows = conn.execute(sql, (workspace_id,)).fetchall()
        return [_row_to_sandbox(r) for r in rows]

    def update_sandbox(self, sandbox_id: str, **fields) -> Sandbox | None:
        allowed = {"name", "emoji", "description", "distribution_path",
                    "population_size", "last_active_at", "archived"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        if not sets:
            return self.get_sandbox(sandbox_id)
        values: list = []
        cols: list[str] = []
        for k, v in sets.items():
            cols.append(f"{k} = ?")
            if k == "last_active_at" and isinstance(v, datetime):
                values.append(v.isoformat())
            elif k == "archived":
                values.append(1 if v else 0)
            else:
                values.append(v)
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE sandboxes SET {', '.join(cols)} "
                "WHERE sandbox_id = ?",
                (*values, sandbox_id))
        return self.get_sandbox(sandbox_id)

    def delete_sandbox(self, sandbox_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM sandboxes WHERE sandbox_id = ?",
                (sandbox_id,))
            conn.execute(
                "DELETE FROM chat_messages WHERE sandbox_id = ?",
                (sandbox_id,))
            return cur.rowcount > 0

    def add_message(self, msg: ChatMessage) -> ChatMessage:
        if msg.message_id == "auto":
            msg.message_id = uuid.uuid4().hex
        meta_json = json.dumps(msg.metadata or {}, ensure_ascii=False)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO chat_messages "
                "(message_id, sandbox_id, role, content, kind, metadata, "
                " user_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (msg.message_id, msg.sandbox_id, msg.role, msg.content,
                 msg.kind, meta_json, msg.user_id,
                 msg.created_at.isoformat()))
            # bump last_active_at if sandbox exists
            conn.execute(
                "UPDATE sandboxes SET last_active_at = ? "
                "WHERE sandbox_id = ?",
                (msg.created_at.isoformat(), msg.sandbox_id))
        return msg

    def list_messages(self, sandbox_id: str, *,
                       limit: int = 200,
                       after_message_id: str | None = None
                       ) -> list[ChatMessage]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_messages WHERE sandbox_id = ? "
                "ORDER BY created_at ASC",
                (sandbox_id,)).fetchall()
        items = [_row_to_msg(r) for r in rows]
        if after_message_id:
            idx = next((i for i, m in enumerate(items)
                        if m.message_id == after_message_id), -1)
            items = items[idx + 1:]
        if limit:
            items = items[-limit:]
        return items
