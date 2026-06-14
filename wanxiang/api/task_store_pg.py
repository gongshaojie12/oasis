# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PgTaskStore: PostgreSQL backend for the simulation task store (M3-9).

镜像 SqliteTaskStore；只在 schema / 占位符 / 连接管理上不同。所有
日期时间序列化为 ISO TEXT，request/result_json 也用 TEXT，以使
round-trip 与 SQLite 完全对称。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Any

import psycopg
from psycopg.rows import dict_row

from wanxiang.api.schemas import SimulateRequest, SimulateResponse
from wanxiang.api.tasks import SimulationTask, TaskStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS simulation_tasks (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    request_json TEXT NOT NULL,
    result_json TEXT,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_simulation_tasks_tenant
    ON simulation_tasks(tenant_id, created_at DESC);
"""


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _parse_dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


class PgTaskStore:
    def __init__(self, dsn: str, *, eager_init: bool = True):
        self.dsn = dsn
        self._lock = Lock()
        if eager_init:
            with self._connect() as conn:
                conn.execute(_SCHEMA)

    def _connect(self):
        # psycopg 3 connections are autocommit by default unless told otherwise;
        # we want auto-commit so simple writes don't require manual conn.commit()
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)

    def _row_to_task(self, row: dict) -> SimulationTask:
        req = SimulateRequest.model_validate_json(row["request_json"])
        result = None
        if row["result_json"]:
            result = SimulateResponse.model_validate_json(row["result_json"])
        return SimulationTask(
            id=row["id"],
            tenant_id=row["tenant_id"],
            status=TaskStatus(row["status"]),
            created_at=_parse_dt(row["created_at"]),
            started_at=_parse_dt(row["started_at"]),
            finished_at=_parse_dt(row["finished_at"]),
            request=req,
            result=result,
            error=row["error"],
        )

    def create(self, tenant_id: str, request: SimulateRequest) -> SimulationTask:
        task = SimulationTask(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            request=request,
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO simulation_tasks "
                "(id, tenant_id, status, created_at, request_json) "
                "VALUES (%s, %s, %s, %s, %s)",
                (task.id, task.tenant_id, task.status.value,
                 _iso(task.created_at), request.model_dump_json()))
        return task

    def get(self, tenant_id: str, task_id: str) -> SimulationTask | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM simulation_tasks WHERE id = %s AND tenant_id = %s",
                (task_id, tenant_id))
            row = cur.fetchone()
        return self._row_to_task(row) if row else None

    def update(self, task_id: str, **fields) -> None:
        if not fields:
            return
        cols: list[str] = []
        vals: list[Any] = []
        for k, v in fields.items():
            if k == "status":
                cols.append("status = %s")
                vals.append(v.value if isinstance(v, TaskStatus) else v)
            elif k in ("started_at", "finished_at", "created_at"):
                cols.append(f"{k} = %s")
                vals.append(_iso(v) if isinstance(v, datetime) else v)
            elif k == "result":
                cols.append("result_json = %s")
                vals.append(v.model_dump_json() if v is not None else None)
            elif k == "error":
                cols.append("error = %s")
                vals.append(v)
            elif k == "request":
                cols.append("request_json = %s")
                vals.append(v.model_dump_json())
            else:
                continue
        if not cols:
            return
        vals.append(task_id)
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE simulation_tasks SET {', '.join(cols)} WHERE id = %s",
                vals)

    def list_for_tenant(self, tenant_id: str, limit: int = 20,
                        offset: int = 0) -> list[SimulationTask]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM simulation_tasks WHERE tenant_id = %s "
                "ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (tenant_id, limit, offset))
            rows = cur.fetchall()
        return [self._row_to_task(r) for r in rows]
