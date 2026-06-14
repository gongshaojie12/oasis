# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteAuditStore (M3-13)."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from threading import Lock

from wanxiang.api.audit import AuditEvent, _aggregate

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    request_id TEXT,
    method TEXT,
    path TEXT,
    status INTEGER,
    ip TEXT,
    user_agent TEXT,
    detail TEXT,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_events_tenant_time
    ON audit_events(tenant_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_action
    ON audit_events(tenant_id, action, recorded_at DESC);
"""


def _row_to_event(row) -> AuditEvent:
    return AuditEvent(
        event_id=row["event_id"],
        tenant_id=row["tenant_id"],
        action=row["action"],
        resource_type=row["resource_type"],
        resource_id=row["resource_id"],
        request_id=row["request_id"],
        method=row["method"],
        path=row["path"],
        status=row["status"],
        ip=row["ip"],
        user_agent=row["user_agent"],
        detail=json.loads(row["detail"]) if row["detail"] else None,
        recorded_at=datetime.fromisoformat(row["recorded_at"]),
    )


class SqliteAuditStore:
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

    def record(self, event: AuditEvent) -> AuditEvent:
        if event.event_id == "auto":
            event.event_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_events "
                "(event_id, tenant_id, action, resource_type, resource_id, "
                "request_id, method, path, status, ip, user_agent, detail, "
                "recorded_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (event.event_id, event.tenant_id, event.action,
                 event.resource_type, event.resource_id, event.request_id,
                 event.method, event.path, event.status, event.ip,
                 event.user_agent,
                 (json.dumps(event.detail, ensure_ascii=False)
                  if event.detail else None),
                 event.recorded_at.isoformat()))
        return event

    def query(self, tenant_id: str, *, start=None, end=None, action=None,
              limit: int = 100) -> dict:
        clauses = ["tenant_id = ?"]
        params: list = [tenant_id]
        if start is not None:
            clauses.append("recorded_at >= ?")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("recorded_at < ?")
            params.append(end.isoformat())
        if action is not None:
            clauses.append("action = ?")
            params.append(action)
        sql = "SELECT * FROM audit_events WHERE " + " AND ".join(clauses)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        events = [_row_to_event(r) for r in rows]
        return _aggregate(events, limit=limit)
