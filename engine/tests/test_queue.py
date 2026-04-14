import asyncio

import pytest

from engine.queue import TaskQueueManager, TaskStatus


@pytest.fixture
def manager():
    return TaskQueueManager(max_concurrent=2)


class TestTaskQueueManager:
    @pytest.mark.asyncio
    async def test_submit_creates_pending_task(self, manager):
        await manager.start()
        try:
            task_info = await manager.submit({"num_agents": 10})
            assert task_info.task_id is not None
            assert len(task_info.task_id) == 12
            assert task_info.params == {"num_agents": 10}
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_get_task_returns_none_for_unknown(self, manager):
        assert manager.get_task("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_task_returns_submitted_task(self, manager):
        await manager.start()
        try:
            task_info = await manager.submit({"x": 1})
            found = manager.get_task(task_info.task_id)
            assert found is not None
            assert found.task_id == task_info.task_id
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_executor_runs_and_completes(self, manager):
        results_received = []

        async def mock_executor(task_info, payload):
            results_received.append(payload)
            return {"done": True}

        manager.set_executor(mock_executor)
        await manager.start()
        try:
            task_info = await manager.submit({"step": 1})
            # Give the worker time to pick up and process the task
            await asyncio.sleep(0.2)
            refreshed = manager.get_task(task_info.task_id)
            assert refreshed.status == TaskStatus.COMPLETED
            assert refreshed.result == {"done": True}
            assert refreshed.progress == 1.0
            assert len(results_received) == 1
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_executor_failure_sets_failed_status(self, manager):
        async def failing_executor(task_info, payload):
            raise RuntimeError("Simulated failure")

        manager.set_executor(failing_executor)
        await manager.start()
        try:
            task_info = await manager.submit({"fail": True})
            await asyncio.sleep(0.2)
            refreshed = manager.get_task(task_info.task_id)
            assert refreshed.status == TaskStatus.FAILED
            assert "Simulated failure" in refreshed.error
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_cancel_pending_task(self, manager):
        # Do not set an executor so the task stays pending
        task_info = await manager.submit({"cancel_me": True})
        cancelled = manager.cancel_task(task_info.task_id)
        assert cancelled is True
        assert manager.get_task(task_info.task_id).status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_returns_false(self, manager):
        assert manager.cancel_task("no-such-id") is False

    @pytest.mark.asyncio
    async def test_cancel_already_completed(self, manager):
        async def instant_executor(task_info, payload):
            return {}

        manager.set_executor(instant_executor)
        await manager.start()
        try:
            task_info = await manager.submit({})
            await asyncio.sleep(0.2)
            assert manager.get_task(task_info.task_id).status == TaskStatus.COMPLETED
            assert manager.cancel_task(task_info.task_id) is False
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_list_tasks_returns_all(self, manager):
        async def noop(task_info, payload):
            return {}

        manager.set_executor(noop)
        await manager.start()
        try:
            await manager.submit({"a": 1})
            await manager.submit({"b": 2})
            await asyncio.sleep(0.2)
            tasks = manager.list_tasks()
            assert len(tasks) == 2
        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, manager):
        """Verify that only max_concurrent tasks run simultaneously."""
        concurrency_log = []
        active = 0
        lock = asyncio.Lock()

        async def tracked_executor(task_info, payload):
            nonlocal active
            async with lock:
                active += 1
                concurrency_log.append(active)
            await asyncio.sleep(0.1)
            async with lock:
                active -= 1
            return {}

        mgr = TaskQueueManager(max_concurrent=2)
        mgr.set_executor(tracked_executor)
        await mgr.start(num_workers=4)
        try:
            for _ in range(4):
                await mgr.submit({})
            await asyncio.sleep(1.0)
            assert max(concurrency_log) <= 2
        finally:
            await mgr.stop()

    @pytest.mark.asyncio
    async def test_no_executor_sets_failed(self, manager):
        await manager.start()
        try:
            task_info = await manager.submit({})
            await asyncio.sleep(0.2)
            refreshed = manager.get_task(task_info.task_id)
            assert refreshed.status == TaskStatus.FAILED
            assert "No executor configured" in refreshed.error
        finally:
            await manager.stop()
