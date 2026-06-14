# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PgAuditStore (M3-13) — mirror of SqliteAuditStore."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from threading import Lock

import psycopg
from psycopg.rows import dict_row

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
"""


def _row_to_event(row) -> AuditEvent:
    return AuditEvent(
        event_id=row["event_id"], tenant_id=row["tenant_id"],
        action=row["action"], resource_type=row["resource_type"],
        resource_id=row["resource_id"], request_id=row["request_id"],
        method=row["method"], path=row["path"], status=row["status"],
        ip=row["ip"], user_agent=row["user_agent"],
        detail=json.loads(row["detail"]) if row["detail"] else None,
        recorded_at=datetime.fromisoformat(row["recorded_at"]))


class PgAuditStore:
    def __init__(self, dsn: str, *, eager_init: bool = True):
        self.dsn = dsn
        self._lock = Lock()
        if eager_init:
            with self._connect() as conn:
                conn.execute(_SCHEMA)

    def _connect(self):
        return psycopg.connect(self.dsn, autocommit=True,
                                row_factory=dict_row)

    def record(self, event: AuditEvent) -> AuditEvent:
        if event.event_id == "auto":
            event.event_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_events "
                "(event_id, tenant_id, action, resource_type, resource_id, "
                "request_id, method, path, status, ip, user_agent, detail, "
                "recorded_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
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
        clauses = ["tenant_id = %s"]
        params: list = [tenant_id]
        if start is not None:
            clauses.append("recorded_at >= %s")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("recorded_at < %s")
            params.append(end.isoformat())
        if action is not None:
            clauses.append("action = %s")
            params.append(action)
        sql = "SELECT * FROM audit_events WHERE " + " AND ".join(clauses)
        with self._connect() as conn:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
        events = [_row_to_event(r) for r in rows]
        return _aggregate(events, limit=limit)
