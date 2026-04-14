from __future__ import annotations

import logging
from typing import Any, Optional

from engine.callback import CallbackClient
from engine.queue import TaskInfo

logger = logging.getLogger("engine.reporter")


class ProgressReporter:
    """Bridges the simulation runner and the callback client.

    Updates the TaskInfo in-place and sends HTTP callbacks to Nuxt.
    """

    def __init__(self, callback_client: CallbackClient) -> None:
        self._client = callback_client

    async def report_progress(
        self,
        task_info: TaskInfo,
        current_step: int,
        total_steps: int,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        """Update task progress and send callback."""
        task_info.current_step = current_step
        task_info.total_steps = total_steps
        task_info.progress = current_step / total_steps if total_steps > 0 else 0.0

        await self._client.send_progress(
            task_id=task_info.task_id,
            current_step=current_step,
            total_steps=total_steps,
            progress=task_info.progress,
            data=data,
        )
        logger.info(
            "Task %s progress: step %d/%d (%.1f%%)",
            task_info.task_id,
            current_step,
            total_steps,
            task_info.progress * 100,
        )

    async def report_complete(
        self,
        task_info: TaskInfo,
        result: dict[str, Any],
    ) -> None:
        """Send completion callback."""
        await self._client.send_complete(
            task_id=task_info.task_id,
            result=result,
        )
        logger.info("Task %s completed", task_info.task_id)

    async def report_error(
        self,
        task_info: TaskInfo,
        error: str,
    ) -> None:
        """Send error callback."""
        await self._client.send_error(
            task_id=task_info.task_id,
            error=error,
        )
        logger.error("Task %s error: %s", task_info.task_id, error)
