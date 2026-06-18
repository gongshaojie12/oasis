# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PgModelConfigStore —— PostgreSQL 后端,接口同 SQLite 版。"""
from __future__ import annotations

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


class PgModelConfigStore:
    def __init__(self, dsn: str, *, eager_init: bool = True):
        self.dsn = dsn
        self._lock = Lock()
        if eager_init:
            with self._connect() as conn:
                conn.execute(_SCHEMA)

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)

    def get(self, workspace_id: str) -> ModelConfigRecord | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT workspace_id, provider, api_key, base_url, "
                " model_name, updated_at, updated_by_user_id "
                "FROM workspace_model_config WHERE workspace_id = %s",
                (workspace_id,))
            row = cur.fetchone()
        if not row:
            return None
        return ModelConfigRecord(
            workspace_id=row["workspace_id"], provider=row["provider"],
            api_key=row["api_key"], base_url=row["base_url"],
            model_name=row["model_name"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
            updated_by_user_id=row["updated_by_user_id"])

    def upsert(self, rec: ModelConfigRecord) -> ModelConfigRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO workspace_model_config "
                "(workspace_id, provider, api_key, base_url, model_name, "
                " updated_at, updated_by_user_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (workspace_id) DO UPDATE SET "
                " provider=EXCLUDED.provider, api_key=EXCLUDED.api_key, "
                " base_url=EXCLUDED.base_url, "
                " model_name=EXCLUDED.model_name, "
                " updated_at=EXCLUDED.updated_at, "
                " updated_by_user_id=EXCLUDED.updated_by_user_id",
                (rec.workspace_id, rec.provider, rec.api_key,
                 rec.base_url, rec.model_name,
                 rec.updated_at.isoformat(), rec.updated_by_user_id))
        return rec
