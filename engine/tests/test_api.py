import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from engine.callback import CallbackClient
from engine.config import Settings, get_settings
from engine.main import app
from engine.queue import TaskQueueManager, TaskStatus
from engine.reporter import ProgressReporter
from engine.runner import SimulationRunner


@pytest.fixture
def api_key():
    return "test-secret-key"


@pytest.fixture
def settings(api_key, monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", api_key)
    monkeypatch.setenv("NUXT_CALLBACK_URL", "http://localhost:3000")
    monkeypatch.setenv("MAX_CONCURRENT_TASKS", "1")
    monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEFAULT_LLM_MODEL", "deepseek-chat")


@pytest.fixture
def auth_headers(api_key):
    return {"X-Internal-Key": api_key}


@pytest_asyncio.fixture
async def initialized_app(settings):
    """Initialize app state for testing."""
    # Initialize app state manually since lifespan doesn't run with ASGITransport
    settings_obj = get_settings()
    callback_client = CallbackClient(
        base_url=settings_obj.nuxt_callback_url,
        internal_api_key=settings_obj.internal_api_key,
    )
    reporter = ProgressReporter(callback_client=callback_client)
    runner = SimulationRunner(settings=settings_obj, reporter=reporter)
    queue_manager = TaskQueueManager(max_concurrent=settings_obj.max_concurrent_tasks)
    queue_manager.set_executor(runner.run)
    await queue_manager.start()

    # Set state on app
    app.state.settings = settings_obj
    app.state.queue_manager = queue_manager

    yield app

    # Cleanup
    await queue_manager.stop()
    # Clear state
    delattr(app.state, "settings")
    delattr(app.state, "queue_manager")


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, initialized_app):
        transport = ASGITransport(app=initialized_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/engine/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "oasis-engine"
        assert "pending_tasks" in data
        assert "running_tasks" in data


class TestTaskEndpoints:
    @pytest.mark.asyncio
    async def test_submit_requires_auth(self, initialized_app):
        transport = ASGITransport(app=initialized_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/engine/tasks", json={"num_agents": 5})
        assert resp.status_code == 422  # missing header

    @pytest.mark.asyncio
    async def test_submit_rejects_wrong_key(self, initialized_app):
        transport = ASGITransport(app=initialized_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/engine/tasks",
                json={"num_agents": 5},
                headers={"X-Internal-Key": "wrong-key"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_submit_and_get_task(self, initialized_app, auth_headers):
        transport = ASGITransport(app=initialized_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Submit
            resp = await client.post(
                "/engine/tasks",
                json={"num_agents": 3, "num_steps": 1},
                headers=auth_headers,
            )
            assert resp.status_code == 202
            data = resp.json()
            task_id = data["task_id"]
            assert data["status"] == "pending"

            # Allow a moment for the queue to pick it up
            await asyncio.sleep(0.1)

            # Get status
            resp = await client.get(
                f"/engine/tasks/{task_id}",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            status_data = resp.json()
            assert status_data["task_id"] == task_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, initialized_app, auth_headers):
        transport = ASGITransport(app=initialized_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/engine/tasks/nonexistent",
                headers=auth_headers,
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self, initialized_app, auth_headers):
        transport = ASGITransport(app=initialized_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/engine/tasks/nonexistent/cancel",
                headers=auth_headers,
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_submitted_task(self, initialized_app, auth_headers):
        transport = ASGITransport(app=initialized_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Submit a task
            resp = await client.post(
                "/engine/tasks",
                json={"num_agents": 5, "num_steps": 100},
                headers=auth_headers,
            )
            task_id = resp.json()["task_id"]

            # Cancel it immediately
            resp = await client.post(
                f"/engine/tasks/{task_id}/cancel",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["task_id"] == task_id


class TestCallbackClient:
    @pytest.mark.asyncio
    async def test_send_progress_to_mock_server(self):
        """Test callback client against a real HTTP server (httpx mock)."""
        from engine.callback import CallbackClient

        # Use httpx's mock transport
        import httpx

        mock_response = httpx.Response(200, json={"ok": True})

        async def mock_handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["X-Internal-Key"] == "test-key"
            assert request.headers["Content-Type"] == "application/json"
            return mock_response

        transport = httpx.MockTransport(mock_handler)
        client = CallbackClient(
            base_url="http://nuxt-mock:3000",
            internal_api_key="test-key",
        )

        # Monkey-patch the _post method to use our mock transport
        original_post = client._post

        async def patched_post(path, body):
            url = f"http://nuxt-mock:3000{path}"
            async with httpx.AsyncClient(transport=transport) as http:
                resp = await http.post(
                    url,
                    json=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Internal-Key": "test-key",
                    },
                )
                return resp.status_code < 400

        client._post = patched_post

        result = await client.send_progress(
            task_id="abc123",
            current_step=3,
            total_steps=10,
            progress=0.3,
        )
        assert result is True

        result = await client.send_complete(
            task_id="abc123",
            result={"db_path": "/tmp/test.db"},
        )
        assert result is True

        result = await client.send_error(
            task_id="abc123",
            error="Something went wrong",
        )
        assert result is True
