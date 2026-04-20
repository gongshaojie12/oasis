from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from engine.analysts.base import AnalysisContext
from engine.analysts.debate import DebateEngine
from engine.callback import CallbackClient
from engine.config import Settings, get_settings
from engine.genome.breeder import GenomeBreeder
from engine.genome.schema import BreedStrategy, GenomeData
from engine.graph.schema import GraphData
from engine.graph.analyzer import GraphAnalyzer
from engine.graph.mapper import GraphToSimulationMapper
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


class AnalysisRequest(BaseModel):
    simulation_id: str
    platform: str = "twitter"
    num_agents: int = 10
    num_steps: int = 5
    db_path: str
    debate_rounds: int = Field(default=2, ge=1, le=5)


class GraphAnalyzeRequest(BaseModel):
    graph_data: dict[str, Any]


class GraphMapRequest(BaseModel):
    graph_data: dict[str, Any]


class SnapshotRequest(BaseModel):
    db_path: str
    num_steps: int
    round_number: Optional[int] = None


class AgentChatRequest(BaseModel):
    db_path: str
    agent_id: int
    round_context: int
    message: str
    history: Optional[list[dict[str, Any]]] = None


class RoundtableRequest(BaseModel):
    db_path: str
    agent_ids: list[int]
    round_context: int
    topic: str
    num_rounds: int = Field(default=3, ge=1, le=5)


class ComposerParseRequest(BaseModel):
    description: str = Field(min_length=1, max_length=5000)


class ComposerMixRequest(BaseModel):
    dna_a: dict[str, Any]
    dna_b: dict[str, Any]
    weight_a: float = Field(default=0.5, ge=0.0, le=1.0)


class ComposerEstimateRequest(BaseModel):
    config: dict[str, Any]


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


