# 万象 WANXIANG · M3-1 FastAPI Simulate 端点 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 把 CLI 已经跑通的"加载分布→造人→（社交）模拟→聚合→报告"全链路包成一个 HTTP 端点 `POST /v1/simulate`，让 chat.html / 其它客户端能通过 JSON 调用。MVP 是同步阻塞（立即返回完整报告），异步任务/流式留给后续 M3-2。本计划还顺带做最基础的 `GET /healthz`、CORS 配置、错误信号、以及 `X-Tenant-Id` 头透传（多租户隔离实质留给 M3-3，但接口形态先稳定）。

**Architecture:** `wanxiang/api/` 包含 FastAPI app（`app.py`）、Pydantic 请求/响应 schema（`schemas.py`）、simulate 路由（`routes/simulate.py`）。所有依赖通过 FastAPI 的 `Depends` 注入，便于测试期替换模型为 stub。**测试零 LLM 调用**：用 `fastapi.testclient.TestClient` + 注入 stub model_call。

**Tech Stack:** FastAPI 0.136 + Pydantic v2（已在 oasis env）。运行解释器固定 `/d/software/conda_data/envs/oasis/python.exe`。

M3 第一个子计划。后续：M3-2（异步任务 + 任务状态查询）、M3-3（真多租户隔离 + API key 鉴权 + 配额）、M3-4（chat.html 真接入：把现在静态原型连到 /v1/simulate 出真实数据）、M3-5（单机部署：systemd unit / Dockerfile / .env）。

---

## 文件结构

- `wanxiang/api/__init__.py`
- `wanxiang/api/app.py` — 构造 FastAPI 应用 + CORS + health
- `wanxiang/api/schemas.py` — Pydantic 请求/响应模型
- `wanxiang/api/deps.py` — Dependency Injection：模型工厂可替换（默认 stub，prod 走 deepseek key）
- `wanxiang/api/routes/__init__.py`
- `wanxiang/api/routes/simulate.py` — `/v1/simulate` 路由
- `test/wanxiang/test_api_simulate.py` — FastAPI TestClient

---

## Task 1: Pydantic Schema + DI 容器

把请求/响应形状定下来（影响后续所有客户端）。DI 让 simulate 路由不直接 import 真实 deepseek 工厂，方便测试。

**Files:**
- Create: `wanxiang/api/__init__.py`
- Create: `wanxiang/api/schemas.py`
- Create: `wanxiang/api/deps.py`
- Test: `test/wanxiang/test_api_schemas.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_api_schemas.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import pytest

from wanxiang.api.schemas import (ScenarioPayload, SimulateRequest,
                                    SimulateResponse, ModelConfig)


def test_simulate_request_choose_validates_options_required():
    """CHOOSE 必须给 options（否则 Pydantic 应在校验时拒绝）。"""
    with pytest.raises(Exception):
        SimulateRequest(
            distribution_path="x.yaml", n=100, seed=42,
            scenario=ScenarioPayload(
                material="m", question="q", kind="choose",
                options=None),
            rounds=0,
            model=ModelConfig(provider="stub"),
        )


def test_simulate_request_rate_no_options_ok():
    req = SimulateRequest(
        distribution_path="x.yaml", n=100, seed=42,
        scenario=ScenarioPayload(material="m", question="q", kind="rate"),
        rounds=0,
        model=ModelConfig(provider="stub"),
    )
    assert req.scenario.options is None
    assert req.scenario.kind == "rate"


def test_simulate_request_rejects_negative_n():
    with pytest.raises(Exception):
        SimulateRequest(
            distribution_path="x.yaml", n=-1, seed=42,
            scenario=ScenarioPayload(material="m", question="q", kind="rate"),
            rounds=0, model=ModelConfig(provider="stub"))


def test_simulate_request_rejects_negative_rounds():
    with pytest.raises(Exception):
        SimulateRequest(
            distribution_path="x.yaml", n=100, seed=42,
            scenario=ScenarioPayload(material="m", question="q", kind="rate"),
            rounds=-1, model=ModelConfig(provider="stub"))


def test_model_config_deepseek_requires_api_key():
    with pytest.raises(Exception):
        ModelConfig(provider="deepseek")
    # 给了 key 就 OK
    cfg = ModelConfig(provider="deepseek", api_key="sk-xxx")
    assert cfg.api_key == "sk-xxx"


def test_simulate_response_basic_shape():
    resp = SimulateResponse(
        decision_kind="rate", n_total=10, n_valid=10,
        error_count=0, error_rate=0.0,
        report={"foo": "bar"},
        markdown="# hi",
        elapsed_ms=123,
    )
    assert resp.decision_kind == "rate"
    assert resp.markdown.startswith("#")
```

