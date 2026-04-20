# P2-2 Scenario Composer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a "Scenario Composer" that lets users describe simulation scenarios in natural language, auto-maps to structured config via LLM, supports Scene DNA mixing, parameter visualization tuning, and resource estimation.

**Architecture:** Engine-side Python module (`engine/composer/`) handles LLM-based parsing, DNA mixing, recommendation, and estimation. Nuxt server proxies 4 API routes. Frontend adds an "AI Compose" tab to the simulation create wizard with DNA radar chart, agent distribution pie, timeline editor, and estimation panel.

**Tech Stack:** Python/Pydantic (engine), Nuxt 4/h3 (server API), Vue 3 + Naive UI + ECharts (frontend), Drizzle ORM/SQLite (DB for scenario templates), Zod (validation)

---

### Task 1: Engine — Scenario Parser (`engine/composer/parser.py`)

**Files:**
- Create: `engine/composer/__init__.py`
- Create: `engine/composer/schema.py`
- Create: `engine/composer/parser.py`

- [ ] **Step 1: Create schema models**

Create `engine/composer/schema.py`:

```python
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class AgentGroup(BaseModel):
    name: str
    ratio: float = Field(ge=0.0, le=1.0)
    stance_range: list[float] = Field(default_factory=lambda: [0.0, 0.0])


class EventInjection(BaseModel):
    round: int = Field(ge=1)
    content: str


class ScenarioDNA(BaseModel):
    conflict_level: float = Field(default=0.5, ge=0.0, le=1.0)
    information_density: float = Field(default=0.5, ge=0.0, le=1.0)
    viral_potential: float = Field(default=0.5, ge=0.0, le=1.0)
    sentiment_polarity: float = Field(default=0.5, ge=0.0, le=1.0)
    temporal_dynamics: str = Field(default="stable")
    agent_diversity: float = Field(default=0.5, ge=0.0, le=1.0)
    platform_fit: list[str] = Field(default_factory=lambda: ["twitter"])


class ScenarioConfig(BaseModel):
    platform: str = "twitter"
    num_agents: int = Field(default=50, ge=1, le=100000)
    num_steps: int = Field(default=10, ge=1, le=1000)
    seed_content: str = ""
    agent_groups: list[AgentGroup] = Field(default_factory=list)
    event_injections: list[EventInjection] = Field(default_factory=list)
    available_actions: list[str] = Field(default_factory=lambda: ["CREATE_POST", "COMMENT", "LIKE", "REPOST", "FOLLOW"])
    dna: Optional[ScenarioDNA] = None
    description: str = ""


class ResourceEstimate(BaseModel):
    llm_calls: int = 0
    estimated_tokens: int = 0
    estimated_minutes: float = 0.0
    estimated_cost_usd: float = 0.0
```

Create `engine/composer/__init__.py`:

```python
from engine.composer.schema import ScenarioConfig, ScenarioDNA, ResourceEstimate
from engine.composer.parser import ScenarioParser

__all__ = ["ScenarioConfig", "ScenarioDNA", "ResourceEstimate", "ScenarioParser"]
```

- [ ] **Step 2: Create ScenarioParser**

Create `engine/composer/parser.py`:

```python
from __future__ import annotations

import json
import logging
from typing import Callable, Awaitable

from engine.composer.schema import ScenarioConfig, ScenarioDNA, AgentGroup, EventInjection

logger = logging.getLogger("engine.composer.parser")

PARSE_PROMPT = """You are a social media simulation scenario designer. Parse the user's natural language description into a structured simulation configuration.

User description:
{description}

Return a valid JSON object with these fields:
{{
  "platform": "twitter" | "reddit" | "weibo" | "xiaohongshu" | "douyin" | "kuaishou" | "bilibili" | "wechat_video",
  "num_agents": <integer 1-100000>,
  "num_steps": <integer 1-1000>,
  "seed_content": "<initial post content>",
  "agent_groups": [
    {{ "name": "<group name>", "ratio": <0-1>, "stance_range": [<min>, <max>] }}
  ],
  "event_injections": [
    {{ "round": <integer>, "content": "<event description>" }}
  ],
  "available_actions": ["CREATE_POST", "COMMENT", "LIKE", "REPOST", "FOLLOW"],
  "dna": {{
    "conflict_level": <0-1>,
    "information_density": <0-1>,
    "viral_potential": <0-1>,
    "sentiment_polarity": <0-1>,
    "temporal_dynamics": "stable" | "escalation" | "decay" | "wave",
    "agent_diversity": <0-1>,
    "platform_fit": ["<platform>"]
  }},
  "description": "<brief summary of the scenario>"
}}

Rules:
- Infer reasonable defaults if the user doesn't specify everything
- Agent group ratios must sum to 1.0
- Event injection rounds must be within num_steps range
- Return ONLY valid JSON, no markdown or explanation"""


class ScenarioParser:
    def __init__(self, llm_call: Callable[[str], Awaitable[str]]):
        self._llm_call = llm_call

    async def parse(self, description: str) -> ScenarioConfig:
        prompt = PARSE_PROMPT.format(description=description)
        raw = await self._llm_call(prompt)

        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        data = json.loads(text)

        groups = [AgentGroup(**g) for g in data.get("agent_groups", [])]
        events = [EventInjection(**e) for e in data.get("event_injections", [])]
        dna = ScenarioDNA(**data["dna"]) if "dna" in data else None

        return ScenarioConfig(
            platform=data.get("platform", "twitter"),
            num_agents=data.get("num_agents", 50),
            num_steps=data.get("num_steps", 10),
            seed_content=data.get("seed_content", ""),
            agent_groups=groups,
            event_injections=events,
            available_actions=data.get("available_actions", ["CREATE_POST", "COMMENT", "LIKE", "REPOST", "FOLLOW"]),
            dna=dna,
            description=data.get("description", description),
        )
```

- [ ] **Step 3: Commit**

```bash
git add engine/composer/__init__.py engine/composer/schema.py engine/composer/parser.py
git commit -m "feat(composer): add scenario parser with LLM-based NL→config mapping"
```

---

### Task 2: Engine — DNA Mixer + Estimator (`engine/composer/mixer.py`, `engine/composer/estimator.py`)

**Files:**
- Create: `engine/composer/mixer.py`
- Create: `engine/composer/estimator.py`

- [ ] **Step 1: Create DNA mixer**

Create `engine/composer/mixer.py`:

