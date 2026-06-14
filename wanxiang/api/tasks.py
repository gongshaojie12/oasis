# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""In-memory simulation task store (M3-2 MVP; Redis-backed later)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class SimulationTask:
    id: str
    tenant_id: str
    status: TaskStatus
    created_at: datetime
    request: Any  # SimulateRequest (avoid circular import)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: Any | None = None       # SimulateResponse on success
    error: str | None = None        # error message on failure


class TaskStore:
    def __init__(self):
        self._tasks: dict[str, SimulationTask] = {}
        self._lock = Lock()

    def create(self, tenant_id: str, request: Any) -> SimulationTask:
        task = SimulationTask(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            request=request,
        )
        with self._lock:
            self._tasks[task.id] = task
        return task

    def get(self, tenant_id: str, task_id: str) -> SimulationTask | None:
        with self._lock:
            t = self._tasks.get(task_id)
        if t is None or t.tenant_id != tenant_id:
            return None
        return t

    def update(self, task_id: str, **fields) -> None:
        with self._lock:
            t = self._tasks.get(task_id)
            if t is None:
                return
            for k, v in fields.items():
                setattr(t, k, v)

    def list_for_tenant(self, tenant_id: str, limit: int = 20,
                        offset: int = 0) -> list[SimulationTask]:
        with self._lock:
            items = [t for t in self._tasks.values()
                     if t.tenant_id == tenant_id]
        # newest first
        items.sort(key=lambda t: t.created_at, reverse=True)
        return items[offset:offset + limit]


from urllib.parse import urlparse


def make_task_store(dsn: str | None, *, eager_init: bool = True):
    """Dispatch by DSN scheme.

    - None / "" → in-memory TaskStore
    - sqlite:///abs.db, sqlite:rel.db, or plain path → SqliteTaskStore
    - postgresql:// or postgres:// → PgTaskStore
    - other schemes → ValueError

    `eager_init` only matters for PG: when False, skip schema bootstrap
    (used by tests that don't want to actually connect).
    """
    if not dsn:
        return TaskStore()

    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()

    # Windows 裸路径 C:\foo\bar.db / C:/foo/bar.db 会被 urlparse 解析成
    # scheme='c'；这是路径不是 DSN，按 backwards-compat 走 SQLite。
    if len(scheme) == 1 and scheme.isalpha():
        scheme = ""

    if scheme in ("postgresql", "postgres"):
        from wanxiang.api.task_store_pg import PgTaskStore
        return PgTaskStore(dsn, eager_init=eager_init)

    if scheme == "sqlite":
        # sqlite:///abs → parsed.path = '/abs' (POSIX) or '/c:/...' (Windows)
        # sqlite:rel  → parsed.path = '' and dsn[7:] is the rest
        path = parsed.path or dsn[len("sqlite:"):]
        # 处理 Windows 形态 /c:/foo → c:/foo
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        from wanxiang.api.task_store_sqlite import SqliteTaskStore
        return SqliteTaskStore(path)

    if not scheme:
        # 裸路径：backwards-compat with WANXIANG_TASKS_DB=/data/x.db
        from wanxiang.api.task_store_sqlite import SqliteTaskStore
        return SqliteTaskStore(dsn)

    raise ValueError(f"unsupported task store DSN scheme: {scheme!r}")