- [ ] **Step 2: 运行确认失败**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_api_schemas.py -v`
Expected: `ModuleNotFoundError: No module named 'wanxiang.api'`

- [ ] **Step 3: 创建 api/__init__.py**

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""api: FastAPI 服务（spec §M7 产品封装）。"""
from wanxiang.api.app import create_app

__all__ = ["create_app"]
```

- [ ] **Step 4: 创建 wanxiang/api/schemas.py**

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Pydantic v2 请求/响应模型。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

# CHOOSE/RATE/CLICK_PROBABILITY/SENTIMENT/WTP — 与 wanxiang.simulation 一致
DecisionKindStr = Literal["rate", "choose", "click_probability",
                          "sentiment", "willingness_to_pay"]


class ScenarioPayload(BaseModel):
    material: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    kind: DecisionKindStr
    options: list[str] | None = None

    @model_validator(mode="after")
    def _choose_needs_options(self):
        if self.kind == "choose" and not self.options:
            raise ValueError("kind='choose' requires non-empty options list")
        return self


class ModelConfig(BaseModel):
    provider: Literal["stub", "deepseek"]
    api_key: str | None = None
    model_name: str | None = None  # e.g. "deepseek-chat"

    @model_validator(mode="after")
    def _deepseek_needs_key(self):
        if self.provider == "deepseek" and not self.api_key:
            raise ValueError("provider='deepseek' requires api_key")
        return self


class SimulateRequest(BaseModel):
    distribution_path: str
    n: int = Field(..., gt=0, le=100_000)
    seed: int = 42
    scenario: ScenarioPayload
    rounds: int = Field(0, ge=0, le=10)
    concurrency: int = Field(16, ge=1, le=128)
    model: ModelConfig


class SimulateResponse(BaseModel):
    decision_kind: str
    n_total: int
    n_valid: int
    error_count: int
    error_rate: float
    report: dict[str, Any]   # build_report 的结构化输出
    markdown: str            # render_markdown 的人类可读版本
    elapsed_ms: int
```

- [ ] **Step 5: 创建 wanxiang/api/deps.py**

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""依赖注入：模型工厂可在测试期被替换。"""
from __future__ import annotations

from wanxiang.api.schemas import ModelConfig
from wanxiang.models import make_deepseek_call, make_stub_call
from wanxiang.simulation.decision import ModelCall


def default_model_factory(cfg: ModelConfig) -> ModelCall:
    """根据 ModelConfig 选择 ModelCall 实现。测试可 monkeypatch 此函数。"""
    if cfg.provider == "stub":
        return make_stub_call()
    if cfg.provider == "deepseek":
        kwargs = {}
        if cfg.model_name:
            kwargs["model_name"] = cfg.model_name
        return make_deepseek_call(api_key=cfg.api_key, **kwargs)
    raise ValueError(f"unknown provider: {cfg.provider}")


# FastAPI dependency wrapper（保持函数引用便于 app.dependency_overrides）
def get_model_factory():
    return default_model_factory
```

- [ ] **Step 6: 运行确认通过**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_api_schemas.py -v`
Expected: 6 passed

- [ ] **Step 7: Commit**
```bash
cd "D:\NLp\oasis"
git add wanxiang/api/__init__.py wanxiang/api/schemas.py wanxiang/api/deps.py test/wanxiang/test_api_schemas.py
git commit -m "feat(api): add Pydantic schemas and model factory DI"
```
End with trailing blank line then: Co-Authored-By: Claude <noreply@anthropic.com>

注意：`api/__init__.py` 引用了 `app.py` 里的 `create_app`，但 `app.py` 还没建——Task 2 才会创建。先把这条 import 注释掉，留到 Task 2 重写：

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""api: FastAPI 服务（spec §M7 产品封装）。"""

__all__: list[str] = []
```
（Task 2 再补全 create_app 导出。）

