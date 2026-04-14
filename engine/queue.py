from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("engine.queue")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskInfo(BaseModel):
    """Public-facing task metadata."""

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    current_step: int = 0
    total_steps: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    params: dict[str, Any] = Field(default_factory=dict)


class _QueueItem:
    """Internal wrapper around a queued task."""

    def __init__(self, task_info: TaskInfo, payload: dict[str, Any]) -> None:
        self.task_info = task_info
        self.payload = payload


# Type alias for the coroutine the queue calls when executing a task.
TaskExecutor = Callable[[TaskInfo, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]


class TaskQueueManager:
    """Manages an asyncio.Queue of simulation tasks with concurrency control.

    Usage:
        manager = TaskQueueManager(max_concurrent=2)
        manager.set_executor(my_run_fn)
        await manager.start()
        task_info = await manager.submit({"num_agents": 100, ...})
        ...
        await manager.stop()
    """

    def __init__(self, max_concurrent: int = 2) -> None:
        self._queue: asyncio.Queue[_QueueItem] = asyncio.Queue()
        self._tasks: dict[str, TaskInfo] = {}
        self._asyncio_tasks: dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._executor: Optional[TaskExecutor] = None
        self._workers: list[asyncio.Task] = []
        self._running = False

    def set_executor(self, executor: TaskExecutor) -> None:
        """Set the coroutine that processes each task."""
        self._executor = executor

    async def start(self, num_workers: int = 4) -> None:
        """Start background worker coroutines."""
        if self._running:
            return
        self._running = True
        for i in range(num_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)
        logger.info("TaskQueueManager started with %d workers", num_workers)

    async def stop(self) -> None:
        """Signal workers to stop and wait for them to finish."""
        self._running = False
        # Drain workers by pushing sentinel items
        for _ in self._workers:
            await self._queue.put(None)  # type: ignore[arg-type]
        for worker in self._workers:
            await worker
        self._workers.clear()
        logger.info("TaskQueueManager stopped")

    async def submit(self, params: dict[str, Any]) -> TaskInfo:
        """Submit a task and return its TaskInfo."""
        task_id = uuid.uuid4().hex[:12]
        task_info = TaskInfo(task_id=task_id, params=params)
        self._tasks[task_id] = task_info
        item = _QueueItem(task_info=task_info, payload=params)
        await self._queue.put(item)
        logger.info("Task %s submitted", task_id)
        return task_info

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Return the TaskInfo for *task_id*, or None."""
        return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Request cancellation of a task.

        Returns True if cancellation was signalled, False if the task
        is not found or already finished.
        """
        task_info = self._tasks.get(task_id)
        if task_info is None:
            return False
        if task_info.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ):
            return False
        # If there is a running asyncio.Task, cancel it
        asyncio_task = self._asyncio_tasks.get(task_id)
        if asyncio_task is not None and not asyncio_task.done():
            asyncio_task.cancel()
        task_info.status = TaskStatus.CANCELLED
        task_info.finished_at = datetime.now(timezone.utc).isoformat()
        logger.info("Task %s cancelled", task_id)
        return True

    def list_tasks(self) -> list[TaskInfo]:
        """Return all tracked tasks, newest first."""
        return sorted(
            self._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True,
        )

    async def _worker_loop(self, worker_id: int) -> None:
        """Continuously pull items from the queue and execute them."""
        while self._running:
            item = await self._queue.get()
            if item is None:
                # Sentinel received, exit
                self._queue.task_done()
                break
            task_info = item.task_info
            if task_info.status == TaskStatus.CANCELLED:
                self._queue.task_done()
                continue
            async with self._semaphore:
                await self._execute(task_info, item.payload)
            self._queue.task_done()

    async def _execute(self, task_info: TaskInfo, payload: dict[str, Any]) -> None:
        """Run the executor for a single task with error handling."""
        if self._executor is None:
            task_info.status = TaskStatus.FAILED
            task_info.error = "No executor configured"
            task_info.finished_at = datetime.now(timezone.utc).isoformat()
            return

        if task_info.status == TaskStatus.CANCELLED:
            return

        task_info.status = TaskStatus.RUNNING
        task_info.started_at = datetime.now(timezone.utc).isoformat()

        # Create an asyncio.Task so we can cancel it
        coro = self._executor(task_info, payload)
        asyncio_task = asyncio.create_task(coro)
        self._asyncio_tasks[task_info.task_id] = asyncio_task

        try:
            result = await asyncio_task
            if task_info.status == TaskStatus.CANCELLED:
                return
            task_info.status = TaskStatus.COMPLETED
            task_info.progress = 1.0
            task_info.result = result
        except asyncio.CancelledError:
            task_info.status = TaskStatus.CANCELLED
            logger.info("Task %s was cancelled during execution", task_info.task_id)
        except Exception as exc:
            task_info.status = TaskStatus.FAILED
            task_info.error = str(exc)
            logger.exception("Task %s failed: %s", task_info.task_id, exc)
        finally:
            task_info.finished_at = datetime.now(timezone.utc).isoformat()
            self._asyncio_tasks.pop(task_info.task_id, None)
