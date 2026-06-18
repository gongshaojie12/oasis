# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteModelConfigStore —— 每工作区一行大模型配置。"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from threading import Lock

from wanxiang.api.model_config import ModelConfigRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS workspace_model_config (
    workspace_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    api_key TEXT,
    base_url TEXT,
    model_name TEXT,
    updated_at TEXT NOT NULL,
    updated_by_user_id TEXT
);
"""


def _row_to_rec(row: sqlite3.Row) -> ModelConfigRecord:
    return ModelConfigRecord(
        workspace_id=row["workspace_id"],
        provider=row["provider"],
        api_key=row["api_key"],
        base_url=row["base_url"],
        model_name=row["model_name"],
        updated_at=datetime.fromisoformat(row["updated_at"]),
        updated_by_user_id=row["updated_by_user_id"],
    )


class SqliteModelConfigStore:
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

    def get(self, workspace_id: str) -> ModelConfigRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workspace_model_config WHERE workspace_id = ?",
                (workspace_id,)).fetchone()
        return _row_to_rec(row) if row else None

    def upsert(self, rec: ModelConfigRecord) -> ModelConfigRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO workspace_model_config "
                "(workspace_id, provider, api_key, base_url, model_name, "
                " updated_at, updated_by_user_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(workspace_id) DO UPDATE SET "
                " provider=excluded.provider, api_key=excluded.api_key, "
                " base_url=excluded.base_url, model_name=excluded.model_name, "
                " updated_at=excluded.updated_at, "
                " updated_by_user_id=excluded.updated_by_user_id",
                (rec.workspace_id, rec.provider, rec.api_key, rec.base_url,
                 rec.model_name, rec.updated_at.isoformat(),
                 rec.updated_by_user_id))
        return rec
