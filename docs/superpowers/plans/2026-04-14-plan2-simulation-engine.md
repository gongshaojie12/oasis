# Plan 2: Simulation Engine (FastAPI Service)

## Overview

This plan creates a FastAPI service (`engine/`) that wraps the existing OASIS core engine (`oasis/`). The service receives simulation tasks from the Nuxt web API, manages a task queue via `asyncio.Queue`, runs simulations through OASIS core Python imports, and reports progress back to Nuxt via HTTP callbacks. It includes multi-LLM provider management (7 providers, all OpenAI-compatible) and cost-tiered agent assignment (core/normal/background).

**Important constraint:** The `oasis/` source code is never modified. The engine calls OASIS via Python imports (`from oasis.environment.make import make`, etc.) -- no subprocesses.

## Directory Structure

```
engine/
  main.py              # FastAPI app, endpoints
  config.py            # Environment config (pydantic-settings)
  queue.py             # Task queue manager (asyncio.Queue)
  runner.py            # Simulation runner (wraps OasisEnv)
  reporter.py          # Progress/result reporter (callbacks to Nuxt)
  callback.py          # HTTP callback client
  llm/
    __init__.py
    provider.py        # LLM provider registry
    tiered.py          # Cost-tiered model assignment
  platforms/
    __init__.py        # Platform registry (will be extended in Plan 3)
  tests/
    test_config.py
    test_queue.py
    test_llm.py
    test_runner.py
  requirements.txt
  .env.example
```

---

## Task 1: FastAPI Project Setup

**Goal:** Create the project skeleton, `requirements.txt`, a minimal `main.py` with a health endpoint, and `.env.example`.

**Estimated time:** 5 minutes

### Step 1.1: Create directory structure

```bash
mkdir -p engine/llm engine/platforms engine/tests
touch engine/llm/__init__.py engine/platforms/__init__.py engine/tests/__init__.py
```

### Step 1.2: Create `engine/requirements.txt`

**File:** `engine/requirements.txt`

```txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic-settings==2.7.1
httpx==0.28.1
pytest==8.3.4
pytest-asyncio==0.25.0
```

### Step 1.3: Create `engine/.env.example`

**File:** `engine/.env.example`

```env
# === Nuxt Callback ===
NUXT_CALLBACK_URL=http://localhost:3000
INTERNAL_API_KEY=change-me-to-a-random-secret

# === Task Queue ===
MAX_CONCURRENT_TASKS=2

# === Default LLM ===
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat

# === LLM Provider API Keys ===
DEEPSEEK_API_KEY=
QWEN_API_KEY=
DOUBAO_API_KEY=
MINIMAX_API_KEY=
ZHIPU_API_KEY=
KIMI_API_KEY=
OPENAI_API_KEY=
```

### Step 1.4: Create `engine/main.py`

**File:** `engine/main.py`

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from engine.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    yield