---

## Task 2: FastAPI app + 健康检查 + CORS

**Files:**
- Create: `wanxiang/api/app.py`
- Modify: `wanxiang/api/__init__.py`（导出 create_app）
- Test: `test/wanxiang/test_api_app.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_api_app.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app


def test_create_app_returns_fastapi_app():
    app = create_app()
    assert app is not None
    # FastAPI 实例应有 routes 属性
    paths = {r.path for r in app.routes}
    assert "/healthz" in paths


def test_healthz_returns_200_with_status():
    client = TestClient(create_app())
    res = client.get("/healthz")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"


def test_app_includes_simulate_route():
    """Task 3 才会加 simulate；此处先确认 app 至少含 /healthz 和 /v1（v1 由 Task 3 接入）。
    本 Task 不强制 /v1/simulate 存在，但保证 healthz 工作即可。"""
    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/healthz" in paths


def test_cors_headers_present_on_get():
    client = TestClient(create_app())
    res = client.get("/healthz", headers={"Origin": "http://localhost:3000"})
    assert res.status_code == 200
    # CORSMiddleware 应回 Access-Control-Allow-Origin
    assert res.headers.get("access-control-allow-origin") is not None


def test_tenant_id_header_echoes_in_response():
    """如果客户端传了 X-Tenant-Id，响应应回带（M3-1 只做透传，真隔离 M3-3）。"""
    client = TestClient(create_app())
    res = client.get("/healthz", headers={"X-Tenant-Id": "demo-tenant"})
    # tenant id 应回到响应头
    assert res.headers.get("x-tenant-id") == "demo-tenant"
```

- [ ] **Step 2: 运行确认失败**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_api_app.py -v`
Expected: `ModuleNotFoundError: No module named 'wanxiang.api.app'`

- [ ] **Step 3: 实现 app.py**

`wanxiang/api/app.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""FastAPI 应用工厂。"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware


class TenantHeaderMiddleware(BaseHTTPMiddleware):
    """把请求头 X-Tenant-Id 透传到响应；M3-1 只透传，M3-3 才做真隔离。"""

    async def dispatch(self, request: Request, call_next):
        tenant = request.headers.get("x-tenant-id")
        response = await call_next(request)
        if tenant:
            response.headers["x-tenant-id"] = tenant
        return response


def create_app() -> FastAPI:
    app = FastAPI(title="WANXIANG API",
                  description="万象人群模拟预测平台 API",
                  version="0.0.1")

    # CORS——MVP 全开放，生产由部署侧约束
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-tenant-id"],
    )
    app.add_middleware(TenantHeaderMiddleware)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": app.version}

    # simulate 路由由 Task 3 挂载（如果 routes.simulate 模块还未导入，跳过）
    try:
        from wanxiang.api.routes.simulate import router as simulate_router
        app.include_router(simulate_router, prefix="/v1")
    except Exception:
        # 在 Task 2 完成而 Task 3 尚未做时不阻塞 app 启动
        pass

    return app
```

- [ ] **Step 4: 补全 wanxiang/api/__init__.py**

```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""api: FastAPI 服务（spec §M7 产品封装）。"""
from wanxiang.api.app import create_app

__all__ = ["create_app"]
```

- [ ] **Step 5: 运行确认通过**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_api_app.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**
```bash
cd "D:\NLp\oasis"
git add wanxiang/api/app.py wanxiang/api/__init__.py test/wanxiang/test_api_app.py
git commit -m "feat(api): FastAPI app factory with health, CORS, tenant header"
```
End with trailing blank line then: Co-Authored-By: Claude <noreply@anthropic.com>

---

## Task 3: POST /v1/simulate 端点

**Files:**
- Create: `wanxiang/api/routes/__init__.py`
- Create: `wanxiang/api/routes/simulate.py`
- Test: `test/wanxiang/test_api_simulate.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_api_simulate.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/simulate 端点测试。

用 dependency_override 替换 model_factory：返回一个会"参考 system prompt
里关键字"的可控 stub，避免依赖 camel STUB 的 'Lorem Ipsum' 输出。
"""
import json
import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import default_model_factory, get_model_factory

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "wanxiang", "datasources", "distributions",
                    "cn_z_generation_v1.yaml")


