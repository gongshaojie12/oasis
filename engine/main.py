from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from engine.callback import CallbackClient
from engine.config import Settings, get_settings
from engine.queue import TaskInfo, TaskQueueManager, TaskStatus
from engine.reporter import ProgressReporter
from engine.runner import SimulationRunner

logger = logging.getLogger("engine.main")


# --- Request / Response models ---

class TaskSubmitRequest(BaseModel):
    """Body for POST /engine/tasks."""

    platform_type: str = Field(default="reddit", description="twitter or reddit")
    num_steps: int = Field(default=5, ge=1, le=1000)
    num_agents: int = Field(default=10, ge=1, le=100000)
    profile_path: Optional[str] = None
    agent_profiles: Optional[list[dict[str, Any]]] = None
    seed_content: Optional[str] = None
    available_actions: Optional[list[str]] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    current_step: int
    total_steps: int
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None


class TaskCancelResponse(BaseModel):
    task_id: str
    cancelled: bool


class HealthResponse(BaseModel):
    status: str
    service: str
    pending_tasks: int
    running_tasks: int


# --- Auth dependency ---

def verify_internal_key(
    x_internal_key: str = Header(...),
    settings: Settings = Depends(get_settings),
):
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid internal API key")


# --- Application lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Build components
    callback_client = CallbackClient(
        base_url=settings.nuxt_callback_url,
        internal_api_key=settings.internal_api_key,
    )
    reporter = ProgressReporter(callback_client=callback_client)
    runner = SimulationRunner(settings=settings, reporter=reporter)
    queue_manager = TaskQueueManager(max_concurrent=settings.max_concurrent_tasks)
    queue_manager.set_executor(runner.run)
    await queue_manager.start()

    # Store on app.state for endpoint access
    app.state.settings = settings
    app.state.queue_manager = queue_manager

    logger.info("Engine started (max_concurrent=%d)", settings.max_concurrent_tasks)
    yield

    await queue_manager.stop()
    logger.info("Engine stopped")


app = FastAPI(
    title="OASIS Simulation Engine",
    version="0.1.0",
    lifespan=lifespan,
)


# --- Endpoints ---

@app.get("/engine/health", response_model=HealthResponse)
async def health(request: Request):
    qm: TaskQueueManager = request.app.state.queue_manager
    all_tasks = qm.list_tasks()
    pending = sum(1 for t in all_tasks if t.status == TaskStatus.PENDING)
    running = sum(1 for t in all_tasks if t.status == TaskStatus.RUNNING)
    return HealthResponse(
        status="ok",
        service="oasis-engine",
        pending_tasks=pending,
        running_tasks=running,
    )


@app.post(
    "/engine/tasks",
    response_model=TaskSubmitResponse,
    status_code=202,
    dependencies=[Depends(verify_internal_key)],
)
async def submit_task(body: TaskSubmitRequest, request: Request):
    qm: TaskQueueManager = request.app.state.queue_manager
    params = body.model_dump(exclude_none=True)
    task_info = await qm.submit(params)
    return TaskSubmitResponse(
        task_id=task_info.task_id,
        status=task_info.status.value,
    )


@app.get(
    "/engine/tasks/{task_id}",
    response_model=TaskStatusResponse,
    dependencies=[Depends(verify_internal_key)],
)
async def get_task_status(task_id: str, request: Request):
    qm: TaskQueueManager = request.app.state.queue_manager
    task_info = qm.get_task(task_id)
    if task_info is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(
        task_id=task_info.task_id,
        status=task_info.status.value,
        progress=task_info.progress,
        current_step=task_info.current_step,
        total_steps=task_info.total_steps,
        created_at=task_info.created_at,
        started_at=task_info.started_at,
        finished_at=task_info.finished_at,
        error=task_info.error,
        result=task_info.result,
    )


@app.post(
    "/engine/tasks/{task_id}/cancel",
    response_model=TaskCancelResponse,
    dependencies=[Depends(verify_internal_key)],
)
async def cancel_task(task_id: str, request: Request):
    qm: TaskQueueManager = request.app.state.queue_manager
    task_info = qm.get_task(task_id)
    if task_info is None:
        raise HTTPException(status_code=404, detail="Task not found")
    cancelled = qm.cancel_task(task_id)
    return TaskCancelResponse(
        task_id=task_id,
        cancelled=cancelled,
    )
