# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PgApiKeyStore (P3) — PG mirror of SqliteApiKeyStore."""
from __future__ import annotations

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
CREATE INDEX IF NOT EXISTS idx_api_keys_workspace ON api_keys(workspace_id);
"""


def _row_to_ak(row: dict) -> ApiKey:
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


class PgApiKeyStore:
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
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (ak.key_id, ak.workspace_id, ak.api_key, ak.name,
                     ak.role, ak.rpm_limit, ak.monthly_budget,
                     ak.created_by_user_id, ak.created_at.isoformat(),
                     ak.revoked_at.isoformat() if ak.revoked_at else None))
            except Exception as e:
                # UniqueViolation, etc.
                msg = str(e).lower()
                if "unique" in msg or "duplicate" in msg:
                    raise ValueError(f"api_key collision: {ak.api_key}") from e
                raise
        return ak

    def lookup(self, api_key: str) -> ApiKey | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM api_keys "
                "WHERE api_key = %s AND revoked_at IS NULL",
                (api_key,))
            row = cur.fetchone()
        return _row_to_ak(row) if row else None

    def list_for_workspace(self, workspace_id: str) -> list[ApiKey]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM api_keys "
                "WHERE workspace_id = %s AND revoked_at IS NULL "
                "ORDER BY created_at ASC",
                (workspace_id,))
            rows = cur.fetchall()
        return [_row_to_ak(r) for r in rows]

    def revoke(self, key_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT revoked_at FROM api_keys WHERE key_id = %s",
                (key_id,))
            row = cur.fetchone()
            if not row or row["revoked_at"] is not None:
                return False
            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE api_keys SET revoked_at = %s WHERE key_id = %s",
                (now_iso, key_id))
            return True
