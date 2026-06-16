# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteApiKeyStore (P3)."""
from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from threading import Lock

from wanxiang.api.api_keys import ApiKey

_SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    key_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    api_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    rpm_limit INTEGER NOT NULL DEFAULT 60,
    monthly_budget INTEGER,
    created_by_user_id TEXT,
    created_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_api_keys_workspace
    ON api_keys(workspace_id);
"""


def _row_to_ak(row: sqlite3.Row) -> ApiKey:
    return ApiKey(
        key_id=row["key_id"],
        workspace_id=row["workspace_id"],
        api_key=row["api_key"],
        name=row["name"],
        role=row["role"] or "member",
        rpm_limit=row["rpm_limit"] or 60,
        monthly_budget=row["monthly_budget"],
        created_by_user_id=row["created_by_user_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        revoked_at=(datetime.fromisoformat(row["revoked_at"])
                     if row["revoked_at"] else None),
    )


class SqliteApiKeyStore:
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

    def create(self, ak: ApiKey) -> ApiKey:
        if ak.key_id == "auto":
            ak.key_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO api_keys "
                    "(key_id, workspace_id, api_key, name, role, rpm_limit, "
                    " monthly_budget, created_by_user_id, created_at, "
                    " revoked_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (ak.key_id, ak.workspace_id, ak.api_key, ak.name,
                     ak.role, ak.rpm_limit, ak.monthly_budget,
                     ak.created_by_user_id, ak.created_at.isoformat(),
                     ak.revoked_at.isoformat() if ak.revoked_at else None))
            except sqlite3.IntegrityError as e:
                raise ValueError(f"api_key collision: {ak.api_key}") from e
        return ak

    def lookup(self, api_key: str) -> ApiKey | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM api_keys WHERE api_key = ? AND revoked_at IS NULL",
                (api_key,)).fetchone()
        return _row_to_ak(row) if row else None

    def list_for_workspace(self, workspace_id: str) -> list[ApiKey]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM api_keys "
                "WHERE workspace_id = ? AND revoked_at IS NULL "
                "ORDER BY created_at ASC",
                (workspace_id,)).fetchall()
        return [_row_to_ak(r) for r in rows]

    def revoke(self, key_id: str) -> bool:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT revoked_at FROM api_keys WHERE key_id = ?",
                (key_id,)).fetchone()
            if not row or row["revoked_at"] is not None:
                return False
            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE api_keys SET revoked_at = ? WHERE key_id = ?",
                (now_iso, key_id))
            return True
