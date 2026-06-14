# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteTaskStore: 持久化版的 TaskStore（M3-6）。

API 与 in-memory TaskStore duck-type 一致：create/get/update/list_for_tenant。
切换由 create_app() 根据 WANXIANG_TASKS_DB 环境变量决定。
"""
from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Any

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


class SqliteTaskStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # 确保父目录存在
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._lock = Lock()
        # 初始化 schema
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        # check_same_thread=False: 我们用自己的 Lock 串行化写
        conn = sqlite3.connect(self.db_path, check_same_thread=False,
                                isolation_level=None)  # autocommit off
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _row_to_task(self, row: sqlite3.Row) -> SimulationTask:
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
                "VALUES (?, ?, ?, ?, ?)",
                (task.id, task.tenant_id, task.status.value,
                 _iso(task.created_at), request.model_dump_json()))
        return task

    def get(self, tenant_id: str, task_id: str) -> SimulationTask | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM simulation_tasks WHERE id = ? AND tenant_id = ?",
                (task_id, tenant_id)).fetchone()
        return self._row_to_task(row) if row else None

    def update(self, task_id: str, **fields) -> None:
        if not fields:
            return
        cols: list[str] = []
        vals: list[Any] = []
        for k, v in fields.items():
            if k == "status":
                cols.append("status = ?")
                vals.append(v.value if isinstance(v, TaskStatus) else v)
            elif k in ("started_at", "finished_at", "created_at"):
                cols.append(f"{k} = ?")
                vals.append(_iso(v) if isinstance(v, datetime) else v)
            elif k == "result":
                cols.append("result_json = ?")
                vals.append(v.model_dump_json() if v is not None else None)
            elif k == "error":
                cols.append("error = ?")
                vals.append(v)
            elif k == "request":
                cols.append("request_json = ?")
                vals.append(v.model_dump_json())
            else:
                # 未知字段忽略——保守
                continue
        if not cols:
            return
        vals.append(task_id)
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE simulation_tasks SET {', '.join(cols)} WHERE id = ?",
                vals)

    def list_for_tenant(self, tenant_id: str, limit: int = 20,
                        offset: int = 0) -> list[SimulationTask]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM simulation_tasks WHERE tenant_id = ? "
                "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (tenant_id, limit, offset)).fetchall()
        return [self._row_to_task(r) for r in rows]