```python
from __future__ import annotations

import json
import logging
from typing import Callable, Awaitable, Optional

from engine.composer.schema import ScenarioDNA, ScenarioConfig

logger = logging.getLogger("engine.composer.mixer")

MIX_PROMPT = """You are a social media simulation scenario designer. Two scenario DNAs have been mixed by weighted average. Based on the blended DNA values, generate a complete simulation configuration.

DNA A (weight {weight_a}):
{dna_a}

DNA B (weight {weight_b}):
{dna_b}

Blended DNA:
{blended}

Generate a JSON simulation config that matches this blended DNA profile:
{{
  "platform": "<best platform>",
  "num_agents": <integer>,
  "num_steps": <integer>,
  "seed_content": "<content matching the scenario>",
  "agent_groups": [{{ "name": "<name>", "ratio": <0-1>, "stance_range": [<min>, <max>] }}],
  "event_injections": [{{ "round": <int>, "content": "<event>" }}],
  "available_actions": ["CREATE_POST", "COMMENT", "LIKE", "REPOST", "FOLLOW"],
  "description": "<scenario description>"
}}

Return ONLY valid JSON."""


class DNAMixer:
    def __init__(self, llm_call: Optional[Callable[[str], Awaitable[str]]] = None):
        self._llm_call = llm_call

    def blend(self, dna_a: ScenarioDNA, dna_b: ScenarioDNA, weight_a: float = 0.5) -> ScenarioDNA:
        weight_b = 1.0 - weight_a
        platforms = list(set(dna_a.platform_fit + dna_b.platform_fit))

        dynamics_options = [dna_a.temporal_dynamics, dna_b.temporal_dynamics]
        temporal = dynamics_options[0] if weight_a >= 0.5 else dynamics_options[1]

        return ScenarioDNA(
            conflict_level=round(dna_a.conflict_level * weight_a + dna_b.conflict_level * weight_b, 3),
            information_density=round(dna_a.information_density * weight_a + dna_b.information_density * weight_b, 3),
            viral_potential=round(dna_a.viral_potential * weight_a + dna_b.viral_potential * weight_b, 3),
            sentiment_polarity=round(dna_a.sentiment_polarity * weight_a + dna_b.sentiment_polarity * weight_b, 3),
            temporal_dynamics=temporal,
            agent_diversity=round(dna_a.agent_diversity * weight_a + dna_b.agent_diversity * weight_b, 3),
            platform_fit=platforms,
        )

    async def mix_to_config(self, dna_a: ScenarioDNA, dna_b: ScenarioDNA, weight_a: float = 0.5) -> ScenarioConfig:
        if not self._llm_call:
            raise RuntimeError("LLM call required for mix_to_config")

        blended = self.blend(dna_a, dna_b, weight_a)
        weight_b = 1.0 - weight_a

        prompt = MIX_PROMPT.format(
            weight_a=weight_a, weight_b=weight_b,
            dna_a=dna_a.model_dump_json(indent=2),
            dna_b=dna_b.model_dump_json(indent=2),
            blended=blended.model_dump_json(indent=2),
        )

        raw = await self._llm_call(prompt)
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        data = json.loads(text)
        from engine.composer.schema import AgentGroup, EventInjection

        config = ScenarioConfig(
            platform=data.get("platform", blended.platform_fit[0] if blended.platform_fit else "twitter"),
            num_agents=data.get("num_agents", 50),
            num_steps=data.get("num_steps", 10),
            seed_content=data.get("seed_content", ""),
            agent_groups=[AgentGroup(**g) for g in data.get("agent_groups", [])],
            event_injections=[EventInjection(**e) for e in data.get("event_injections", [])],
            available_actions=data.get("available_actions", ["CREATE_POST", "COMMENT", "LIKE", "REPOST", "FOLLOW"]),
            dna=blended,
            description=data.get("description", ""),
        )
        return config
```

- [ ] **Step 2: Create resource estimator**

Create `engine/composer/estimator.py`:

```python
from __future__ import annotations

from engine.composer.schema import ScenarioConfig, ResourceEstimate


class ResourceEstimator:
    AVG_TOKENS_PER_CALL = 800
    AVG_SECONDS_PER_CALL = 2.0
    COST_PER_1K_TOKENS = 0.003

    def estimate(self, config: ScenarioConfig) -> ResourceEstimate:
        calls_per_step = config.num_agents
        total_calls = calls_per_step * config.num_steps
        total_tokens = total_calls * self.AVG_TOKENS_PER_CALL
        total_seconds = total_calls * self.AVG_SECONDS_PER_CALL
        total_cost = (total_tokens / 1000) * self.COST_PER_1K_TOKENS

        return ResourceEstimate(
            llm_calls=total_calls,
            estimated_tokens=total_tokens,
            estimated_minutes=round(total_seconds / 60, 1),
            estimated_cost_usd=round(total_cost, 2),
        )
```

- [ ] **Step 3: Update __init__.py and commit**

Update `engine/composer/__init__.py` to add new exports:

```python
from engine.composer.schema import ScenarioConfig, ScenarioDNA, ResourceEstimate
from engine.composer.parser import ScenarioParser
from engine.composer.mixer import DNAMixer
from engine.composer.estimator import ResourceEstimator

__all__ = ["ScenarioConfig", "ScenarioDNA", "ResourceEstimate", "ScenarioParser", "DNAMixer", "ResourceEstimator"]
```

```bash
git add engine/composer/mixer.py engine/composer/estimator.py engine/composer/__init__.py
git commit -m "feat(composer): add DNA mixer and resource estimator"
```

---

### Task 3: Engine — FastAPI Endpoints

**Files:**
- Modify: `engine/main.py` (add 4 endpoints + request models)

- [ ] **Step 1: Add request models to engine/main.py**

Add after `RoundtableRequest` class (around line 121):