@app.post(
    "/engine/analysis/run",
    dependencies=[Depends(verify_internal_key)],
)
async def run_analysis(body: AnalysisRequest, request: Request):
    import asyncio
    import uuid

    settings = request.app.state.settings

    task_id = str(uuid.uuid4())
    if not hasattr(request.app.state, "analysis_tasks"):
        request.app.state.analysis_tasks = {}

    state = {"task_id": task_id, "status": "running", "progress": 0.0}
    request.app.state.analysis_tasks[task_id] = state

    async def _run():
        try:
            import sqlite3

            conn = sqlite3.connect(body.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            trace_data = [dict(r) for r in cursor.execute("SELECT * FROM trace").fetchall()]
            post_data = [dict(r) for r in cursor.execute("SELECT * FROM post").fetchall()]
            user_data = [dict(r) for r in cursor.execute("SELECT * FROM user").fetchall()]

            try:
                follow_data = [dict(r) for r in cursor.execute("SELECT * FROM follow").fetchall()]
            except Exception:
                follow_data = []

            conn.close()

            context = AnalysisContext(
                simulation_id=body.simulation_id,
                platform=body.platform,
                num_agents=body.num_agents,
                num_steps=body.num_steps,
                trace_data=trace_data,
                post_data=post_data,
                user_data=user_data,
                follow_data=follow_data,
            )

            async def llm_call(prompt: str) -> str:
                from engine.llm.provider import create_model, LLMProviderRegistry
                registry = LLMProviderRegistry()
                provider = settings.default_llm_provider or "qwen"
                model_id = settings.default_llm_model or "qwen-plus"
                model = create_model(provider, model_id, settings, registry)
                from camel.messages import BaseMessage
                user_msg = BaseMessage.make_user_message(role_name="user", content=prompt)
                response = model.run([user_msg])
                return response.msgs[0].content

            async def on_progress(phase: str, progress: float) -> None:
                state["progress"] = progress

            engine = DebateEngine(
                llm_call=llm_call,
                debate_rounds=body.debate_rounds,
                on_progress=on_progress,
            )
            report = await engine.run(context)
            state["status"] = "completed"
            state["result"] = report.model_dump()
        except Exception as e:
            logger.error("Analysis failed: %s", e)
            state["status"] = "failed"
            state["error"] = str(e)

    asyncio.create_task(_run())
    return {"task_id": task_id, "status": "running"}


@app.get(
    "/engine/analysis/{task_id}",
    dependencies=[Depends(verify_internal_key)],
)
async def get_analysis_status(task_id: str, request: Request):
    tasks = getattr(request.app.state, "analysis_tasks", {})
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Analysis task not found")
    return tasks[task_id]


@app.post(
    "/engine/graph/analyze",
    dependencies=[Depends(verify_internal_key)],
)
async def analyze_graph(body: GraphAnalyzeRequest):
    graph = GraphData.model_validate(body.graph_data)
    analyzer = GraphAnalyzer(graph)
    result = analyzer.analyze()
    return result.model_dump()


@app.post(
    "/engine/graph/to-simulation",
    dependencies=[Depends(verify_internal_key)],
)
async def graph_to_simulation(body: GraphMapRequest):
    graph = GraphData.model_validate(body.graph_data)
    mapper = GraphToSimulationMapper(graph)
    return mapper.map()


@app.post(
    "/engine/timemachine/snapshots",
    dependencies=[Depends(verify_internal_key)],
)
async def extract_snapshots(body: SnapshotRequest):
    from engine.timemachine.snapshot import SnapshotExtractor

    extractor = SnapshotExtractor(body.db_path)
    if body.round_number is not None:
        snap = extractor.extract_round(body.round_number)
        return {"snapshot": snap.model_dump()}
    else:
        snaps = extractor.extract_all(body.num_steps)
        return {"snapshots": [s.model_dump() for s in snaps]}


@app.post(
    "/engine/timemachine/chat",
    dependencies=[Depends(verify_internal_key)],
)
async def agent_chat(body: AgentChatRequest, request: Request):
    from engine.timemachine.chat import AgentChatEngine, ChatMessage

    settings = request.app.state.settings

    async def llm_call(prompt: str) -> str:
        from engine.llm.provider import LLMProviderRegistry, create_model
        from camel.messages import BaseMessage

        registry = LLMProviderRegistry()
        provider = settings.default_llm_provider or "qwen"
        model_id = settings.default_llm_model or "qwen-plus"
        model = create_model(provider, model_id, settings, registry)
        user_msg = BaseMessage.make_user_message(role_name="user", content=prompt)
        response = model.run([user_msg])
        return response.msgs[0].content

    history = None
    if body.history:
        history = [ChatMessage(**m) for m in body.history]

    engine = AgentChatEngine(db_path=body.db_path, llm_call=llm_call)
    result = await engine.chat(
        agent_id=body.agent_id,
        round_context=body.round_context,
        user_message=body.message,
        history=history,
    )
    return result.model_dump()


@app.post(
    "/engine/timemachine/roundtable",
    dependencies=[Depends(verify_internal_key)],
)
async def roundtable(body: RoundtableRequest, request: Request):
    from engine.timemachine.chat import AgentChatEngine

    settings = request.app.state.settings

    async def llm_call(prompt: str) -> str:
        from engine.llm.provider import LLMProviderRegistry, create_model
        from camel.messages import BaseMessage

        registry = LLMProviderRegistry()
        provider = settings.default_llm_provider or "qwen"
        model_id = settings.default_llm_model or "qwen-plus"
        model = create_model(provider, model_id, settings, registry)
        user_msg = BaseMessage.make_user_message(role_name="user", content=prompt)
        response = model.run([user_msg])
        return response.msgs[0].content

    engine = AgentChatEngine(db_path=body.db_path, llm_call=llm_call)
    messages = await engine.roundtable(
        agent_ids=body.agent_ids,
        round_context=body.round_context,
        topic=body.topic,
        num_rounds=body.num_rounds,
    )
    return {"messages": [m.model_dump() for m in messages]}


@app.post(
    "/engine/composer/parse",
    dependencies=[Depends(verify_internal_key)],
)
async def composer_parse(body: ComposerParseRequest, request: Request):
    from engine.composer.parser import ScenarioParser

    settings = request.app.state.settings

    async def llm_call(prompt: str) -> str:
        from engine.llm.provider import LLMProviderRegistry, create_model
        from camel.messages import BaseMessage
        registry = LLMProviderRegistry()
        provider = settings.default_llm_provider or "qwen"
        model_id = settings.default_llm_model or "qwen-plus"
        model = create_model(provider, model_id, settings, registry)
        user_msg = BaseMessage.make_user_message(role_name="user", content=prompt)
        response = model.run([user_msg])
        return response.msgs[0].content

    parser = ScenarioParser(llm_call=llm_call)
    config = await parser.parse(body.description)
    return config.model_dump()


@app.post(
    "/engine/composer/mix",
    dependencies=[Depends(verify_internal_key)],
)
async def composer_mix(body: ComposerMixRequest, request: Request):
    from engine.composer.mixer import DNAMixer
    from engine.composer.schema import ScenarioDNA

    settings = request.app.state.settings

    async def llm_call(prompt: str) -> str:
        from engine.llm.provider import LLMProviderRegistry, create_model
        from camel.messages import BaseMessage
        registry = LLMProviderRegistry()
        provider = settings.default_llm_provider or "qwen"
        model_id = settings.default_llm_model or "qwen-plus"
        model = create_model(provider, model_id, settings, registry)
        user_msg = BaseMessage.make_user_message(role_name="user", content=prompt)
        response = model.run([user_msg])
        return response.msgs[0].content

    dna_a = ScenarioDNA.model_validate(body.dna_a)
    dna_b = ScenarioDNA.model_validate(body.dna_b)
    mixer = DNAMixer(llm_call=llm_call)
    config = await mixer.mix_to_config(dna_a, dna_b, body.weight_a)
    return config.model_dump()


@app.get(
    "/engine/composer/recommend",
    dependencies=[Depends(verify_internal_key)],
)
async def composer_recommend(platform: Optional[str] = None):
    from engine.composer.schema import ScenarioDNA, ScenarioConfig

    templates = [
        ScenarioConfig(
            platform="weibo", num_agents=500, num_steps=72,
            seed_content="重磅！新政策即将实施...",
            description="舆论危机仿真 — 政策争议引发两派激辩",
            dna=ScenarioDNA(conflict_level=0.8, information_density=0.6, viral_potential=0.7, sentiment_polarity=0.9, temporal_dynamics="escalation", agent_diversity=0.7, platform_fit=["weibo", "twitter"]),
        ),
        ScenarioConfig(
            platform="xiaohongshu", num_agents=200, num_steps=48,
            seed_content="今天发现了一款超好用的产品...",
            description="品牌营销仿真 — 新品种草与口碑传播",
            dna=ScenarioDNA(conflict_level=0.2, information_density=0.7, viral_potential=0.8, sentiment_polarity=0.3, temporal_dynamics="wave", agent_diversity=0.5, platform_fit=["xiaohongshu", "douyin"]),
        ),
        ScenarioConfig(
            platform="twitter", num_agents=1000, num_steps=100,
            seed_content="Breaking: Major announcement from...",
            description="信息传播研究 — 假新闻在社交网络中的扩散",
            dna=ScenarioDNA(conflict_level=0.6, information_density=0.8, viral_potential=0.9, sentiment_polarity=0.7, temporal_dynamics="escalation", agent_diversity=0.8, platform_fit=["twitter", "reddit"]),
        ),
        ScenarioConfig(
            platform="reddit", num_agents=300, num_steps=50,
            seed_content="I just tried this new product and...",
            description="产品评测仿真 — 用户对新产品的真实反馈",
            dna=ScenarioDNA(conflict_level=0.4, information_density=0.9, viral_potential=0.4, sentiment_polarity=0.5, temporal_dynamics="stable", agent_diversity=0.6, platform_fit=["reddit"]),
        ),
    ]

    filtered = templates
    if platform:
        filtered = [t for t in filtered if platform in (t.dna.platform_fit if t.dna else []) or t.platform == platform]

    return {"templates": [t.model_dump() for t in filtered]}


@app.post(
    "/engine/composer/estimate",
    dependencies=[Depends(verify_internal_key)],
)
async def composer_estimate(body: ComposerEstimateRequest):
    from engine.composer.estimator import ResourceEstimator
    from engine.composer.schema import ScenarioConfig

    config = ScenarioConfig.model_validate(body.config)
    estimator = ResourceEstimator()
    result = estimator.estimate(config)
    return result.model_dump()