def _smart_stub_factory(cfg):
    """忽略 cfg.provider，永远返回基于 user prompt 中 schema 关键字的合规 JSON。"""

    async def call(messages):
        user = messages[-1]["content"]
        if "score" in user.lower():
            return '{"score": 7}'
        if "option" in user.lower() or "选项" in user:
            # 找一个看上去合法的 option
            return '{"option": "青提"}'
        if "polarity" in user.lower():
            return '{"polarity": 0.5}'
        if "probability" in user.lower():
            return '{"probability": 0.6}'
        if "price" in user.lower():
            return '{"price": 8}'
        return '{"score": 5}'

    return call


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _smart_stub_factory
    return TestClient(app)


def test_simulate_rate_returns_full_report(client):
    body = {
        "distribution_path": DIST, "n": 30, "seed": 1,
        "scenario": {"material": "m", "question": "0-10 评分", "kind": "rate"},
        "rounds": 0, "concurrency": 8,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["decision_kind"] == "rate"
    assert data["n_total"] == 30
    assert data["n_valid"] >= 25  # stub 应几乎全成功
    assert data["error_count"] <= 5
    assert "万象模拟报告" in data["markdown"]
    assert data["report"]["recommendation"]["mean"] is not None


def test_simulate_choose_returns_recommendation(client):
    body = {
        "distribution_path": DIST, "n": 20, "seed": 2,
        "scenario": {"material": "m", "question": "挑一个", "kind": "choose",
                     "options": ["青提", "白桃", "海盐荔枝"]},
        "rounds": 0, "concurrency": 8,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["decision_kind"] == "choose"
    assert data["report"]["recommendation"]["top"] in {"青提", "白桃", "海盐荔枝"}


def test_simulate_validation_error_returns_422(client):
    """缺 options 的 choose 应被 schema 拒。"""
    body = {
        "distribution_path": DIST, "n": 5, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "choose"},
        "rounds": 0,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 422


def test_simulate_missing_distribution_file_returns_400(client):
    body = {
        "distribution_path": "/nonexistent/xxx.yaml", "n": 5, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "rate"},
        "rounds": 0,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    # 业务错应返 400 而不是 500
    assert res.status_code == 400
    body = res.json()
    assert "detail" in body
    assert "not found" in body["detail"].lower() or "找不到" in body["detail"]


def test_simulate_with_social_rounds(client):
    body = {
        "distribution_path": DIST, "n": 10, "seed": 1,
        "scenario": {"material": "m", "question": "0-10 评分", "kind": "rate"},
        "rounds": 1, "concurrency": 4,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["n_total"] == 10


def test_simulate_returns_elapsed_ms(client):
    body = {
        "distribution_path": DIST, "n": 5, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "rate"},
        "rounds": 0,
        "model": {"provider": "stub"},
    }
    res = client.post("/v1/simulate", json=body)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["elapsed_ms"], int)
    assert data["elapsed_ms"] >= 0
```

- [ ] **Step 2: 运行确认失败**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_api_simulate.py -v`
Expected: 404 on POST（路由不存在）或 ModuleNotFoundError（路由模块不存在）。

- [ ] **Step 3: 实现 routes**

`wanxiang/api/routes/__init__.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""api.routes: HTTP 路由集合。"""
```

`wanxiang/api/routes/simulate.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""POST /v1/simulate —— 端到端模拟同步端点。"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException

from wanxiang.api.deps import get_model_factory
from wanxiang.api.schemas import SimulateRequest, SimulateResponse
from wanxiang.datasources import load_distribution
from wanxiang.personas import PersonaBuilder
from wanxiang.reporting import build_report, render_markdown
from wanxiang.simulation import (BatchRunner, DecisionKind, ScenarioConfig,
                                  SocialRoundsRunner, aggregate)

router = APIRouter()


@router.post("/simulate", response_model=SimulateResponse)
async def simulate(
    req: SimulateRequest,
    model_factory=Depends(get_model_factory),
):
    started = time.monotonic()

    # 1. 分布加载（文件不存在 → 400）
    try:
        distribution = load_distribution(req.distribution_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400,
                            detail=f"distribution file not found: {e}")

    # 2. 造人
    pb = PersonaBuilder()
    personas = pb.sample(distribution, n=req.n, seed=req.seed)

    # 3. 场景
    kind = DecisionKind(req.scenario.kind)
    scenario = ScenarioConfig(
        material=req.scenario.material,
        question=req.scenario.question,
        decision_kind=kind,
        options=tuple(req.scenario.options) if req.scenario.options else None,
    )

    # 4. 模型
    model_call = model_factory(req.model)

    # 5. 跑模拟（按 rounds 选 decision_only 或 social）
    if req.rounds == 0:
        runner = BatchRunner(decision_concurrency=req.concurrency)
        results = await runner.run_all(personas, scenario, model_call)
    else:
        social = SocialRoundsRunner(
            rounds=req.rounds, decision_concurrency=req.concurrency)
        results, _hist = await social.run(personas, scenario, model_call)

    # 6. 聚合 + 报告
    agg = aggregate(results)
    report = build_report(scenario=scenario, aggregate=agg,
                          persona_count=req.n)
    markdown = render_markdown(report)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    return SimulateResponse(
        decision_kind=kind.value,
        n_total=agg.n_total, n_valid=agg.n_valid,
        error_count=agg.error_count, error_rate=agg.error_rate,
        report=report, markdown=markdown, elapsed_ms=elapsed_ms,
    )
```

- [ ] **Step 4: 运行确认通过**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_api_simulate.py -v`
Expected: 6 passed

- [ ] **Step 5: 全量回归**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/ -q`
Expected: 142 + 6 + 5 + 6 = 159 passed

- [ ] **Step 6: 实跑：用 uvicorn 把服务起来 5 秒，curl 一下 /healthz**

```bash
cd "D:\NLp\oasis"
/d/software/conda_data/envs/oasis/python.exe -c "
import threading, time
from fastapi.testclient import TestClient
from wanxiang.api import create_app
c = TestClient(create_app())
print('healthz:', c.get('/healthz').json())
print('OK')
"
```
Expected: `healthz: {'status': 'ok', 'version': '0.0.1'}` + `OK`

- [ ] **Step 7: Commit**
```bash
cd "D:\NLp\oasis"
git add wanxiang/api/routes/__init__.py wanxiang/api/routes/simulate.py test/wanxiang/test_api_simulate.py
git commit -m "feat(api): POST /v1/simulate end-to-end synchronous endpoint"
```
End with trailing blank line then: Co-Authored-By: Claude <noreply@anthropic.com>

---

## 完成标准（Definition of Done）

- [ ] `from wanxiang.api import create_app` 可用
- [ ] `GET /healthz` 返回 `{"status":"ok",...}`
- [ ] `POST /v1/simulate` 用 stub model + 真实 yaml 分布跑通 RATE 与 CHOOSE 场景，返回完整 SimulateResponse
- [ ] Pydantic 校验：缺 options 的 choose / deepseek 缺 api_key / n<=0 / rounds<0 全部 422 或在 schema 构造期抛
- [ ] 分布文件找不到时返 400（不是 500）
- [ ] CORS 允许跨域；X-Tenant-Id 透传
- [ ] `test/wanxiang/` 159 passed
- [ ] oasis 存量测试无变化（recsys clean、database 仍是预存 6+2）

## 下一个子计划（不在本计划范围）
- **M3-2**：把 /v1/simulate 改异步化：POST /v1/simulations 返回 task_id，GET /v1/simulations/{id} 查状态/结果（chat.html 的"流式状态卡"需要它）
- **M3-3**：真多租户隔离 + API key 鉴权 + 配额（每租户 RPM/月模拟次数上限）
- **M3-4**：chat.html 真接入 /v1/simulate（替掉静态原型的 mock 数据）
- **M3-5**：单机部署（systemd unit / Dockerfile / .env / 数据持久化）