app = FastAPI(
    title="OASIS Simulation Engine",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/engine/health")
async def health():
    return {"status": "ok", "service": "oasis-engine"}
```

### Step 1.5: Create a minimal `engine/config.py` placeholder

This will be fully implemented in Task 2, but we need it to exist so `main.py` imports succeed.

**File:** `engine/config.py`

```python
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    nuxt_callback_url: str = "http://localhost:3000"
    internal_api_key: str = "change-me-to-a-random-secret"
    max_concurrent_tasks: int = 2
    default_llm_provider: str = "deepseek"
    default_llm_model: str = "deepseek-chat"

    model_config = {"env_file": "engine/.env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### Step 1.6: Verify the health endpoint

```bash
cd D:/project/oasis
pip install -r engine/requirements.txt
python -m pytest engine/tests/ -x -q  # no tests yet, just verify import
uvicorn engine.main:app --host 0.0.0.0 --port 8100 &
curl http://localhost:8100/engine/health
# Expected: {"status":"ok","service":"oasis-engine"}
kill %1
```

### Step 1.7: Commit

```bash
git add engine/
git commit -m "feat(engine): scaffold FastAPI project with health endpoint

Create engine/ directory structure with main.py, config.py,
requirements.txt, and .env.example. Health endpoint at /engine/health."
```

---

## Task 2: Configuration Module

**Goal:** Full Pydantic Settings config with all environment variables, including per-provider API keys.

**Estimated time:** 5 minutes

### Step 2.1: Implement `engine/config.py`

**File:** `engine/config.py`

```python
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Nuxt callback
    nuxt_callback_url: str = "http://localhost:3000"
    internal_api_key: str = "change-me-to-a-random-secret"

    # Task queue
    max_concurrent_tasks: int = 2

    # Default LLM
    default_llm_provider: str = "deepseek"
    default_llm_model: str = "deepseek-chat"

    # LLM provider API keys
    deepseek_api_key: Optional[str] = None
    qwen_api_key: Optional[str] = None
    doubao_api_key: Optional[str] = None
    minimax_api_key: Optional[str] = None
    zhipu_api_key: Optional[str] = None
    kimi_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    model_config = {
        "env_file": "engine/.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### Step 2.2: Create `engine/tests/test_config.py`

**File:** `engine/tests/test_config.py`

```python
import os

import pytest

from engine.config import Settings


class TestSettings:
    def test_default_values(self):
        settings = Settings(
            _env_file=None,
        )
        assert settings.nuxt_callback_url == "http://localhost:3000"
        assert settings.internal_api_key == "change-me-to-a-random-secret"
        assert settings.max_concurrent_tasks == 2
        assert settings.default_llm_provider == "deepseek"
        assert settings.default_llm_model == "deepseek-chat"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("NUXT_CALLBACK_URL", "http://nuxt:4000")
        monkeypatch.setenv("MAX_CONCURRENT_TASKS", "5")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
        settings = Settings(_env_file=None)
        assert settings.nuxt_callback_url == "http://nuxt:4000"
        assert settings.max_concurrent_tasks == 5
        assert settings.deepseek_api_key == "sk-test-key"

    def test_optional_api_keys_default_none(self):
        settings = Settings(_env_file=None)
        assert settings.deepseek_api_key is None
        assert settings.qwen_api_key is None
        assert settings.doubao_api_key is None
        assert settings.minimax_api_key is None
        assert settings.zhipu_api_key is None
        assert settings.kimi_api_key is None
        assert settings.openai_api_key is None
```

### Step 2.3: Run tests

```bash
cd D:/project/oasis
python -m pytest engine/tests/test_config.py -v
```

### Step 2.4: Commit

```bash
git add engine/config.py engine/tests/test_config.py
git commit -m "feat(engine): implement configuration module with pydantic-settings

Full Settings class with Nuxt callback URL, task queue concurrency,
default LLM provider/model, and per-provider API keys. Includes tests."
```

---

## Task 3: LLM Provider Registry

**Goal:** Create a provider registry that maps provider names to their `base_url` and supported models. Provide a factory function that creates CAMEL `BaseModelBackend` instances using `ModelFactory.create()` with the OpenAI-compatible platform type.

**Estimated time:** 5 minutes

### Step 3.1: Implement `engine/llm/__init__.py`

**File:** `engine/llm/__init__.py`

```python
from engine.llm.provider import LLMProviderRegistry, create_model
from engine.llm.tiered import TieredModelAssigner, AgentTier

__all__ = [
    "LLMProviderRegistry",
    "create_model",
    "TieredModelAssigner",
    "AgentTier",
]
```

### Step 3.2: Implement `engine/llm/provider.py`

**File:** `engine/llm/provider.py`

```python
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

from engine.config import Settings


@dataclass(frozen=True)
class ProviderSpec:
    """Specification for a single LLM provider."""

    name: str
    base_url: str
    models: list[str]
    api_key_env: str
    platform_type: ModelPlatformType


# All 7 providers with their OpenAI-compatible endpoints.
_BUILTIN_PROVIDERS: list[ProviderSpec] = [
    ProviderSpec(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        models=["deepseek-chat", "deepseek-reasoner"],
        api_key_env="DEEPSEEK_API_KEY",
        platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    ),
    ProviderSpec(
        name="qwen",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        models=["qwen-plus", "qwen-max", "qwen-turbo"],
        api_key_env="QWEN_API_KEY",
        platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    ),
    ProviderSpec(
        name="doubao",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        models=["doubao-1-5-pro-256k", "doubao-1-5-lite-32k"],
        api_key_env="DOUBAO_API_KEY",
        platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    ),
    ProviderSpec(
        name="minimax",
        base_url="https://api.minimax.chat/v1",
        models=["MiniMax-Text-01", "abab6.5s"],
        api_key_env="MINIMAX_API_KEY",
        platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    ),
    ProviderSpec(
        name="zhipu",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        models=["glm-4-plus", "glm-4-flash"],
        api_key_env="ZHIPU_API_KEY",
        platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    ),
    ProviderSpec(
        name="kimi",
        base_url="https://api.moonshot.cn/v1",
        models=["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        api_key_env="KIMI_API_KEY",
        platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    ),
    ProviderSpec(
        name="openai",
        base_url="https://api.openai.com/v1",
        models=["gpt-4o", "gpt-4o-mini"],
        api_key_env="OPENAI_API_KEY",
        platform_type=ModelPlatformType.OPENAI,
    ),
]


class LLMProviderRegistry:
    """Registry of LLM providers and their configurations."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderSpec] = {}
        for spec in _BUILTIN_PROVIDERS:
            self._providers[spec.name] = spec

    def get(self, name: str) -> ProviderSpec:
        """Return the ProviderSpec for *name*, or raise KeyError."""
        if name not in self._providers:
            available = ", ".join(sorted(self._providers.keys()))
            raise KeyError(
                f"Unknown LLM provider '{name}'. Available: {available}"
            )
        return self._providers[name]

    def list_providers(self) -> list[str]:
        """Return sorted list of registered provider names."""
        return sorted(self._providers.keys())

    def list_models(self, provider_name: str) -> list[str]:
        """Return the models supported by a provider."""
        return list(self.get(provider_name).models)

    def register(self, spec: ProviderSpec) -> None:
        """Register a custom provider (or override a built-in one)."""
        self._providers[spec.name] = spec


def create_model(
    provider_name: str,
    model_id: str,
    settings: Settings,
    registry: Optional[LLMProviderRegistry] = None,
):
    """Create a CAMEL BaseModelBackend for the given provider and model.

    Args:
        provider_name: e.g. "deepseek", "qwen", "openai".
        model_id: e.g. "deepseek-chat", "gpt-4o-mini".
        settings: Application settings (carries API keys).
        registry: Provider registry.  Uses a default if None.

    Returns:
        A CAMEL BaseModelBackend instance ready for agent use.
    """
    if registry is None:
        registry = LLMProviderRegistry()

    spec = registry.get(provider_name)

    if model_id not in spec.models:
        raise ValueError(
            f"Model '{model_id}' is not registered for provider "
            f"'{provider_name}'. Available: {spec.models}"
        )

    # Resolve the API key from settings
    api_key = getattr(settings, spec.api_key_env.lower(), None)
    if not api_key:
        raise ValueError(
            f"API key for provider '{provider_name}' is not configured. "
            f"Set the {spec.api_key_env} environment variable."
        )

    # For the native OpenAI provider, use CAMEL's built-in OpenAI platform
    if spec.platform_type == ModelPlatformType.OPENAI:
        model_type = _resolve_openai_model_type(model_id)
        os.environ["OPENAI_API_KEY"] = api_key
        return ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=model_type,
        )

    # For all OpenAI-compatible providers, use the compatible model platform
    os.environ["OPENAI_COMPATIBILIY_API_KEY"] = api_key
    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
        model_type=model_id,
        api_key=api_key,
        url=spec.base_url,
        model_config_dict={"max_tokens": 4096},
    )


def _resolve_openai_model_type(model_id: str) -> ModelType:
    """Map a model ID string to a CAMEL ModelType enum for OpenAI models."""
    _mapping = {
        "gpt-4o": ModelType.GPT_4O,
        "gpt-4o-mini": ModelType.GPT_4O_MINI,
    }
    if model_id not in _mapping:
        raise ValueError(
            f"Unknown OpenAI model '{model_id}'. "
            f"Supported: {list(_mapping.keys())}"
        )
    return _mapping[model_id]
```

### Step 3.3: Create `engine/tests/test_llm.py`

**File:** `engine/tests/test_llm.py`

```python
import pytest

from engine.config import Settings
from engine.llm.provider import (
    LLMProviderRegistry,
    ProviderSpec,
    create_model,
    _resolve_openai_model_type,
)
from camel.types import ModelPlatformType, ModelType


class TestLLMProviderRegistry:
    def setup_method(self):
        self.registry = LLMProviderRegistry()

    def test_builtin_providers_registered(self):
        providers = self.registry.list_providers()
        assert "deepseek" in providers
        assert "qwen" in providers
        assert "doubao" in providers
        assert "minimax" in providers
        assert "zhipu" in providers
        assert "kimi" in providers
        assert "openai" in providers
        assert len(providers) == 7

    def test_get_existing_provider(self):
        spec = self.registry.get("deepseek")
        assert spec.name == "deepseek"
        assert spec.base_url == "https://api.deepseek.com/v1"
        assert "deepseek-chat" in spec.models

    def test_get_unknown_provider_raises(self):
        with pytest.raises(KeyError, match="Unknown LLM provider 'nonexistent'"):
            self.registry.get("nonexistent")

    def test_list_models(self):
        models = self.registry.list_models("qwen")
        assert "qwen-plus" in models
        assert "qwen-max" in models
        assert "qwen-turbo" in models

    def test_register_custom_provider(self):
        custom = ProviderSpec(
            name="custom-llm",
            base_url="https://custom.example.com/v1",
            models=["custom-model-1"],
            api_key_env="CUSTOM_API_KEY",
            platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
        )
        self.registry.register(custom)
        assert "custom-llm" in self.registry.list_providers()
        assert self.registry.get("custom-llm").base_url == "https://custom.example.com/v1"


class TestResolveOpenAIModelType:
    def test_gpt_4o(self):
        assert _resolve_openai_model_type("gpt-4o") == ModelType.GPT_4O

    def test_gpt_4o_mini(self):
        assert _resolve_openai_model_type("gpt-4o-mini") == ModelType.GPT_4O_MINI

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown OpenAI model"):
            _resolve_openai_model_type("gpt-99")


class TestCreateModel:
    def test_missing_api_key_raises(self):
        settings = Settings(_env_file=None)
        with pytest.raises(ValueError, match="API key for provider 'deepseek' is not configured"):
            create_model("deepseek", "deepseek-chat", settings)

    def test_invalid_model_for_provider_raises(self):
        settings = Settings(_env_file=None, deepseek_api_key="sk-test")
        with pytest.raises(ValueError, match="not registered for provider"):
            create_model("deepseek", "nonexistent-model", settings)

    def test_unknown_provider_raises(self):
        settings = Settings(_env_file=None)
        with pytest.raises(KeyError, match="Unknown LLM provider"):
            create_model("nonexistent", "some-model", settings)
```

### Step 3.4: Run tests

```bash
cd D:/project/oasis
python -m pytest engine/tests/test_llm.py -v
```

### Step 3.5: Commit

```bash
git add engine/llm/ engine/tests/test_llm.py
git commit -m "feat(engine): add LLM provider registry with 7 built-in providers

Registry maps provider names to base_url, models, and API key env vars.
Factory function creates CAMEL BaseModelBackend instances. Supports
DeepSeek, Qwen, Doubao, MiniMax, Zhipu, Kimi, and OpenAI."
```

---

## Task 4: Cost-Tiered Model Assignment

**Goal:** Assign LLM models to agents based on their tier (core/normal/background) using configurable percentages and model mappings.

**Estimated time:** 5 minutes

### Step 4.1: Implement `engine/llm/tiered.py`

**File:** `engine/llm/tiered.py`

```python
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from camel.models import BaseModelBackend

from engine.config import Settings
from engine.llm.provider import LLMProviderRegistry, create_model


class AgentTier(str, Enum):
    """Cost tier for agent LLM assignment."""

    CORE = "core"
    NORMAL = "normal"
    BACKGROUND = "background"


@dataclass
class TierConfig:
    """Configuration for a single agent tier."""

    tier: AgentTier
    percentage: float  # 0.0 to 1.0
    provider: str
    model: str


DEFAULT_TIER_CONFIGS: list[TierConfig] = [
    TierConfig(
        tier=AgentTier.CORE,
        percentage=0.10,
        provider="qwen",
        model="qwen-max",
    ),
    TierConfig(
        tier=AgentTier.NORMAL,
        percentage=0.25,
        provider="deepseek",
        model="deepseek-chat",
    ),
    TierConfig(
        tier=AgentTier.BACKGROUND,
        percentage=0.65,
        provider="zhipu",
        model="glm-4-flash",
    ),
]


class TieredModelAssigner:
    """Assigns LLM models to agents based on cost tiers.

    Given a total number of agents, splits them into core (KOL),
    normal (active), and background (silent) tiers, then creates
    appropriate model backends for each tier.
    """

    def __init__(
        self,
        settings: Settings,
        tier_configs: Optional[list[TierConfig]] = None,
        registry: Optional[LLMProviderRegistry] = None,
        seed: int = 42,
    ) -> None:
        self._settings = settings
        self._tier_configs = tier_configs or DEFAULT_TIER_CONFIGS
        self._registry = registry or LLMProviderRegistry()
        self._rng = random.Random(seed)
        self._model_cache: dict[tuple[str, str], BaseModelBackend] = {}

    def _get_or_create_model(
        self, provider: str, model_id: str
    ) -> BaseModelBackend:
        """Return a cached model or create a new one."""
        cache_key = (provider, model_id)
        if cache_key not in self._model_cache:
            self._model_cache[cache_key] = create_model(
                provider_name=provider,
                model_id=model_id,
                settings=self._settings,
                registry=self._registry,
            )
        return self._model_cache[cache_key]

    def assign_tiers(self, num_agents: int) -> dict[int, AgentTier]:
        """Assign a tier to each agent index.

        Agents are shuffled and then partitioned sequentially according
        to configured percentages.  Returns a mapping from agent_id to tier.
        """
        agent_ids = list(range(num_agents))
        self._rng.shuffle(agent_ids)

        assignments: dict[int, AgentTier] = {}
        offset = 0
        for i, tc in enumerate(self._tier_configs):
            if i == len(self._tier_configs) - 1:
                # Last tier gets all remaining agents
                count = num_agents - offset
            else:
                count = round(tc.percentage * num_agents)
            for agent_id in agent_ids[offset : offset + count]:
                assignments[agent_id] = tc.tier
            offset += count

        return assignments

    def get_model_for_tier(self, tier: AgentTier) -> BaseModelBackend:
        """Return the LLM model backend for the given tier."""
        for tc in self._tier_configs:
            if tc.tier == tier:
                return self._get_or_create_model(tc.provider, tc.model)
        raise ValueError(f"No configuration found for tier '{tier.value}'")

    def assign_models(
        self, num_agents: int
    ) -> dict[int, tuple[AgentTier, BaseModelBackend]]:
        """Assign both a tier and a model to each agent.

        Returns a mapping from agent_id to (tier, model).
        """
        tier_map = self.assign_tiers(num_agents)
        result: dict[int, tuple[AgentTier, BaseModelBackend]] = {}
        for agent_id, tier in tier_map.items():
            model = self.get_model_for_tier(tier)
            result[agent_id] = (tier, model)
        return result

    def get_tier_summary(self, num_agents: int) -> dict[str, int]:
        """Return a count of agents in each tier for diagnostics."""
        tier_map = self.assign_tiers(num_agents)
        summary: dict[str, int] = {}
        for tier in AgentTier:
            summary[tier.value] = sum(
                1 for t in tier_map.values() if t == tier
            )
        return summary
```

### Step 4.2: Add tiered assignment tests to `engine/tests/test_llm.py`

Append to **File:** `engine/tests/test_llm.py`

```python
from engine.llm.tiered import AgentTier, TierConfig, TieredModelAssigner


class TestTieredModelAssigner:
    def test_assign_tiers_covers_all_agents(self):
        settings = Settings(_env_file=None)
        assigner = TieredModelAssigner(settings=settings)
        assignments = assigner.assign_tiers(100)
        assert len(assignments) == 100
        assert set(assignments.keys()) == set(range(100))

    def test_assign_tiers_distribution(self):
        settings = Settings(_env_file=None)
        assigner = TieredModelAssigner(settings=settings, seed=123)
        assignments = assigner.assign_tiers(100)
        core_count = sum(1 for t in assignments.values() if t == AgentTier.CORE)
        normal_count = sum(1 for t in assignments.values() if t == AgentTier.NORMAL)
        bg_count = sum(1 for t in assignments.values() if t == AgentTier.BACKGROUND)
        assert core_count == 10
        assert normal_count == 25
        assert bg_count == 65
        assert core_count + normal_count + bg_count == 100

    def test_assign_tiers_small_count(self):
        settings = Settings(_env_file=None)
        assigner = TieredModelAssigner(settings=settings)
        assignments = assigner.assign_tiers(3)
        assert len(assignments) == 3
        all_tiers = set(assignments.values())
        assert len(all_tiers) >= 1  # at least one tier assigned

    def test_assign_tiers_single_agent(self):
        settings = Settings(_env_file=None)
        assigner = TieredModelAssigner(settings=settings)
        assignments = assigner.assign_tiers(1)
        assert len(assignments) == 1
        assert 0 in assignments

    def test_assign_tiers_deterministic_with_same_seed(self):
        settings = Settings(_env_file=None)
        a1 = TieredModelAssigner(settings=settings, seed=99).assign_tiers(50)
        a2 = TieredModelAssigner(settings=settings, seed=99).assign_tiers(50)
        assert a1 == a2

    def test_tier_summary(self):
        settings = Settings(_env_file=None)
        assigner = TieredModelAssigner(settings=settings)
        summary = assigner.get_tier_summary(100)
        assert "core" in summary
        assert "normal" in summary
        assert "background" in summary
        assert summary["core"] + summary["normal"] + summary["background"] == 100

    def test_get_model_for_unknown_tier_raises(self):
        settings = Settings(_env_file=None)
        assigner = TieredModelAssigner(
            settings=settings,
            tier_configs=[],
        )
        with pytest.raises(ValueError, match="No configuration found"):
            assigner.get_model_for_tier(AgentTier.CORE)
```

### Step 4.3: Run tests

```bash
cd D:/project/oasis
python -m pytest engine/tests/test_llm.py -v
```

### Step 4.4: Commit

```bash
git add engine/llm/tiered.py engine/tests/test_llm.py
git commit -m "feat(engine): add cost-tiered model assignment for agents

TieredModelAssigner splits agents into core (10%), normal (25%), and
background (65%) tiers. Each tier maps to a specific LLM provider/model.
Deterministic assignment via configurable seed."
```

---

## Task 5: Task Queue Manager

**Goal:** Build an `asyncio.Queue`-based task queue with concurrency control, task lifecycle tracking, and cancellation support.

**Estimated time:** 5 minutes

### Step 5.1: Implement `engine/queue.py`

**File:** `engine/queue.py`

```python
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
```

### Step 5.2: Create `engine/tests/test_queue.py`

**File:** `engine/tests/test_queue.py`

```python
import asyncio

import pytest
import pytest_asyncio

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
```

### Step 5.3: Run tests

```bash
cd D:/project/oasis
python -m pytest engine/tests/test_queue.py -v
```

### Step 5.4: Commit

```bash
git add engine/queue.py engine/tests/test_queue.py
git commit -m "feat(engine): add asyncio task queue with concurrency control

TaskQueueManager with asyncio.Queue, Semaphore-based concurrency limit,
task lifecycle tracking (pending/running/completed/failed/cancelled),
and cancellation support."
```

---

## Task 6: HTTP Callback Client

**Goal:** Create an HTTP client that sends progress, completion, and error callbacks to the Nuxt API with retry logic.

**Estimated time:** 5 minutes

### Step 6.1: Implement `engine/callback.py`

**File:** `engine/callback.py`

```python
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger("engine.callback")

_DEFAULT_TIMEOUT = 10.0
_MAX_RETRIES = 3


class CallbackClient:
    """HTTP client that posts updates back to the Nuxt API.

    Endpoints:
        POST {base_url}/api/internal/progress   - step progress
        POST {base_url}/api/internal/complete    - simulation done
        POST {base_url}/api/internal/error       - simulation failed
    """

    def __init__(
        self,
        base_url: str,
        internal_api_key: str,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Content-Type": "application/json",
            "X-Internal-Key": internal_api_key,
        }
        self._timeout = timeout
        self._max_retries = max_retries

    async def _post(self, path: str, body: dict[str, Any]) -> bool:
        """POST to the given path with retry logic.

        Returns True if any attempt succeeded, False if all attempts failed.
        """
        url = f"{self._base_url}{path}"
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        url, json=body, headers=self._headers
                    )
                    if resp.status_code < 400:
                        logger.debug(
                            "Callback %s succeeded (attempt %d)", path, attempt
                        )
                        return True
                    logger.warning(
                        "Callback %s returned %d (attempt %d/%d)",
                        path,
                        resp.status_code,
                        attempt,
                        self._max_retries,
                    )
            except httpx.HTTPError as exc:
                logger.warning(
                    "Callback %s failed (attempt %d/%d): %s",
                    path,
                    attempt,
                    self._max_retries,
                    exc,
                )
        logger.error(
            "Callback %s failed after %d attempts", path, self._max_retries
        )
        return False

    async def send_progress(
        self,
        task_id: str,
        current_step: int,
        total_steps: int,
        progress: float,
        data: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Report step-level progress to Nuxt."""
        body: dict[str, Any] = {
            "task_id": task_id,
            "current_step": current_step,
            "total_steps": total_steps,
            "progress": round(progress, 4),
        }
        if data:
            body["data"] = data
        return await self._post("/api/internal/progress", body)

    async def send_complete(
        self,
        task_id: str,
        result: dict[str, Any],
    ) -> bool:
        """Report successful simulation completion to Nuxt."""
        body = {
            "task_id": task_id,
            "result": result,
        }
        return await self._post("/api/internal/complete", body)

    async def send_error(
        self,
        task_id: str,
        error: str,
    ) -> bool:
        """Report simulation failure to Nuxt."""
        body = {
            "task_id": task_id,
            "error": error,
        }
        return await self._post("/api/internal/error", body)
```

### Step 6.2: Implement `engine/reporter.py`

**File:** `engine/reporter.py`

```python
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
```

### Step 6.3: Verify (no separate test file -- tested via integration tests in Task 9)

The callback client is primarily tested through integration tests because it makes real HTTP calls. However, we verify the module imports cleanly:

```bash
cd D:/project/oasis
python -c "from engine.callback import CallbackClient; from engine.reporter import ProgressReporter; print('OK')"
```

### Step 6.4: Commit

```bash
git add engine/callback.py engine/reporter.py
git commit -m "feat(engine): add HTTP callback client and progress reporter

CallbackClient sends progress/complete/error POSTs to Nuxt with retry
logic and X-Internal-Key auth. ProgressReporter bridges the simulation
runner and callback client, updating TaskInfo in-place."
```

---

## Task 7: Simulation Runner

**Goal:** Create the simulation runner that wraps OasisEnv -- creates agents with tiered models, runs simulation steps, and reports progress after each step.

**Estimated time:** 5 minutes

### Step 7.1: Implement `engine/runner.py`

**File:** `engine/runner.py`

```python
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import Any, Optional

from engine.callback import CallbackClient
from engine.config import Settings
from engine.llm.provider import LLMProviderRegistry, create_model
from engine.llm.tiered import AgentTier, TieredModelAssigner
from engine.queue import TaskInfo
from engine.reporter import ProgressReporter

logger = logging.getLogger("engine.runner")


class SimulationRunner:
    """Wraps OASIS core to run a full simulation lifecycle.

    Responsibilities:
        1. Build an AgentGraph with tiered LLM models.
        2. Create an OasisEnv and reset it.
        3. Execute N simulation steps, reporting progress per step.
        4. Close the environment and return results.
    """

    def __init__(
        self,
        settings: Settings,
        reporter: ProgressReporter,
        registry: Optional[LLMProviderRegistry] = None,
    ) -> None:
        self._settings = settings
        self._reporter = reporter
        self._registry = registry or LLMProviderRegistry()

    async def run(self, task_info: TaskInfo, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a simulation task end-to-end.

        Expected params:
            platform_type: str  - "twitter" or "reddit" (default "reddit")
            num_steps: int      - number of simulation steps (default 5)
            num_agents: int     - number of agents (default 10)
            agent_profiles: list[dict] | None - custom agent profiles
            profile_path: str | None - path to agent profile JSON/CSV file
            seed_content: str | None - initial post content for step 0
            available_actions: list[str] | None - action types to enable
            tier_config: dict | None - override tier percentages/models
            llm_provider: str | None - override default LLM provider
            llm_model: str | None - override default LLM model

        Returns:
            dict with db_path, num_steps_completed, and agent summary.
        """
        # Lazy import to avoid importing oasis at module level (so tests
        # that mock oasis can control the import).
        import oasis
        from oasis import (
            ActionType,
            AgentGraph,
            DefaultPlatformType,
            LLMAction,
            ManualAction,
            SocialAgent,
            UserInfo,
            generate_reddit_agent_graph,
        )

        platform_type_str = params.get("platform_type", "reddit")
        num_steps = params.get("num_steps", 5)
        num_agents = params.get("num_agents", 10)
        profile_path = params.get("profile_path")
        agent_profiles = params.get("agent_profiles")
        seed_content = params.get("seed_content")
        llm_provider = params.get("llm_provider", self._settings.default_llm_provider)
        llm_model = params.get("llm_model", self._settings.default_llm_model)

        # Resolve platform type
        if platform_type_str == "twitter":
            platform_enum = DefaultPlatformType.TWITTER
            recsys_type = "twitter"
            default_actions = ActionType.get_default_twitter_actions()
        else:
            platform_enum = DefaultPlatformType.REDDIT
            recsys_type = "reddit"
            default_actions = ActionType.get_default_reddit_actions()

        # Resolve available actions
        action_names = params.get("available_actions")
        if action_names:
            available_actions = [ActionType(name) for name in action_names]
        else:
            available_actions = default_actions

        # Total steps = 1 (setup) + num_steps (simulation) + 1 (cleanup)
        total_progress_steps = num_steps + 2

        # --- Step 0: Setup ---
        await self._reporter.report_progress(
            task_info, current_step=0, total_steps=total_progress_steps,
            data={"phase": "setup"},
        )

        # Create a temporary database file
        db_dir = os.path.join(tempfile.gettempdir(), "oasis_simulations")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, f"{task_info.task_id}.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        os.environ["OASIS_DB_PATH"] = os.path.abspath(db_path)

        # Build models via tiered assignment
        tiered_assigner = self._build_tiered_assigner(params)

        # Build agent graph
        if profile_path:
            # Use existing profile file
            if profile_path.endswith(".json"):
                default_model = create_model(
                    llm_provider, llm_model, self._settings, self._registry,
                )
                agent_graph = await generate_reddit_agent_graph(
                    profile_path=profile_path,
                    model=default_model,
                    available_actions=available_actions,
                )
            else:
                # CSV path handled by generate_twitter_agent_graph
                from oasis import generate_twitter_agent_graph
                default_model = create_model(
                    llm_provider, llm_model, self._settings, self._registry,
                )
                agent_graph = await generate_twitter_agent_graph(
                    profile_path=profile_path,
                    model=default_model,
                    available_actions=available_actions,
                )
        elif agent_profiles:
            # Build agents from inline profile data
            agent_graph = self._build_agent_graph_from_profiles(
                agent_profiles=agent_profiles,
                tiered_assigner=tiered_assigner,
                available_actions=available_actions,
                recsys_type=recsys_type,
                AgentGraph=AgentGraph,
                SocialAgent=SocialAgent,
                UserInfo=UserInfo,
            )
        else:
            # Generate simple numbered agents
            agent_graph = self._build_simple_agent_graph(
                num_agents=num_agents,
                tiered_assigner=tiered_assigner,
                available_actions=available_actions,
                recsys_type=recsys_type,
                AgentGraph=AgentGraph,
                SocialAgent=SocialAgent,
                UserInfo=UserInfo,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )

        # Create OasisEnv
        env = oasis.make(
            agent_graph=agent_graph,
            platform=platform_enum,
            database_path=db_path,
        )

        try:
            await env.reset()

            # --- Step 1..N: Simulation ---
            for step in range(1, num_steps + 1):
                # Check for cancellation
                if task_info.status.value == "cancelled":
                    logger.info("Task %s cancelled at step %d", task_info.task_id, step)
                    break

                if step == 1 and seed_content:
                    # First step: seed content via manual action, then LLM for rest
                    actions = {}
                    first_agent = env.agent_graph.get_agent(0)
                    actions[first_agent] = [
                        ManualAction(
                            action_type=ActionType.CREATE_POST,
                            action_args={"content": seed_content},
                        ),
                    ]
                    # Other agents do LLM actions
                    for agent_id, agent in env.agent_graph.get_agents():
                        if agent_id != 0:
                            actions[agent] = LLMAction()
                    await env.step(actions)
                else:
                    # All agents perform LLM-driven actions
                    actions = {
                        agent: LLMAction()
                        for _, agent in env.agent_graph.get_agents()
                    }
                    await env.step(actions)

                await self._reporter.report_progress(
                    task_info,
                    current_step=step,
                    total_steps=total_progress_steps,
                    data={"phase": "simulation", "step": step},
                )

        finally:
            # --- Cleanup ---
            await env.close()

        await self._reporter.report_progress(
            task_info,
            current_step=total_progress_steps,
            total_steps=total_progress_steps,
            data={"phase": "cleanup"},
        )

        result = {
            "db_path": db_path,
            "num_steps_completed": num_steps,
            "num_agents": agent_graph.get_num_nodes(),
            "platform_type": platform_type_str,
        }

        await self._reporter.report_complete(task_info, result)
        return result

    def _build_tiered_assigner(
        self, params: dict[str, Any]
    ) -> Optional[TieredModelAssigner]:
        """Build a TieredModelAssigner if API keys are available."""
        try:
            return TieredModelAssigner(
                settings=self._settings,
                registry=self._registry,
            )
        except Exception:
            logger.debug("Tiered assignment not available, using single model")
            return None

    def _build_simple_agent_graph(
        self,
        num_agents: int,
        tiered_assigner: Optional[TieredModelAssigner],
        available_actions,
        recsys_type: str,
        AgentGraph,
        SocialAgent,
        UserInfo,
        llm_provider: str,
        llm_model: str,
    ):
        """Create a simple agent graph with numbered agents."""
        agent_graph = AgentGraph()

        # Try tiered assignment first, fall back to single model
        if tiered_assigner:
            try:
                tier_assignments = tiered_assigner.assign_models(num_agents)
            except Exception:
                logger.info("Tiered model creation failed, falling back to single model")
                tier_assignments = None
        else:
            tier_assignments = None

        if tier_assignments is None:
            # Single model for all agents
            single_model = create_model(
                llm_provider, llm_model, self._settings, self._registry,
            )
            for i in range(num_agents):
                agent = SocialAgent(
                    agent_id=i,
                    user_info=UserInfo(
                        user_name=f"agent_{i}",
                        name=f"Agent {i}",
                        description=f"Simulated user {i}",
                        profile=None,
                        recsys_type=recsys_type,
                    ),
                    agent_graph=agent_graph,
                    model=single_model,
                    available_actions=available_actions,
                )
                agent_graph.add_agent(agent)
        else:
            for i in range(num_agents):
                tier, model = tier_assignments[i]
                agent = SocialAgent(
                    agent_id=i,
                    user_info=UserInfo(
                        user_name=f"agent_{i}",
                        name=f"Agent {i}",
                        description=f"Simulated user {i} (tier={tier.value})",
                        profile=None,
                        recsys_type=recsys_type,
                    ),
                    agent_graph=agent_graph,
                    model=model,
                    available_actions=available_actions,
                )
                agent_graph.add_agent(agent)

        return agent_graph

    def _build_agent_graph_from_profiles(
        self,
        agent_profiles: list[dict[str, Any]],
        tiered_assigner: Optional[TieredModelAssigner],
        available_actions,
        recsys_type: str,
        AgentGraph,
        SocialAgent,
        UserInfo,
    ):
        """Create an agent graph from user-provided profile dictionaries.

        Each profile dict should have:
            user_name: str
            name: str
            description: str
            profile: dict | None (optional, for persona/mbti/etc.)
        """
        agent_graph = AgentGraph()
        num_agents = len(agent_profiles)

        if tiered_assigner:
            try:
                tier_assignments = tiered_assigner.assign_models(num_agents)
            except Exception:
                tier_assignments = None
        else:
            tier_assignments = None

        for i, prof in enumerate(agent_profiles):
            if tier_assignments and i in tier_assignments:
                _, model = tier_assignments[i]
            else:
                model = create_model(
                    self._settings.default_llm_provider,
                    self._settings.default_llm_model,
                    self._settings,
                    self._registry,
                )

            profile_data = prof.get("profile")

            agent = SocialAgent(
                agent_id=i,
                user_info=UserInfo(
                    user_name=prof.get("user_name", f"agent_{i}"),
                    name=prof.get("name", f"Agent {i}"),
                    description=prof.get("description", ""),
                    profile=profile_data,
                    recsys_type=recsys_type,
                ),
                agent_graph=agent_graph,
                model=model,
                available_actions=available_actions,
            )
            agent_graph.add_agent(agent)

        return agent_graph
```

### Step 7.2: Create `engine/tests/test_runner.py`

**File:** `engine/tests/test_runner.py`

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.config import Settings
from engine.queue import TaskInfo, TaskStatus
from engine.reporter import ProgressReporter
from engine.runner import SimulationRunner


def _make_settings(**overrides):
    defaults = {
        "_env_file": None,
        "deepseek_api_key": "sk-test",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _make_reporter():
    client = MagicMock()
    client.send_progress = AsyncMock(return_value=True)
    client.send_complete = AsyncMock(return_value=True)
    client.send_error = AsyncMock(return_value=True)
    return ProgressReporter(callback_client=client)


class TestSimulationRunner:
    @pytest.mark.asyncio
    async def test_run_with_mocked_oasis(self):
        """Full run with mocked oasis module to verify the runner flow."""
        settings = _make_settings()
        reporter = _make_reporter()

        # Mock the entire oasis module
        mock_env = AsyncMock()
        mock_env.reset = AsyncMock()
        mock_env.step = AsyncMock()
        mock_env.close = AsyncMock()

        mock_agent = MagicMock()
        mock_agent.social_agent_id = 0
        mock_agent_graph = MagicMock()
        mock_agent_graph.get_agents.return_value = [(0, mock_agent)]
        mock_agent_graph.get_agent.return_value = mock_agent
        mock_agent_graph.get_num_nodes.return_value = 1
        mock_env.agent_graph = mock_agent_graph

        mock_make = MagicMock(return_value=mock_env)
        mock_create_model = MagicMock(return_value=MagicMock())

        task_info = TaskInfo(task_id="test123", params={})

        with patch("engine.runner.create_model", mock_create_model), \
             patch.dict("sys.modules", {
                 "oasis": MagicMock(
                     make=mock_make,
                     ActionType=MagicMock(
                         get_default_reddit_actions=MagicMock(return_value=[]),
                         CREATE_POST=MagicMock(),
                     ),
                     AgentGraph=MagicMock,
                     DefaultPlatformType=MagicMock(REDDIT="reddit", TWITTER="twitter"),
                     LLMAction=MagicMock,
                     ManualAction=MagicMock,
                     SocialAgent=MagicMock,
                     UserInfo=MagicMock,
                     generate_reddit_agent_graph=AsyncMock(),
                 ),
             }):
            runner = SimulationRunner(settings=settings, reporter=reporter)
            result = await runner.run(task_info, {
                "num_agents": 1,
                "num_steps": 2,
                "platform_type": "reddit",
            })

        assert result["num_steps_completed"] == 2
        assert result["platform_type"] == "reddit"
        assert "db_path" in result
        assert mock_env.reset.called
        assert mock_env.close.called
        # step called once per simulation step
        assert mock_env.step.call_count == 2
        # Reporter progress calls: setup + 2 steps + cleanup = 4
        assert reporter._client.send_progress.call_count == 4
        assert reporter._client.send_complete.call_count == 1

    @pytest.mark.asyncio
    async def test_run_with_seed_content(self):
        """Verify seed content creates a manual action on step 1."""
        settings = _make_settings()
        reporter = _make_reporter()

        mock_env = AsyncMock()
        mock_env.reset = AsyncMock()
        mock_env.step = AsyncMock()
        mock_env.close = AsyncMock()

        mock_agent_0 = MagicMock()
        mock_agent_0.social_agent_id = 0
        mock_agent_1 = MagicMock()
        mock_agent_1.social_agent_id = 1
        mock_agent_graph = MagicMock()
        mock_agent_graph.get_agents.return_value = [
            (0, mock_agent_0),
            (1, mock_agent_1),
        ]
        mock_agent_graph.get_agent.return_value = mock_agent_0
        mock_agent_graph.get_num_nodes.return_value = 2
        mock_env.agent_graph = mock_agent_graph

        mock_make = MagicMock(return_value=mock_env)
        mock_create_model = MagicMock(return_value=MagicMock())

        task_info = TaskInfo(task_id="seed-test", params={})

        mock_manual_action_cls = MagicMock()
        mock_llm_action_cls = MagicMock()

        with patch("engine.runner.create_model", mock_create_model), \
             patch.dict("sys.modules", {
                 "oasis": MagicMock(
                     make=mock_make,
                     ActionType=MagicMock(
                         get_default_reddit_actions=MagicMock(return_value=[]),
                         CREATE_POST=MagicMock(),
                     ),
                     AgentGraph=MagicMock,
                     DefaultPlatformType=MagicMock(REDDIT="reddit", TWITTER="twitter"),
                     LLMAction=mock_llm_action_cls,
                     ManualAction=mock_manual_action_cls,
                     SocialAgent=MagicMock,
                     UserInfo=MagicMock,
                     generate_reddit_agent_graph=AsyncMock(),
                 ),
             }):
            runner = SimulationRunner(settings=settings, reporter=reporter)
            result = await runner.run(task_info, {
                "num_agents": 2,
                "num_steps": 2,
                "seed_content": "Hello OASIS!",
            })

        # ManualAction should have been instantiated for the seed post
        mock_manual_action_cls.assert_called()
        assert result["num_steps_completed"] == 2
```

### Step 7.3: Run tests

```bash
cd D:/project/oasis
python -m pytest engine/tests/test_runner.py -v
```

### Step 7.4: Commit

```bash
git add engine/runner.py engine/tests/test_runner.py
git commit -m "feat(engine): add simulation runner wrapping OasisEnv

SimulationRunner builds agent graph (simple, from profiles, or from
file), creates OasisEnv, runs N steps with LLM actions, reports
progress per step, and handles cleanup. Supports seed content,
tiered model assignment, and cancellation."
```

---

## Task 8: FastAPI API Endpoints

**Goal:** Wire up the full FastAPI application with task submission, status, cancellation, and health endpoints.

**Estimated time:** 5 minutes

### Step 8.1: Implement the full `engine/main.py`

**File:** `engine/main.py`

```python
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
```

### Step 8.2: Implement `engine/platforms/__init__.py`

**File:** `engine/platforms/__init__.py`

```python
"""Platform registry placeholder.

This module will be extended in Plan 3 to support custom platform
configurations beyond the built-in TWITTER and REDDIT types.
"""

from oasis.social_platform.typing import DefaultPlatformType

SUPPORTED_PLATFORMS = {
    "twitter": DefaultPlatformType.TWITTER,
    "reddit": DefaultPlatformType.REDDIT,
}


def resolve_platform(name: str) -> DefaultPlatformType:
    """Return the DefaultPlatformType for a platform name string."""
    platform = SUPPORTED_PLATFORMS.get(name.lower())
    if platform is None:
        available = ", ".join(sorted(SUPPORTED_PLATFORMS.keys()))
        raise ValueError(
            f"Unknown platform '{name}'. Available: {available}"
        )
    return platform
```

### Step 8.3: Verify endpoints start correctly

```bash
cd D:/project/oasis
python -c "from engine.main import app; print('App loaded:', app.title)"
```

### Step 8.4: Commit

```bash
git add engine/main.py engine/platforms/__init__.py
git commit -m "feat(engine): add FastAPI endpoints for task submission, status, cancellation

POST /engine/tasks (submit), GET /engine/tasks/{id} (status),
POST /engine/tasks/{id}/cancel, GET /engine/health. Auth via
X-Internal-Key header. Platform registry for twitter/reddit."
```

---

## Task 9: Integration Tests

**Goal:** Test the full flow with mocked OASIS core -- submit a task via the API, verify progress reporting, and confirm completion.

**Estimated time:** 5 minutes

### Step 9.1: Create `engine/tests/conftest.py`

**File:** `engine/tests/conftest.py`

```python
import os

import pytest


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Clear the lru_cache on get_settings between tests."""
    from engine.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

### Step 9.2: Create `engine/tests/test_api.py`

**File:** `engine/tests/test_api.py`

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from engine.config import Settings
from engine.main import app
from engine.queue import TaskQueueManager, TaskStatus


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


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, settings):
        transport = ASGITransport(app=app)
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
    async def test_submit_requires_auth(self, settings):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/engine/tasks", json={"num_agents": 5})
        assert resp.status_code == 422  # missing header

    @pytest.mark.asyncio
    async def test_submit_rejects_wrong_key(self, settings):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/engine/tasks",
                json={"num_agents": 5},
                headers={"X-Internal-Key": "wrong-key"},
            )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_submit_and_get_task(self, settings, auth_headers):
        transport = ASGITransport(app=app)
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
    async def test_get_nonexistent_task(self, settings, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/engine/tasks/nonexistent",
                headers=auth_headers,
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self, settings, auth_headers):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/engine/tasks/nonexistent/cancel",
                headers=auth_headers,
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_submitted_task(self, settings, auth_headers):
        transport = ASGITransport(app=app)
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
```

### Step 9.3: Update `engine/tests/__init__.py`

**File:** `engine/tests/__init__.py`

```python
```

(Leave empty -- just needs to exist as a package marker.)

### Step 9.4: Run all tests

```bash
cd D:/project/oasis
python -m pytest engine/tests/ -v --tb=short
```

### Step 9.5: Commit

```bash
git add engine/tests/
git commit -m "feat(engine): add integration tests for API endpoints and callbacks

Tests cover health check, task submission with auth, task status,
cancellation, auth rejection, and callback client with mock transport."
```

---

## Summary of All Files

| File | Purpose |
|------|---------|
| `engine/main.py` | FastAPI app with lifespan, endpoints, auth |
| `engine/config.py` | Pydantic Settings with all env vars |
| `engine/queue.py` | asyncio.Queue task manager with concurrency control |
| `engine/runner.py` | Simulation runner wrapping OasisEnv |
| `engine/reporter.py` | Progress reporter bridging runner and callback |
| `engine/callback.py` | HTTP callback client with retry logic |
| `engine/llm/__init__.py` | LLM module exports |
| `engine/llm/provider.py` | LLM provider registry (7 providers) |
| `engine/llm/tiered.py` | Cost-tiered model assignment |
| `engine/platforms/__init__.py` | Platform registry (twitter/reddit) |
| `engine/tests/__init__.py` | Test package marker |
| `engine/tests/conftest.py` | Shared fixtures (settings cache reset) |
| `engine/tests/test_config.py` | Config module tests |
| `engine/tests/test_queue.py` | Task queue tests |
| `engine/tests/test_llm.py` | Provider registry and tiered assignment tests |
| `engine/tests/test_runner.py` | Simulation runner tests (mocked oasis) |
| `engine/tests/test_api.py` | API endpoint integration tests |
| `engine/requirements.txt` | Python dependencies |
| `engine/.env.example` | Example environment variables |

## Execution Order

```
Task 1 (setup) --> Task 2 (config) --> Task 3 (LLM providers) --> Task 4 (tiering)
                                                                        |
Task 5 (queue) --> Task 6 (callbacks) --> Task 7 (runner) --> Task 8 (API) --> Task 9 (tests)
```

Tasks 1-4 build the configuration and LLM layers bottom-up. Tasks 5-8 build the runtime flow from queue to API. Task 9 validates the complete integration.

## Running the Engine

```bash
cd D:/project/oasis
cp engine/.env.example engine/.env
# Edit engine/.env with real API keys

pip install -r engine/requirements.txt
uvicorn engine.main:app --host 0.0.0.0 --port 8100 --reload
```

## Testing

```bash
cd D:/project/oasis
python -m pytest engine/tests/ -v
```

## Communication Flow

```
Nuxt Web App                      Engine Service                    OASIS Core
    |                                  |                                |
    |-- POST /engine/tasks ----------->|                                |
    |<-- 202 {task_id, pending} -------|                                |
    |                                  |-- asyncio.Queue picks up ----->|
    |                                  |-- oasis.make() --------------->|
    |                                  |-- env.reset() ---------------->|
    |<-- POST /api/internal/progress --|                                |
    |                                  |-- env.step(actions) ---------->|
    |<-- POST /api/internal/progress --|                                |
    |                                  |-- ... (N steps) ...            |
    |                                  |-- env.close() ---------------->|
    |<-- POST /api/internal/complete --|                                |
```