```python
class ComposerParseRequest(BaseModel):
    description: str = Field(min_length=1, max_length=5000)


class ComposerMixRequest(BaseModel):
    dna_a: dict[str, Any]
    dna_b: dict[str, Any]
    weight_a: float = Field(default=0.5, ge=0.0, le=1.0)


class ComposerRecommendRequest(BaseModel):
    platform: Optional[str] = None
    type: Optional[str] = None


class ComposerEstimateRequest(BaseModel):
    config: dict[str, Any]
```

- [ ] **Step 2: Add 4 engine endpoints**

Add after the roundtable endpoint (end of file):

```python
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
async def composer_recommend(platform: Optional[str] = None, type: Optional[str] = None):
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
    if type:
        pass

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
```

- [ ] **Step 3: Commit**

```bash
git add engine/main.py
git commit -m "feat(composer): add 4 engine endpoints (parse/mix/recommend/estimate)"
```

---

### Task 4: Nuxt Server — 4 Proxy API Routes

**Files:**
- Create: `web/server/api/composer/parse.post.ts`
- Create: `web/server/api/composer/mix.post.ts`
- Create: `web/server/api/composer/recommend.get.ts`
- Create: `web/server/api/composer/estimate.post.ts`

- [ ] **Step 1: Create parse API route**

Create `web/server/api/composer/parse.post.ts`:

```typescript
import { z } from 'zod'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const schema = z.object({
  description: z.string().min(1).max(5000),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = schema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '请输入场景描述')

  const config = useRuntimeConfig()

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/composer/parse`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: { description: parsed.data.description },
    })
    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '场景解析失败: ' + (e.message || ''))
  }
})
```

- [ ] **Step 2: Create mix API route**

Create `web/server/api/composer/mix.post.ts`:

```typescript
import { z } from 'zod'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const schema = z.object({
  dna_a: z.record(z.string(), z.any()),
  dna_b: z.record(z.string(), z.any()),
  weight_a: z.number().min(0).max(1).default(0.5),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = schema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const config = useRuntimeConfig()

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/composer/mix`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: parsed.data,
    })
    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, 'DNA混合失败: ' + (e.message || ''))
  }
})
```

- [ ] **Step 3: Create recommend API route**

Create `web/server/api/composer/recommend.get.ts`:

```typescript
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const config = useRuntimeConfig()

  try {
    const params = new URLSearchParams()
    if (query.platform) params.set('platform', String(query.platform))
    if (query.type) params.set('type', String(query.type))

    const result = await $fetch<any>(`${config.engineUrl}/engine/composer/recommend?${params.toString()}`, {
      headers: { 'X-Internal-Key': config.internalApiKey },
    })
    return success(result.templates || [])
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '获取推荐场景失败: ' + (e.message || ''))
  }
})
```

- [ ] **Step 4: Create estimate API route**

Create `web/server/api/composer/estimate.post.ts`:

```typescript
import { z } from 'zod'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const schema = z.object({
  config: z.record(z.string(), z.any()),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = schema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const config = useRuntimeConfig()

  try {
    const result = await $fetch<any>(`${config.engineUrl}/engine/composer/estimate`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: { config: parsed.data.config },
    })
    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '资源估算失败: ' + (e.message || ''))
  }
})
```

- [ ] **Step 5: Commit**

```bash
git add web/server/api/composer/parse.post.ts web/server/api/composer/mix.post.ts web/server/api/composer/recommend.get.ts web/server/api/composer/estimate.post.ts
git commit -m "feat(composer): add 4 Nuxt server proxy API routes"
```

---

### Task 5: Frontend — Composer Store + i18n Keys

**Files:**
- Create: `web/app/stores/composer.ts`
- Modify: `web/locales/zh-CN.json`
- Modify: `web/locales/en-US.json`

- [ ] **Step 1: Create Pinia store**

Create `web/app/stores/composer.ts`:

```typescript
import { defineStore } from 'pinia'

export interface AgentGroup {
  name: string
  ratio: number
  stance_range: number[]
}

export interface EventInjection {
  round: number
  content: string
}

export interface ScenarioDNA {
  conflict_level: number
  information_density: number
  viral_potential: number
  sentiment_polarity: number
  temporal_dynamics: string
  agent_diversity: number
  platform_fit: string[]
}

export interface ScenarioConfig {
  platform: string
  num_agents: number
  num_steps: number
  seed_content: string
  agent_groups: AgentGroup[]
  event_injections: EventInjection[]
  available_actions: string[]
  dna: ScenarioDNA | null
  description: string
}

export interface ResourceEstimate {
  llm_calls: number
  estimated_tokens: number
  estimated_minutes: number
  estimated_cost_usd: number
}

interface ComposerState {
  config: ScenarioConfig | null
  estimate: ResourceEstimate | null
  templates: ScenarioConfig[]
  parsing: boolean
  mixing: boolean
  estimating: boolean
}

export const useComposerStore = defineStore('composer', {
  state: (): ComposerState => ({
    config: null,
    estimate: null,
    templates: [],
    parsing: false,
    mixing: false,
    estimating: false,
  }),

  actions: {
    async parse(description: string) {
      this.parsing = true
      try {
        const { $api } = useApi()
        const res = await $api<any>('/api/composer/parse', { method: 'POST', body: { description } })
        if (res.code === 0) {
          this.config = res.data
          return res.data
        }
        throw new Error(res.message)
      } finally {
        this.parsing = false
      }
    },

    async mix(dna_a: ScenarioDNA, dna_b: ScenarioDNA, weight_a: number = 0.5) {
      this.mixing = true
      try {
        const { $api } = useApi()
        const res = await $api<any>('/api/composer/mix', { method: 'POST', body: { dna_a, dna_b, weight_a } })
        if (res.code === 0) {
          this.config = res.data
          return res.data
        }
        throw new Error(res.message)
      } finally {
        this.mixing = false
      }
    },

    async fetchTemplates(platform?: string) {
      try {
        const { $api } = useApi()
        const query = platform ? `?platform=${platform}` : ''
        const res = await $api<any>(`/api/composer/recommend${query}`)
        if (res.code === 0) {
          this.templates = res.data
        }
      } catch {}
    },

    async fetchEstimate(config: ScenarioConfig) {
      this.estimating = true
      try {
        const { $api } = useApi()
        const res = await $api<any>('/api/composer/estimate', { method: 'POST', body: { config } })
        if (res.code === 0) {
          this.estimate = res.data
          return res.data
        }
        throw new Error(res.message)
      } finally {
        this.estimating = false
      }
    },

    updateConfig(partial: Partial<ScenarioConfig>) {
      if (this.config) {
        Object.assign(this.config, partial)
      }
    },

    reset() {
      this.config = null
      this.estimate = null
      this.parsing = false
      this.mixing = false
      this.estimating = false
    },
  },
})
```

- [ ] **Step 2: Add i18n keys to zh-CN.json**

Add a `"composer"` section to `web/locales/zh-CN.json`:

```json
"composer": {
  "title": "AI 场景编排",
  "subtitle": "用自然语言描述仿真场景，AI 自动生成配置",
  "inputPlaceholder": "描述你想要模拟的场景，例如：模拟一场关于新能源汽车补贴取消的微博舆论战，大约500个用户，持续3天...",
  "parseBtn": "AI 解析",
  "parsing": "正在解析场景...",
  "configGenerated": "场景配置已生成",
  "dnaTitle": "场景 DNA",
  "dnaConflict": "冲突强度",
  "dnaInfoDensity": "信息密度",
  "dnaViralPotential": "传播潜力",
  "dnaSentiment": "情感极性",
  "dnaTemporal": "时间动态",
  "dnaDiversity": "Agent 多样性",
  "dnaPlatformFit": "平台适配",
  "mixerTitle": "场景 DNA 混合器",
  "mixerWeight": "混合权重",
  "mixBtn": "混合",
  "mixing": "正在混合场景...",
  "sceneA": "场景 A",
  "sceneB": "场景 B",
  "agentGroups": "Agent 分组",
  "groupName": "分组名称",
  "groupRatio": "比例",
  "groupStance": "立场范围",
  "eventInjections": "事件注入",
  "eventRound": "轮次",
  "eventContent": "事件内容",
  "addEvent": "添加事件",
  "removeEvent": "移除",
  "estimateTitle": "资源估算",
  "llmCalls": "LLM 调用次数",
  "estimatedTokens": "预计 Token 消耗",
  "estimatedTime": "预计耗时",
  "estimatedCost": "预计费用",
  "minutes": "分钟",
  "useConfig": "使用此配置",
  "templateTitle": "推荐场景模板",
  "useTemplate": "使用模板",
  "manualMode": "手动配置",
  "aiMode": "AI 编排",
  "temporalStable": "稳定",
  "temporalEscalation": "升级",
  "temporalDecay": "衰退",
  "temporalWave": "波动"
}
```

- [ ] **Step 3: Add i18n keys to en-US.json**

Add a `"composer"` section to `web/locales/en-US.json`:

```json
"composer": {
  "title": "AI Scenario Composer",
  "subtitle": "Describe a simulation scenario in natural language, AI generates the config",
  "inputPlaceholder": "Describe the scenario you want to simulate, e.g.: Simulate a Twitter debate about electric vehicle subsidies with 500 users over 3 days...",
  "parseBtn": "AI Parse",
  "parsing": "Parsing scenario...",
  "configGenerated": "Scenario config generated",
  "dnaTitle": "Scenario DNA",
  "dnaConflict": "Conflict Level",
  "dnaInfoDensity": "Information Density",
  "dnaViralPotential": "Viral Potential",
  "dnaSentiment": "Sentiment Polarity",
  "dnaTemporal": "Temporal Dynamics",
  "dnaDiversity": "Agent Diversity",
  "dnaPlatformFit": "Platform Fit",
  "mixerTitle": "Scene DNA Mixer",
  "mixerWeight": "Mix Weight",
  "mixBtn": "Mix",
  "mixing": "Mixing scenarios...",
  "sceneA": "Scene A",
  "sceneB": "Scene B",
  "agentGroups": "Agent Groups",
  "groupName": "Group Name",
  "groupRatio": "Ratio",
  "groupStance": "Stance Range",
  "eventInjections": "Event Injections",
  "eventRound": "Round",
  "eventContent": "Event Content",
  "addEvent": "Add Event",
  "removeEvent": "Remove",
  "estimateTitle": "Resource Estimate",
  "llmCalls": "LLM Calls",
  "estimatedTokens": "Estimated Tokens",
  "estimatedTime": "Estimated Time",
  "estimatedCost": "Estimated Cost",
  "minutes": "minutes",
  "useConfig": "Use This Config",
  "templateTitle": "Recommended Templates",
  "useTemplate": "Use Template",
  "manualMode": "Manual Config",
  "aiMode": "AI Compose",
  "temporalStable": "Stable",
  "temporalEscalation": "Escalation",
  "temporalDecay": "Decay",
  "temporalWave": "Wave"
}
```

- [ ] **Step 4: Commit**

```bash
git add web/app/stores/composer.ts web/locales/zh-CN.json web/locales/en-US.json
git commit -m "feat(composer): add Pinia store and i18n keys"
```

---

### Task 6: Frontend — DNA Radar Chart + Parameter Panel Components

**Files:**
- Create: `web/app/components/composer/DNARadarChart.vue`
- Create: `web/app/components/composer/ParameterPanel.vue`

- [ ] **Step 1: Create DNA radar chart component**

Create `web/app/components/composer/DNARadarChart.vue`:

A Vue component using ECharts radar chart to display ScenarioDNA dimensions. Props: `dna: ScenarioDNA`, `editable: boolean`. When editable, emits `update:dna` on drag. Shows 6 dimensions: conflict_level, information_density, viral_potential, sentiment_polarity, agent_diversity, and a computed "overall" score. Uses `$t()` for all labels.

Key implementation:
- ECharts radar chart with `indicator` array from DNA dimension names
- Single series data from DNA values
- If `editable`, add click handler on radar points that opens an NSlider for adjustment
- Responsive sizing via ResizeObserver

- [ ] **Step 2: Create parameter tuning panel component**

Create `web/app/components/composer/ParameterPanel.vue`:

A Vue component for tuning ScenarioConfig parameters. Props: `config: ScenarioConfig`, `estimate: ResourceEstimate | null`. Emits: `update:config`, `request-estimate`.

Layout:
- Top row: NSlider for num_agents (1-100000), NSlider for num_steps (1-1000)
- Middle: Agent group pie chart (ECharts) showing group ratios, editable via NInputNumber
- Bottom left: Event injection timeline — list of events with round number + content, add/remove buttons
- Bottom right: Resource estimate card showing llm_calls, tokens, time, cost
- All labels use `$t()` from composer i18n keys

- [ ] **Step 3: Commit**

```bash
git add web/app/components/composer/DNARadarChart.vue web/app/components/composer/ParameterPanel.vue
git commit -m "feat(composer): add DNA radar chart and parameter panel components"
```

---

### Task 7: Frontend — DNA Mixer Component

**Files:**
- Create: `web/app/components/composer/DNAMixer.vue`

- [ ] **Step 1: Create DNA mixer component**

Create `web/app/components/composer/DNAMixer.vue`:

A Vue component for mixing two scenario DNAs. Shows two side-by-side DNA radar charts (Scene A and Scene B), a weight slider in the middle, and a "Mix" button. Below, shows the blended result radar chart.

Props: `templates: ScenarioConfig[]`. Emits: `mixed(config: ScenarioConfig)`.

Implementation:
- Two NSelect dropdowns to pick templates for Scene A and Scene B
- NSlider for weight_a (0.0 to 1.0, step 0.05) with labels showing "A: 70% / B: 30%"
- Two small DNARadarChart instances (readonly) showing each scene's DNA
- Mix button calls composerStore.mix()
- Result preview below showing blended DNA radar + generated config summary
- All labels use `$t()`

- [ ] **Step 2: Commit**

```bash
git add web/app/components/composer/DNAMixer.vue
git commit -m "feat(composer): add DNA mixer component"
```

---

### Task 8: Frontend — Enhance Simulation Create Page with AI Mode

**Files:**
- Modify: `web/app/pages/simulations/create.vue`

- [ ] **Step 1: Add AI mode tab to create page**

Modify `web/app/pages/simulations/create.vue` to add an NTabs component at the top switching between "Manual Config" (`manualMode`) and "AI Compose" (`aiMode`).

Manual mode: existing wizard (Steps 1-3) — no changes needed.

AI mode content:
1. **NInput textarea** for natural language description with "AI Parse" button
2. On parse success, show generated config with:
   - `DNARadarChart` component (editable)
   - `ParameterPanel` component (with estimate request)
   - Agent groups table
   - Event injection list
3. **Template recommendations** — show `DNAMixer` for mixing templates
4. "Use This Config" button that maps the ScenarioConfig to the existing form fields and switches to Step 3 (confirm)

Key integration:
- Import `useComposerStore` and composer components
- Map `ScenarioConfig` → existing `form` reactive: `form.platform = config.platform`, `form.agentCount = config.num_agents`, etc.
- Store seed_content, agent_groups, event_injections in form for submission
- The existing `handleSubmit` already passes these to the API

- [ ] **Step 2: Commit**

```bash
git add web/app/pages/simulations/create.vue
git commit -m "feat(composer): add AI compose mode to simulation create page"
```

---

### Task 9: Integration — Wire Up Submission with Composer Config

**Files:**
- Modify: `web/app/pages/simulations/create.vue` (if not done in Task 8)

- [ ] **Step 1: Ensure composer config maps to submission**

When user clicks "Use This Config" from AI mode:
- Map all ScenarioConfig fields to form reactive
- Add `agentDistribution` (from agent_groups) and `eventInjections` to the config object sent in `handleSubmit`
- The existing `index.post.ts` already accepts a `config: z.record()` field that passes through to fullConfig

Verify the flow: AI parse → config displayed → user tunes → "Use Config" → confirm step → submit → engine receives full config including groups + events.

- [ ] **Step 2: Commit if changes needed**

```bash
git add web/app/pages/simulations/create.vue
git commit -m "feat(composer): wire up AI compose config to simulation submission"
```
