# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteUsageStore (M3-10): 持久化版的计费事件存储。"""
from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime
from threading import Lock

from wanxiang.api.usage import (UsageEvent, _aggregate, _month_window)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    task_id TEXT,
    mode TEXT NOT NULL,
    n_agents INTEGER NOT NULL,
    rounds INTEGER NOT NULL,
    decision_kind TEXT NOT NULL,
    cost_units INTEGER NOT NULL,
    status TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_usage_events_tenant_time
    ON usage_events(tenant_id, recorded_at DESC);
"""


def _row_to_event(row) -> UsageEvent:
    return UsageEvent(
        event_id=row["event_id"],
        tenant_id=row["tenant_id"],
        task_id=row["task_id"],
        mode=row["mode"],
        n_agents=row["n_agents"],
        rounds=row["rounds"],
        decision_kind=row["decision_kind"],
        cost_units=row["cost_units"],
        status=row["status"],
        recorded_at=datetime.fromisoformat(row["recorded_at"]),
    )


class SqliteUsageStore:
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

    def record(self, event: UsageEvent) -> UsageEvent:
        if event.event_id == "auto":
            event.event_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO usage_events "
                "(event_id, tenant_id, task_id, mode, n_agents, rounds, "
                "decision_kind, cost_units, status, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (event.event_id, event.tenant_id, event.task_id, event.mode,
                 event.n_agents, event.rounds, event.decision_kind,
                 event.cost_units, event.status,
                 event.recorded_at.isoformat()))
        return event

    def query(self, tenant_id: str, start: datetime, end: datetime) -> dict:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM usage_events WHERE tenant_id = ? "
                "AND recorded_at >= ? AND recorded_at < ?",
                (tenant_id, start.isoformat(), end.isoformat())).fetchall()
        events = [_row_to_event(r) for r in rows]
        result = _aggregate(events)
        result["period"] = {"start": start.isoformat(), "end": end.isoformat()}
        return result

    def monthly(self, tenant_id: str, year: int, month: int) -> dict:
        start, end = _month_window(year, month)
        return self.query(tenant_id, start, end)
