from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from engine.callback import CallbackClient
from engine.config import Settings, get_settings
from engine.genome.breeder import GenomeBreeder
from engine.genome.schema import BreedStrategy, GenomeData
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


class GenomeExtractRequest(BaseModel):
    source_type: str = Field(default="natural_language")
    content: str = Field(default="")
    structured_data: Optional[dict[str, Any]] = None


class GenomeBreedRequest(BaseModel):
    seeds: list[dict[str, Any]]
    target_count: int = Field(default=10, ge=1, le=10000)
    mutation_rate: float = Field(default=0.15, ge=0.0, le=1.0)
    strategy: str = Field(default="crossover")


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


@app.post(
    "/engine/genomes/extract",
    dependencies=[Depends(verify_internal_key)],
)
async def extract_genome(body: GenomeExtractRequest, request: Request):
    settings = request.app.state.settings

    async def llm_call(prompt: str) -> str:
        from engine.llm.provider import LLMProviderRegistry, create_model

        registry = LLMProviderRegistry()
        provider = settings.default_llm_provider or "qwen"
        model_id = settings.default_llm_model or "qwen-plus"
        model = create_model(provider, model_id, settings, registry)
        from camel.messages import BaseMessage

        user_msg = BaseMessage.make_user_message(role_name="user", content=prompt)
        response = model.run([user_msg])
        return response.msgs[0].content

    from engine.genome.extractor import GenomeExtractor

    extractor = GenomeExtractor(llm_call=llm_call)

    if body.structured_data:
        genome = await extractor.extract_from_structured(body.structured_data)
    else:
        genome = await extractor.extract_from_text(body.content)

    return {"genome": genome.model_dump()}


@app.post(
    "/engine/genomes/breed",
    dependencies=[Depends(verify_internal_key)],
)
async def breed_genomes(body: GenomeBreedRequest):
    seeds = [GenomeData.model_validate(s) for s in body.seeds]
    strategy = BreedStrategy(body.strategy)
    breeder = GenomeBreeder(
        seeds=seeds,
        target_count=body.target_count,
        mutation_rate=body.mutation_rate,
        strategy=strategy,
    )
    result = breeder.breed()
    diversity = breeder.compute_diversity(result)
    return {
        "genomes": [g.model_dump() for g in result],
        "diversity": round(diversity, 4),
        "count": len(result),
    }
