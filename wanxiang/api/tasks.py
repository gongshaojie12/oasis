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
