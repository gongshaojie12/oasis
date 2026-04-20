# P0-1: 人格基因组 (Persona Genome) 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建多源智能 Agent Profile 生成系统，支持从文档/URL/CSV/自然语言描述中提取人格基因组，并通过繁殖算法批量生成多样化 Agent 群体。

**Architecture:** Engine 层新增 `genome` 模块处理基因组提取和繁殖算法，通过 LLM 分析源数据并映射到结构化基因组。Server 层新增 Drizzle 表和 CRUD API。Frontend 新增基因组管理页面和群体预览可视化组件。

**Tech Stack:** Python (FastAPI, Pydantic), TypeScript (Nuxt 4, Naive UI, ECharts), Drizzle ORM, Zod

---

## 文件结构

### 新建文件

```
engine/
├── genome/
│   ├── __init__.py          — 模块导出
│   ├── schema.py            — Pydantic 数据模型（GenomeData, TraitSet 等）
│   ├── extractor.py         — 多源基因组提取（LLM 驱动）
│   └── breeder.py           — 群体繁殖算法（克隆突变/交叉/分布采样）

web/
├── server/
│   ├── api/genomes/
│   │   ├── index.get.ts     — 列表（分页、筛选）
│   │   ├── index.post.ts    — 手动创建基因组
│   │   ├── [id].get.ts      — 获取详情
│   │   ├── [id].put.ts      — 更新基因组
│   │   ├── [id].delete.ts   — 删除基因组
│   │   ├── extract.post.ts  — 从数据源提取基因组（调用 Engine）
│   │   ├── breed.post.ts    — 繁殖批量生成（调用 Engine）
│   │   ├── preview.post.ts  — 群体画像预览
│   │   └── to-profiles.post.ts — 基因组 → OASIS Profile 转换
├── app/
│   ├── pages/genomes/
│   │   ├── index.vue        — 基因组列表页
│   │   ├── create.vue       — 创建基因组页（多源输入）
│   │   ├── [id].vue         — 基因组详情/编辑页
│   │   └── breed.vue        — 群体繁殖配置 + 预览页
│   ├── components/
│   │   ├── GenomeRadar.vue  — 五大人格雷达图
│   │   └── PopulationPreview.vue — 群体分布预览组件
│   └── stores/
│       └── genomes.ts       — 基因组 Pinia Store
```

### 修改文件

```
web/server/database/schema/sqlite.ts  — 添加 personaGenomes, genomeBatches 表
web/server/database/schema/pg.ts      — 同上（PostgreSQL 版本）
web/server/database/schema/index.ts   — 导出新表
web/app/layouts/default.vue           — 侧边栏添加「基因组」导航项
engine/main.py                         — 添加基因组相关 API 端点
```

---

## Task 1: Engine 基因组数据模型

**Files:**
- Create: `engine/genome/__init__.py`
- Create: `engine/genome/schema.py`
- Test: `engine/tests/test_genome_schema.py`

- [ ] **Step 1: 创建基因组 Pydantic 模型**

```python
# engine/genome/schema.py
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    DOCUMENT = "document"
    URL = "url"
    CSV = "csv"
    MANUAL = "manual"
    NATURAL_LANGUAGE = "natural_language"


class BigFiveTraits(BaseModel):
    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)


class SocialBehavior(BaseModel):
    activity_level: float = Field(default=0.5, ge=0.0, le=1.0)
    content_creation_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    interaction_preference: str = Field(default="balanced")
    influence_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    echo_chamber_tendency: float = Field(default=0.5, ge=0.0, le=1.0)


class OpinionSpectrum(BaseModel):
    topic_stances: dict[str, float] = Field(default_factory=dict)
    persuadability: float = Field(default=0.5, ge=0.0, le=1.0)
    stance_volatility: float = Field(default=0.5, ge=0.0, le=1.0)


class Demographics(BaseModel):
    age_range: list[int] = Field(default=[20, 40])
    profession: str = Field(default="general")
    interests: list[str] = Field(default_factory=list)
    mbti: Optional[str] = None


class BehavioralPatterns(BaseModel):
    peak_activity_hours: list[int] = Field(default=[9, 12, 20, 22])
    avg_post_length: str = Field(default="medium")
    emoji_usage: float = Field(default=0.3, ge=0.0, le=1.0)
    hashtag_usage: float = Field(default=0.3, ge=0.0, le=1.0)


class GenomeData(BaseModel):
    traits: BigFiveTraits = Field(default_factory=BigFiveTraits)
    social_behavior: SocialBehavior = Field(default_factory=SocialBehavior)
    opinion_spectrum: OpinionSpectrum = Field(default_factory=OpinionSpectrum)
    demographics: Demographics = Field(default_factory=Demographics)
    behavioral_patterns: BehavioralPatterns = Field(
        default_factory=BehavioralPatterns
    )


class BreedStrategy(str, Enum):
    CLONE_MUTATE = "clone_mutate"
    CROSSOVER = "crossover"
    DISTRIBUTION = "distribution"
```

- [ ] **Step 2: 创建 __init__.py 导出**

```python
# engine/genome/__init__.py
from .schema import (
    BigFiveTraits,
    BehavioralPatterns,
    BreedStrategy,
    Demographics,
    GenomeData,
    OpinionSpectrum,
    SocialBehavior,
    SourceType,
)

__all__ = [
    "BigFiveTraits",
    "BehavioralPatterns",
    "BreedStrategy",
    "Demographics",
    "GenomeData",
    "OpinionSpectrum",
    "SocialBehavior",
    "SourceType",
]
```

- [ ] **Step 3: 编写测试**

```python
# engine/tests/test_genome_schema.py
from genome.schema import GenomeData, BigFiveTraits, BreedStrategy, SourceType


def test_genome_data_defaults():
    g = GenomeData()
    assert g.traits.openness == 0.5
    assert g.social_behavior.activity_level == 0.5
    assert g.demographics.profession == "general"


def test_genome_data_custom():
    g = GenomeData(
        traits=BigFiveTraits(openness=0.9, extraversion=0.2),
        demographics={"age_range": [18, 25], "profession": "student", "interests": ["gaming"]},
    )
    assert g.traits.openness == 0.9
    assert g.demographics.profession == "student"


def test_genome_data_serialization():
    g = GenomeData()
    d = g.model_dump()
    assert "traits" in d
    assert "social_behavior" in d
    restored = GenomeData.model_validate(d)
    assert restored.traits.openness == g.traits.openness


def test_source_type_values():
    assert SourceType.DOCUMENT.value == "document"
    assert SourceType.NATURAL_LANGUAGE.value == "natural_language"


def test_breed_strategy_values():
    assert BreedStrategy.CROSSOVER.value == "crossover"
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd D:/NLP/oasis && python -m pytest engine/tests/test_genome_schema.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: 提交**

```bash
git add engine/genome/__init__.py engine/genome/schema.py engine/tests/test_genome_schema.py
git commit -m "feat(genome): add persona genome data models"
```

---

## Task 2: 繁殖算法

**Files:**
- Create: `engine/genome/breeder.py`
- Test: `engine/tests/test_genome_breeder.py`

- [ ] **Step 1: 编写繁殖算法测试**

```python
# engine/tests/test_genome_breeder.py
import pytest
from genome.schema import GenomeData, BigFiveTraits, BreedStrategy
from genome.breeder import GenomeBreeder


def _make_seed(openness: float = 0.8) -> GenomeData:
    return GenomeData(traits=BigFiveTraits(openness=openness, extraversion=0.6))


def test_clone_mutate_preserves_count():
    seeds = [_make_seed()]
    breeder = GenomeBreeder(seeds=seeds, target_count=10, mutation_rate=0.1, strategy=BreedStrategy.CLONE_MUTATE)
    result = breeder.breed()
    assert len(result) == 10


def test_clone_mutate_introduces_variation():
    seeds = [_make_seed()]
    breeder = GenomeBreeder(seeds=seeds, target_count=50, mutation_rate=0.3, strategy=BreedStrategy.CLONE_MUTATE)
    result = breeder.breed()
    openness_values = [g.traits.openness for g in result]
    assert len(set(round(v, 4) for v in openness_values)) > 1


def test_crossover_requires_two_seeds():
    seeds = [_make_seed(0.8), _make_seed(0.2)]
    breeder = GenomeBreeder(seeds=seeds, target_count=20, mutation_rate=0.1, strategy=BreedStrategy.CROSSOVER)
    result = breeder.breed()
    assert len(result) == 20


def test_distribution_sampling():
    seeds = [_make_seed(0.3), _make_seed(0.7), _make_seed(0.5)]
    breeder = GenomeBreeder(seeds=seeds, target_count=100, mutation_rate=0.0, strategy=BreedStrategy.DISTRIBUTION)
    result = breeder.breed()
    assert len(result) == 100
    avg_openness = sum(g.traits.openness for g in result) / len(result)
    assert 0.3 <= avg_openness <= 0.7


def test_values_stay_in_bounds():
    seeds = [GenomeData(traits=BigFiveTraits(openness=0.99, neuroticism=0.01))]
    breeder = GenomeBreeder(seeds=seeds, target_count=200, mutation_rate=0.5, strategy=BreedStrategy.CLONE_MUTATE)
    result = breeder.breed()
    for g in result:
        assert 0.0 <= g.traits.openness <= 1.0
        assert 0.0 <= g.traits.neuroticism <= 1.0


def test_diversity_check():
    seeds = [_make_seed()]
    breeder = GenomeBreeder(seeds=seeds, target_count=50, mutation_rate=0.2, strategy=BreedStrategy.CLONE_MUTATE)
    diversity = breeder.compute_diversity(breeder.breed())
    assert diversity > 0.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:/NLP/oasis && python -m pytest engine/tests/test_genome_breeder.py -v`
Expected: FAIL (ModuleNotFoundError: genome.breeder)

- [ ] **Step 3: 实现繁殖算法**

```python
# engine/genome/breeder.py
from __future__ import annotations

import random
from typing import Optional

import numpy as np

from .schema import GenomeData, BreedStrategy


_FLOAT_FIELDS = [
    ("traits", ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]),
    ("social_behavior", ["activity_level", "content_creation_ratio", "influence_weight", "echo_chamber_tendency"]),
    ("opinion_spectrum", ["persuadability", "stance_volatility"]),
    ("behavioral_patterns", ["emoji_usage", "hashtag_usage"]),
]


def _get_float_vector(genome: GenomeData) -> list[float]:
    values: list[float] = []
    for section, fields in _FLOAT_FIELDS:
        obj = getattr(genome, section)
        for f in fields:
            values.append(getattr(obj, f))
    return values


def _set_float_vector(genome: GenomeData, values: list[float]) -> None:
    idx = 0
    for section, fields in _FLOAT_FIELDS:
        obj = getattr(genome, section)
        for f in fields:
            clamped = max(0.0, min(1.0, values[idx]))
            setattr(obj, f, round(clamped, 4))
            idx += 1


class GenomeBreeder:
    def __init__(
        self,
        seeds: list[GenomeData],
        target_count: int,
        mutation_rate: float = 0.15,
        strategy: BreedStrategy = BreedStrategy.CROSSOVER,
        rng_seed: Optional[int] = 42,
    ):
        self._seeds = seeds
        self._target_count = target_count
        self._mutation_rate = mutation_rate
        self._strategy = strategy
        self._rng = random.Random(rng_seed)
        self._np_rng = np.random.default_rng(rng_seed)

    def breed(self) -> list[GenomeData]:
        if self._strategy == BreedStrategy.CLONE_MUTATE:
            return self._clone_mutate()
        elif self._strategy == BreedStrategy.CROSSOVER:
            return self._crossover()
        else:
            return self._distribution()

    def _clone_mutate(self) -> list[GenomeData]:
        result: list[GenomeData] = []
        for i in range(self._target_count):
            parent = self._seeds[i % len(self._seeds)]
            child = parent.model_copy(deep=True)
            vec = _get_float_vector(child)
            mutated = [
                v + self._np_rng.normal(0, self._mutation_rate) if self._rng.random() < 0.7 else v
                for v in vec
            ]
            _set_float_vector(child, mutated)
            self._mutate_non_float(child, parent)
            result.append(child)
        return result

    def _crossover(self) -> list[GenomeData]:
        result: list[GenomeData] = []
        for _ in range(self._target_count):
            p1, p2 = self._rng.choices(self._seeds, k=2)
            child = p1.model_copy(deep=True)
            v1 = _get_float_vector(p1)
            v2 = _get_float_vector(p2)
            alpha = self._np_rng.uniform(0.3, 0.7, size=len(v1))
            merged = [a * x + (1 - a) * y for a, x, y in zip(alpha, v1, v2)]
            noise = [self._np_rng.normal(0, self._mutation_rate * 0.5) for _ in merged]
            final = [m + n for m, n in zip(merged, noise)]
            _set_float_vector(child, final)
            self._crossover_non_float(child, p1, p2)
            result.append(child)
        return result

    def _distribution(self) -> list[GenomeData]:
        vectors = np.array([_get_float_vector(s) for s in self._seeds])
        mean = vectors.mean(axis=0)
        std = vectors.std(axis=0) + 1e-6
        result: list[GenomeData] = []
        for _ in range(self._target_count):
            template = self._rng.choice(self._seeds)
            child = template.model_copy(deep=True)
            sampled = self._np_rng.normal(mean, std)
            _set_float_vector(child, sampled.tolist())
            self._mutate_non_float(child, template)
            result.append(child)
        return result

    def _mutate_non_float(self, child: GenomeData, parent: GenomeData) -> None:
        if parent.demographics.interests and self._rng.random() < self._mutation_rate:
            pool = list(parent.demographics.interests)
            keep = max(1, len(pool) - 1)
            child.demographics.interests = self._rng.sample(pool, min(keep, len(pool)))

        if parent.demographics.age_range and self._rng.random() < self._mutation_rate:
            lo, hi = parent.demographics.age_range
            shift = self._rng.randint(-5, 5)
            child.demographics.age_range = [max(13, lo + shift), max(14, hi + shift)]

    def _crossover_non_float(self, child: GenomeData, p1: GenomeData, p2: GenomeData) -> None:
        all_interests = list(set(p1.demographics.interests + p2.demographics.interests))
        if all_interests:
            k = max(1, len(all_interests) // 2)
            child.demographics.interests = self._rng.sample(all_interests, min(k, len(all_interests)))
        child.demographics.mbti = self._rng.choice([p1.demographics.mbti, p2.demographics.mbti])
        child.demographics.profession = self._rng.choice([p1.demographics.profession, p2.demographics.profession])

    def compute_diversity(self, genomes: list[GenomeData]) -> float:
        if len(genomes) < 2:
            return 0.0
        vectors = np.array([_get_float_vector(g) for g in genomes])
        return float(vectors.std(axis=0).mean())
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd D:/NLP/oasis && python -m pytest engine/tests/test_genome_breeder.py -v`
Expected: 6 tests PASS

- [ ] **Step 5: 更新 __init__.py 并提交**

在 `engine/genome/__init__.py` 末尾添加:
```python
from .breeder import GenomeBreeder
```

```bash
git add engine/genome/breeder.py engine/genome/__init__.py engine/tests/test_genome_breeder.py
git commit -m "feat(genome): implement breeding algorithms (clone/crossover/distribution)"
```

---

## Task 3: LLM 基因组提取器

**Files:**
- Create: `engine/genome/extractor.py`
- Test: `engine/tests/test_genome_extractor.py`

- [ ] **Step 1: 编写提取器测试**

```python
# engine/tests/test_genome_extractor.py
import json
import pytest
from unittest.mock import AsyncMock, patch
from genome.schema import GenomeData, SourceType
from genome.extractor import GenomeExtractor


MOCK_LLM_RESPONSE = json.dumps({
    "traits": {"openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.7, "agreeableness": 0.5, "neuroticism": 0.3},
    "social_behavior": {"activity_level": 0.9, "content_creation_ratio": 0.7, "interaction_preference": "reply_heavy", "influence_weight": 0.8, "echo_chamber_tendency": 0.3},
    "opinion_spectrum": {"topic_stances": {"AI": 0.9}, "persuadability": 0.3, "stance_volatility": 0.2},
    "demographics": {"age_range": [25, 35], "profession": "engineer", "interests": ["tech", "gaming"], "mbti": "INTJ"},
    "behavioral_patterns": {"peak_activity_hours": [9, 20], "avg_post_length": "long", "emoji_usage": 0.2, "hashtag_usage": 0.4},
})


@pytest.mark.asyncio
async def test_extract_from_text():
    mock_llm = AsyncMock(return_value=MOCK_LLM_RESPONSE)
    extractor = GenomeExtractor(llm_call=mock_llm)
    genome = await extractor.extract_from_text("这是一个科技爱好者，喜欢发长文讨论AI技术")
    assert isinstance(genome, GenomeData)
    assert genome.traits.openness == 0.8
    assert genome.demographics.profession == "engineer"


@pytest.mark.asyncio
async def test_extract_from_csv_row():
    extractor = GenomeExtractor(llm_call=AsyncMock(return_value=MOCK_LLM_RESPONSE))
    row = {"name": "张三", "age": 30, "interests": "科技,游戏", "personality": "内向理性"}
    genome = await extractor.extract_from_structured(row)
    assert isinstance(genome, GenomeData)


@pytest.mark.asyncio
async def test_extract_handles_malformed_llm_output():
    mock_llm = AsyncMock(return_value="not valid json")
    extractor = GenomeExtractor(llm_call=mock_llm)
    genome = await extractor.extract_from_text("some text")
    assert isinstance(genome, GenomeData)
    assert genome.traits.openness == 0.5  # default fallback
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:/NLP/oasis && python -m pytest engine/tests/test_genome_extractor.py -v`
Expected: FAIL (ModuleNotFoundError: genome.extractor)

- [ ] **Step 3: 实现提取器**

```python
# engine/genome/extractor.py
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Awaitable, Optional

from .schema import GenomeData

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """你是一个人格分析专家。根据以下文本/数据，分析其中描述的人物特征，并输出一个 JSON 对象。

输出格式要求（所有数值字段范围 0.0-1.0）：
{
  "traits": {
    "openness": <float>, "conscientiousness": <float>, "extraversion": <float>,
    "agreeableness": <float>, "neuroticism": <float>
  },
  "social_behavior": {
    "activity_level": <float>, "content_creation_ratio": <float>,
    "interaction_preference": "<reply_heavy|post_heavy|balanced|lurker>",
    "influence_weight": <float>, "echo_chamber_tendency": <float>
  },
  "opinion_spectrum": {
    "topic_stances": {"<话题>": <-1.0到1.0的立场值>},
    "persuadability": <float>, "stance_volatility": <float>
  },
  "demographics": {
    "age_range": [<int>, <int>], "profession": "<string>",
    "interests": ["<string>"], "mbti": "<string或null>"
  },
  "behavioral_patterns": {
    "peak_activity_hours": [<int>], "avg_post_length": "<short|medium|long>",
    "emoji_usage": <float>, "hashtag_usage": <float>
  }
}

只输出 JSON，不要输出其他内容。

输入内容：
"""

STRUCTURED_PROMPT = """你是一个人格分析专家。根据以下结构化数据，推断此人的完整人格画像。
对于数据中没有的字段，请根据已有信息合理推断。

输出格式同上（JSON）。只输出 JSON。

结构化数据：
"""


class GenomeExtractor:
    def __init__(self, llm_call: Callable[[str], Awaitable[str]]):
        self._llm_call = llm_call

    async def extract_from_text(self, text: str) -> GenomeData:
        prompt = EXTRACTION_PROMPT + text
        return await self._call_and_parse(prompt)

    async def extract_from_structured(self, data: dict[str, Any]) -> GenomeData:
        prompt = STRUCTURED_PROMPT + json.dumps(data, ensure_ascii=False, indent=2)
        return await self._call_and_parse(prompt)

    async def _call_and_parse(self, prompt: str) -> GenomeData:
        try:
            raw = await self._llm_call(prompt)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            parsed = json.loads(cleaned)
            return GenomeData.model_validate(parsed)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse LLM genome output: %s", e)
            return GenomeData()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd D:/NLP/oasis && python -m pytest engine/tests/test_genome_extractor.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: 更新导出并提交**

在 `engine/genome/__init__.py` 添加:
```python
from .extractor import GenomeExtractor
```

```bash
git add engine/genome/extractor.py engine/genome/__init__.py engine/tests/test_genome_extractor.py
git commit -m "feat(genome): add LLM-driven genome extractor with multi-source support"
```

---

## Task 4: Engine 基因组 API 端点

**Files:**
- Modify: `engine/main.py`
- Test: `engine/tests/test_genome_api.py`

- [ ] **Step 1: 编写 API 测试**

```python
# engine/tests/test_genome_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from main import app


@pytest.fixture
def internal_key_header():
    return {"X-Internal-Key": "test-key"}


@pytest.mark.asyncio
async def test_extract_genome_endpoint(internal_key_header):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/engine/genomes/extract",
            json={"source_type": "natural_language", "content": "一个热爱科技的年轻人"},
            headers=internal_key_header,
        )
        assert resp.status_code in (200, 202)


@pytest.mark.asyncio
async def test_breed_genome_endpoint(internal_key_header):
    seed = {
        "traits": {"openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.5,
                    "agreeableness": 0.5, "neuroticism": 0.3},
        "social_behavior": {"activity_level": 0.7, "content_creation_ratio": 0.5,
                            "interaction_preference": "balanced", "influence_weight": 0.5,
                            "echo_chamber_tendency": 0.3},
        "opinion_spectrum": {"topic_stances": {}, "persuadability": 0.5, "stance_volatility": 0.3},
        "demographics": {"age_range": [20, 30], "profession": "student", "interests": ["tech"], "mbti": "INTP"},
        "behavioral_patterns": {"peak_activity_hours": [9, 21], "avg_post_length": "medium",
                                "emoji_usage": 0.3, "hashtag_usage": 0.3},
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/engine/genomes/breed",
            json={"seeds": [seed], "target_count": 5, "mutation_rate": 0.15, "strategy": "clone_mutate"},
            headers=internal_key_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["genomes"]) == 5
        assert "diversity" in data
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:/NLP/oasis && python -m pytest engine/tests/test_genome_api.py -v`
Expected: FAIL (no /engine/genomes/ routes)

- [ ] **Step 3: 在 main.py 添加基因组端点**

在 `engine/main.py` 中，在现有端点后添加：

```python
# === 在 import 区域添加 ===
from genome.schema import GenomeData, BreedStrategy
from genome.breeder import GenomeBreeder

# === 新增请求/响应模型 ===
class GenomeExtractRequest(BaseModel):
    source_type: str = Field(default="natural_language")
    content: str = Field(default="")
    structured_data: Optional[dict[str, Any]] = None

class GenomeBreedRequest(BaseModel):
    seeds: list[dict[str, Any]]
    target_count: int = Field(default=10, ge=1, le=10000)
    mutation_rate: float = Field(default=0.15, ge=0.0, le=1.0)
    strategy: str = Field(default="crossover")

# === 新增端点 ===
@app.post(
    "/engine/genomes/extract",
    dependencies=[Depends(verify_internal_key)],
)
async def extract_genome(body: GenomeExtractRequest, request: Request):
    settings = request.app.state.settings

    async def llm_call(prompt: str) -> str:
        from llm.provider import create_model, LLMProviderRegistry
        registry = LLMProviderRegistry()
        provider = settings.default_llm_provider or "qwen"
        model_id = settings.default_llm_model or "qwen-plus"
        model = create_model(provider, model_id, settings, registry)
        from camel.messages import BaseMessage
        user_msg = BaseMessage.make_user_message(role_name="user", content=prompt)
        response = model.run([user_msg])
        return response.msgs[0].content

    from genome.extractor import GenomeExtractor
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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd D:/NLP/oasis && python -m pytest engine/tests/test_genome_api.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: 提交**

```bash
git add engine/main.py engine/tests/test_genome_api.py
git commit -m "feat(engine): add genome extract and breed API endpoints"
```

---

## Task 5: 数据库表定义

**Files:**
- Modify: `web/server/database/schema/sqlite.ts`
- Modify: `web/server/database/schema/pg.ts`

- [ ] **Step 1: 在 sqlite.ts 末尾添加基因组表**

在 `web/server/database/schema/sqlite.ts` 文件末尾添加：

```typescript
export const personaGenomes = sqliteTable('persona_genomes', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  name: text('name').notNull(),
  sourceType: text('source_type').notNull(),
  genomeData: text('genome_data').notNull(),
  tags: text('tags'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const genomeBatches = sqliteTable('genome_batches', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  name: text('name').notNull(),
  seedGenomeIds: text('seed_genome_ids').notNull(),
  targetCount: integer('target_count').notNull(),
  mutationRate: real('mutation_rate').default(0.15).notNull(),
  strategy: text('strategy').default('crossover').notNull(),
  status: text('status').default('pending').notNull(),
  resultGenomeIds: text('result_genome_ids'),
  diversity: real('diversity'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})
```

- [ ] **Step 2: 在 pg.ts 末尾添加对应的 PostgreSQL 表**

在 `web/server/database/schema/pg.ts` 文件末尾添加：

```typescript
export const personaGenomes = pgTable('persona_genomes', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  name: text('name').notNull(),
  sourceType: text('source_type').notNull(),
  genomeData: text('genome_data').notNull(),
  tags: text('tags'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})

export const genomeBatches = pgTable('genome_batches', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  name: text('name').notNull(),
  seedGenomeIds: text('seed_genome_ids').notNull(),
  targetCount: integer('target_count').notNull(),
  mutationRate: real('mutation_rate').default(0.15).notNull(),
  strategy: text('strategy').default('crossover').notNull(),
  status: text('status').default('pending').notNull(),
  resultGenomeIds: text('result_genome_ids'),
  diversity: real('diversity'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})
```

- [ ] **Step 3: 确认 schema/index.ts 导出两个新表**

检查 `web/server/database/schema/index.ts`，确认它使用 `export *` 方式导出。如果是条件导出，需要添加新表名。

- [ ] **Step 4: 生成数据库迁移**

Run: `cd D:/NLP/oasis/web && npx drizzle-kit generate`
Expected: 生成新的迁移文件

- [ ] **Step 5: 提交**

```bash
git add web/server/database/schema/sqlite.ts web/server/database/schema/pg.ts web/drizzle/
git commit -m "feat(db): add persona_genomes and genome_batches tables"
```

---

## Task 6: Server 端基因组 CRUD API

**Files:**
- Create: `web/server/api/genomes/index.get.ts`
- Create: `web/server/api/genomes/index.post.ts`
- Create: `web/server/api/genomes/[id].get.ts`
- Create: `web/server/api/genomes/[id].put.ts`
- Create: `web/server/api/genomes/[id].delete.ts`

- [ ] **Step 1: 创建列表 API**

```typescript
// web/server/api/genomes/index.get.ts
import { eq, desc, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { personaGenomes } from '~~/server/database/schema'
import { success } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const { enterpriseId } = event.context.user!
  const query = getQuery(event)
  const page = Number(query.page) || 1
  const pageSize = Math.min(Number(query.pageSize) || 20, 100)
  const sourceType = query.sourceType as string | undefined

  const db = useDB()

  const conditions = [eq(personaGenomes.enterpriseId, enterpriseId)]
  if (sourceType) conditions.push(eq(personaGenomes.sourceType, sourceType))

  const where = conditions.length === 1 ? conditions[0] : and(...conditions)

  const items = await db.select()
    .from(personaGenomes)
    .where(where)
    .orderBy(desc(personaGenomes.createdAt))
    .limit(pageSize)
    .offset((page - 1) * pageSize)

  const allMatching = await db.select({ id: personaGenomes.id })
    .from(personaGenomes)
    .where(where)
  const total = allMatching.length

  const parsed = items.map(item => ({
    ...item,
    genomeData: JSON.parse(item.genomeData),
    tags: item.tags ? JSON.parse(item.tags) : [],
  }))

  return success({
    items: parsed,
    pagination: { page, pageSize, total, totalPages: Math.ceil(total / pageSize) },
  })
})
```

- [ ] **Step 2: 创建手动新增 API**

```typescript
// web/server/api/genomes/index.post.ts
import { z } from 'zod'
import { useDB } from '~~/server/database'
import { personaGenomes, operationLogs } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100),
  sourceType: z.enum(['document', 'url', 'csv', 'manual', 'natural_language']),
  genomeData: z.record(z.string(), z.any()),
  tags: z.array(z.string()).optional(),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误: ' + parsed.error.issues.map(i => i.message).join(', '))
  }

  const { userId, enterpriseId } = event.context.user!
  const db = useDB()
  const id = generateId()
  const timestamp = now()

  await db.insert(personaGenomes).values({
    id,
    enterpriseId,
    name: parsed.data.name,
    sourceType: parsed.data.sourceType,
    genomeData: JSON.stringify(parsed.data.genomeData),
    tags: parsed.data.tags ? JSON.stringify(parsed.data.tags) : null,
    createdAt: timestamp,
    updatedAt: timestamp,
  })

  await db.insert(operationLogs).values({
    id: generateId(), enterpriseId, userId,
    action: 'create', resourceType: 'genome', resourceId: id,
    details: JSON.stringify({ name: parsed.data.name, sourceType: parsed.data.sourceType }),
    createdAt: timestamp,
  })

  return success({ id, name: parsed.data.name })
})
```

- [ ] **Step 3: 创建详情 API**

```typescript
// web/server/api/genomes/[id].get.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { personaGenomes } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select().from(personaGenomes)
    .where(and(eq(personaGenomes.id, id), eq(personaGenomes.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '基因组不存在')

  return success({
    ...items[0],
    genomeData: JSON.parse(items[0].genomeData),
    tags: items[0].tags ? JSON.parse(items[0].tags) : [],
  })
})
```

- [ ] **Step 4: 创建更新 API**

```typescript
// web/server/api/genomes/[id].put.ts
import { z } from 'zod'
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { personaGenomes } from '~~/server/database/schema'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100).optional(),
  genomeData: z.record(z.string(), z.any()).optional(),
  tags: z.array(z.string()).optional(),
})

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误')
  }

  const db = useDB()

  const existing = await db.select().from(personaGenomes)
    .where(and(eq(personaGenomes.id, id), eq(personaGenomes.enterpriseId, enterpriseId)))
    .limit(1)

  if (existing.length === 0) return error(ErrorCodes.NOT_FOUND, '基因组不存在')

  const updates: Record<string, any> = { updatedAt: now() }
  if (parsed.data.name) updates.name = parsed.data.name
  if (parsed.data.genomeData) updates.genomeData = JSON.stringify(parsed.data.genomeData)
  if (parsed.data.tags) updates.tags = JSON.stringify(parsed.data.tags)

  await db.update(personaGenomes).set(updates).where(eq(personaGenomes.id, id))

  return success({ id })
})
```

- [ ] **Step 5: 创建删除 API**

```typescript
// web/server/api/genomes/[id].delete.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { personaGenomes } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const existing = await db.select().from(personaGenomes)
    .where(and(eq(personaGenomes.id, id), eq(personaGenomes.enterpriseId, enterpriseId)))
    .limit(1)

  if (existing.length === 0) return error(ErrorCodes.FORBIDDEN, '只能删除自己的基因组')

  await db.delete(personaGenomes).where(eq(personaGenomes.id, id))
  return success({ id })
})
```

- [ ] **Step 6: 提交**

```bash
git add web/server/api/genomes/
git commit -m "feat(api): add genome CRUD endpoints"
```

---

## Task 7: Server 端基因组提取和繁殖代理 API

**Files:**
- Create: `web/server/api/genomes/extract.post.ts`
- Create: `web/server/api/genomes/breed.post.ts`
- Create: `web/server/api/genomes/preview.post.ts`
- Create: `web/server/api/genomes/to-profiles.post.ts`

- [ ] **Step 1: 创建提取代理 API（转发到 Engine）**

```typescript
// web/server/api/genomes/extract.post.ts
import { z } from 'zod'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  sourceType: z.enum(['document', 'url', 'csv', 'manual', 'natural_language']),
  content: z.string().optional(),
  structuredData: z.record(z.string(), z.any()).optional(),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误')
  }

  const config = useRuntimeConfig()
  try {
    const result = await $fetch(`${config.engineUrl}/engine/genomes/extract`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: {
        source_type: parsed.data.sourceType,
        content: parsed.data.content || '',
        structured_data: parsed.data.structuredData || null,
      },
    })
    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '基因组提取失败: ' + (e.message || '引擎不可用'))
  }
})
```

- [ ] **Step 2: 创建繁殖代理 API**

```typescript
// web/server/api/genomes/breed.post.ts
import { z } from 'zod'
import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { personaGenomes, genomeBatches, operationLogs } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100),
  seedGenomeIds: z.array(z.string()).min(1),
  targetCount: z.number().int().min(1).max(10000),
  mutationRate: z.number().min(0).max(1).default(0.15),
  strategy: z.enum(['clone_mutate', 'crossover', 'distribution']).default('crossover'),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误: ' + parsed.error.issues.map(i => i.message).join(', '))
  }

  const { userId, enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const seeds: any[] = []
  for (const gid of parsed.data.seedGenomeIds) {
    const g = await db.select().from(personaGenomes).where(eq(personaGenomes.id, gid)).limit(1)
    if (g.length === 0) return error(ErrorCodes.NOT_FOUND, `种子基因组 ${gid} 不存在`)
    seeds.push(JSON.parse(g[0].genomeData))
  }

  const batchId = generateId()
  const timestamp = now()

  await db.insert(genomeBatches).values({
    id: batchId, enterpriseId, name: parsed.data.name,
    seedGenomeIds: JSON.stringify(parsed.data.seedGenomeIds),
    targetCount: parsed.data.targetCount, mutationRate: parsed.data.mutationRate,
    strategy: parsed.data.strategy, status: 'processing',
    createdAt: timestamp, updatedAt: timestamp,
  })

  try {
    const result: any = await $fetch(`${config.engineUrl}/engine/genomes/breed`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: {
        seeds,
        target_count: parsed.data.targetCount,
        mutation_rate: parsed.data.mutationRate,
        strategy: parsed.data.strategy,
      },
    })

    const genomeIds: string[] = []
    for (let i = 0; i < result.genomes.length; i++) {
      const gId = generateId()
      genomeIds.push(gId)
      await db.insert(personaGenomes).values({
        id: gId, enterpriseId,
        name: `${parsed.data.name}_${String(i + 1).padStart(3, '0')}`,
        sourceType: 'breed',
        genomeData: JSON.stringify(result.genomes[i]),
        tags: JSON.stringify([`batch:${batchId}`]),
        createdAt: timestamp, updatedAt: timestamp,
      })
    }

    await db.update(genomeBatches).set({
      status: 'completed',
      resultGenomeIds: JSON.stringify(genomeIds),
      diversity: result.diversity,
      updatedAt: now(),
    }).where(eq(genomeBatches.id, batchId))

    await db.insert(operationLogs).values({
      id: generateId(), enterpriseId, userId,
      action: 'breed', resourceType: 'genome_batch', resourceId: batchId,
      details: JSON.stringify({ count: result.count, diversity: result.diversity }),
      createdAt: timestamp,
    })

    return success({ batchId, count: result.count, diversity: result.diversity, genomeIds })
  } catch (e: any) {
    await db.update(genomeBatches).set({ status: 'failed', updatedAt: now() }).where(eq(genomeBatches.id, batchId))
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '繁殖失败: ' + (e.message || '引擎不可用'))
  }
})
```

- [ ] **Step 3: 创建预览 API**

```typescript
// web/server/api/genomes/preview.post.ts
import { z } from 'zod'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  genomes: z.array(z.record(z.string(), z.any())).min(1),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误')
  }

  const genomes = parsed.data.genomes

  const traitKeys = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
  const traitDistribution: Record<string, { values: number[]; mean: number; std: number }> = {}
  for (const key of traitKeys) {
    const values = genomes.map(g => g.traits?.[key] ?? 0.5)
    const mean = values.reduce((a, b) => a + b, 0) / values.length
    const std = Math.sqrt(values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length)
    traitDistribution[key] = { values, mean: Math.round(mean * 1000) / 1000, std: Math.round(std * 1000) / 1000 }
  }

  const ageValues = genomes.map(g => {
    const range = g.demographics?.age_range ?? [25, 35]
    return Math.round((range[0] + range[1]) / 2)
  })

  const activityValues = genomes.map(g => g.social_behavior?.activity_level ?? 0.5)

  const professionCounts: Record<string, number> = {}
  for (const g of genomes) {
    const prof = g.demographics?.profession ?? 'unknown'
    professionCounts[prof] = (professionCounts[prof] || 0) + 1
  }

  return success({
    count: genomes.length,
    traitDistribution,
    ageDistribution: { values: ageValues, mean: Math.round(ageValues.reduce((a, b) => a + b, 0) / ageValues.length) },
    activityDistribution: { values: activityValues, mean: Math.round(activityValues.reduce((a, b) => a + b, 0) / activityValues.length * 100) / 100 },
    professionCounts,
  })
})
```

- [ ] **Step 4: 创建基因组转 OASIS Profile API**

```typescript
// web/server/api/genomes/to-profiles.post.ts
import { z } from 'zod'
import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { personaGenomes } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  genomeIds: z.array(z.string()).min(1),
  platform: z.string().default('twitter'),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) {
    return error(ErrorCodes.VALIDATION_ERROR, '参数错误')
  }

  const { enterpriseId } = event.context.user!
  const db = useDB()

  const profiles: any[] = []
  for (let i = 0; i < parsed.data.genomeIds.length; i++) {
    const gid = parsed.data.genomeIds[i]
    const g = await db.select().from(personaGenomes).where(eq(personaGenomes.id, gid)).limit(1)
    if (g.length === 0) continue
    const genome = JSON.parse(g[0].genomeData)

    const mbtiMap: Record<string, string> = {
      'INTJ': 'analytical and strategic thinker',
      'INTP': 'logical and curious explorer',
      'ENTJ': 'decisive and ambitious leader',
      'ENTP': 'innovative and quick-witted debater',
      'INFJ': 'insightful and idealistic advocate',
      'INFP': 'empathetic and creative mediator',
      'ENFJ': 'charismatic and inspiring protagonist',
      'ENFP': 'enthusiastic and creative campaigner',
      'ISTJ': 'responsible and detail-oriented logistician',
      'ISFJ': 'dedicated and warm protector',
      'ESTJ': 'organized and direct executive',
      'ESFJ': 'caring and sociable consul',
      'ISTP': 'bold and practical virtuoso',
      'ISFP': 'charming and artistic adventurer',
      'ESTP': 'smart and energetic entrepreneur',
      'ESFP': 'spontaneous and enthusiastic entertainer',
    }

    const personality = mbtiMap[genome.demographics?.mbti || ''] || 'thoughtful individual'
    const interests = (genome.demographics?.interests || []).join(', ')
    const ageRange = genome.demographics?.age_range || [25, 35]
    const age = Math.round((ageRange[0] + ageRange[1]) / 2)

    profiles.push({
      agent_id: i,
      name: g[0].name,
      user_name: g[0].name.toLowerCase().replace(/\s+/g, '_') + '_' + i,
      description: `A ${age}-year-old ${genome.demographics?.profession || 'professional'}, ${personality}. Interested in ${interests || 'various topics'}.`,
      persona: `${personality} who is ${genome.traits?.extraversion > 0.6 ? 'outgoing' : 'reserved'} and ${genome.traits?.agreeableness > 0.6 ? 'cooperative' : 'independent-minded'}`,
      age,
      mbti: genome.demographics?.mbti || null,
      interests: genome.demographics?.interests || [],
      activity_level: genome.social_behavior?.activity_level || 0.5,
    })
  }

  return success({ profiles, count: profiles.length })
})
```

- [ ] **Step 5: 提交**

```bash
git add web/server/api/genomes/extract.post.ts web/server/api/genomes/breed.post.ts web/server/api/genomes/preview.post.ts web/server/api/genomes/to-profiles.post.ts
git commit -m "feat(api): add genome extract, breed, preview and profile conversion endpoints"
```

---

## Task 8: Frontend Pinia Store

**Files:**
- Create: `web/app/stores/genomes.ts`

- [ ] **Step 1: 创建基因组 Store**

```typescript
// web/app/stores/genomes.ts
import { defineStore } from 'pinia'

export interface GenomeItem {
  id: string
  name: string
  sourceType: string
  genomeData: any
  tags: string[]
  createdAt: string
  updatedAt: string
}

interface Pagination {
  page: number
  pageSize: number
  total: number
  totalPages: number
}

interface GenomesState {
  items: GenomeItem[]
  pagination: Pagination
  loading: boolean
  currentGenome: GenomeItem | null
}

export const useGenomesStore = defineStore('genomes', {
  state: (): GenomesState => ({
    items: [],
    pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 },
    loading: false,
    currentGenome: null,
  }),

  actions: {
    async fetchList(params: { page?: number; pageSize?: number; sourceType?: string } = {}) {
      this.loading = true
      try {
        const { $api } = useApi()
        const query = new URLSearchParams()
        if (params.page) query.set('page', String(params.page))
        if (params.pageSize) query.set('pageSize', String(params.pageSize))
        if (params.sourceType) query.set('sourceType', params.sourceType)
        const res = await $api<any>(`/api/genomes?${query.toString()}`)
        if (res.code === 0) {
          this.items = res.data.items
          this.pagination = res.data.pagination
        }
      } finally {
        this.loading = false
      }
    },

    async fetchOne(id: string) {
      const { $api } = useApi()
      const res = await $api<any>(`/api/genomes/${id}`)
      if (res.code === 0) {
        this.currentGenome = res.data
      }
      return res
    },

    async create(data: { name: string; sourceType: string; genomeData: any; tags?: string[] }) {
      const { $api } = useApi()
      return await $api<any>('/api/genomes', { method: 'POST', body: data })
    },

    async update(id: string, data: { name?: string; genomeData?: any; tags?: string[] }) {
      const { $api } = useApi()
      return await $api<any>(`/api/genomes/${id}`, { method: 'PUT', body: data })
    },

    async remove(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/genomes/${id}`, { method: 'DELETE' })
    },

    async extract(data: { sourceType: string; content?: string; structuredData?: any }) {
      const { $api } = useApi()
      return await $api<any>('/api/genomes/extract', { method: 'POST', body: data })
    },

    async breed(data: { name: string; seedGenomeIds: string[]; targetCount: number; mutationRate?: number; strategy?: string }) {
      const { $api } = useApi()
      return await $api<any>('/api/genomes/breed', { method: 'POST', body: data })
    },

    async preview(genomes: any[]) {
      const { $api } = useApi()
      return await $api<any>('/api/genomes/preview', { method: 'POST', body: { genomes } })
    },

    async toProfiles(genomeIds: string[], platform: string = 'twitter') {
      const { $api } = useApi()
      return await $api<any>('/api/genomes/to-profiles', { method: 'POST', body: { genomeIds, platform } })
    },
  },
})
```

- [ ] **Step 2: 提交**

```bash
git add web/app/stores/genomes.ts
git commit -m "feat(store): add genomes Pinia store"
```

---

## Task 9: 雷达图组件

**Files:**
- Create: `web/app/components/GenomeRadar.vue`

- [ ] **Step 1: 创建雷达图组件**

```vue
<!-- web/app/components/GenomeRadar.vue -->
<template>
  <div ref="chartRef" :style="{ width: width, height: height }" />
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import * as echarts from 'echarts/core'

use([CanvasRenderer, RadarChart, TitleComponent, TooltipComponent, LegendComponent])

interface Props {
  traits: {
    openness: number
    conscientiousness: number
    extraversion: number
    agreeableness: number
    neuroticism: number
  }
  width?: string
  height?: string
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  width: '100%',
  height: '300px',
  title: '人格特质',
})

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const labels = {
  openness: '开放性',
  conscientiousness: '尽责性',
  extraversion: '外向性',
  agreeableness: '宜人性',
  neuroticism: '神经质',
}

function renderChart() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  chart.setOption({
    title: { text: props.title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {},
    radar: {
      indicator: Object.entries(labels).map(([key, name]) => ({ name, max: 1 })),
      shape: 'polygon',
      splitNumber: 4,
    },
    series: [{
      type: 'radar',
      data: [{
        value: [
          props.traits.openness,
          props.traits.conscientiousness,
          props.traits.extraversion,
          props.traits.agreeableness,
          props.traits.neuroticism,
        ],
        areaStyle: { opacity: 0.3 },
      }],
    }],
  })
}

onMounted(() => renderChart())
watch(() => props.traits, () => renderChart(), { deep: true })
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/components/GenomeRadar.vue
git commit -m "feat(ui): add GenomeRadar echarts component"
```

---

## Task 10: 群体预览组件

**Files:**
- Create: `web/app/components/PopulationPreview.vue`

- [ ] **Step 1: 创建群体预览组件**

```vue
<!-- web/app/components/PopulationPreview.vue -->
<template>
  <n-card title="群体画像预览" v-if="data">
    <n-grid :cols="2" :x-gap="16" :y-gap="16">
      <n-gi>
        <n-statistic label="总人数" :value="data.count" />
      </n-gi>
      <n-gi>
        <n-statistic label="平均年龄" :value="data.ageDistribution.mean" />
      </n-gi>
    </n-grid>

    <n-divider />
    <n-h4>五大人格分布</n-h4>
    <div ref="traitChartRef" style="width: 100%; height: 250px" />

    <n-divider />
    <n-h4>活跃度分布</n-h4>
    <div ref="activityChartRef" style="width: 100%; height: 200px" />

    <n-divider />
    <n-h4>职业分布</n-h4>
    <div ref="professionChartRef" style="width: 100%; height: 250px" />
  </n-card>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TitleComponent, TooltipComponent } from 'echarts/components'

echarts.use([CanvasRenderer, BarChart, PieChart, GridComponent, TitleComponent, TooltipComponent])

interface PreviewData {
  count: number
  traitDistribution: Record<string, { mean: number; std: number }>
  ageDistribution: { values: number[]; mean: number }
  activityDistribution: { values: number[]; mean: number }
  professionCounts: Record<string, number>
}

const props = defineProps<{ data: PreviewData | null }>()

const traitChartRef = ref<HTMLElement>()
const activityChartRef = ref<HTMLElement>()
const professionChartRef = ref<HTMLElement>()

const traitLabels: Record<string, string> = {
  openness: '开放性', conscientiousness: '尽责性', extraversion: '外向性',
  agreeableness: '宜人性', neuroticism: '神经质',
}

function renderCharts() {
  if (!props.data) return

  if (traitChartRef.value) {
    const chart = echarts.init(traitChartRef.value)
    const keys = Object.keys(props.data.traitDistribution)
    chart.setOption({
      tooltip: {},
      xAxis: { type: 'category', data: keys.map(k => traitLabels[k] || k) },
      yAxis: { type: 'value', max: 1 },
      series: [{
        type: 'bar', data: keys.map(k => props.data!.traitDistribution[k].mean),
        itemStyle: { color: '#18a058' },
      }],
    })
  }

  if (activityChartRef.value) {
    const chart = echarts.init(activityChartRef.value)
    const bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
    const counts = new Array(bins.length - 1).fill(0)
    for (const v of props.data.activityDistribution.values) {
      const idx = Math.min(Math.floor(v * 5), 4)
      counts[idx]++
    }
    chart.setOption({
      tooltip: {},
      xAxis: { type: 'category', data: ['极低', '低', '中', '高', '极高'] },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: counts, itemStyle: { color: '#2080f0' } }],
    })
  }

  if (professionChartRef.value) {
    const chart = echarts.init(professionChartRef.value)
    const entries = Object.entries(props.data.professionCounts)
    chart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie', radius: '60%',
        data: entries.map(([name, value]) => ({ name, value })),
      }],
    })
  }
}

onMounted(() => { nextTick(renderCharts) })
watch(() => props.data, () => { nextTick(renderCharts) }, { deep: true })
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/components/PopulationPreview.vue
git commit -m "feat(ui): add PopulationPreview visualization component"
```

---

## Task 11: 基因组列表页

**Files:**
- Create: `web/app/pages/genomes/index.vue`

- [ ] **Step 1: 创建列表页面**

```vue
<!-- web/app/pages/genomes/index.vue -->
<template>
  <div>
    <PageHeader title="人格基因组" subtitle="管理和生成 Agent 人格基因组">
      <template #action>
        <n-space>
          <n-button type="primary" @click="$router.push('/genomes/create')">新建基因组</n-button>
          <n-button @click="$router.push('/genomes/breed')">群体繁殖</n-button>
        </n-space>
      </template>
    </PageHeader>

    <n-card>
      <n-space justify="space-between" align="center" style="margin-bottom: 16px">
        <n-select
          v-model:value="filterSource"
          :options="sourceOptions"
          placeholder="按来源筛选"
          clearable
          style="width: 200px"
          @update:value="loadList"
        />
      </n-space>

      <n-data-table
        :columns="columns"
        :data="store.items"
        :loading="store.loading"
        :row-key="(row: any) => row.id"
      />

      <n-space justify="center" style="margin-top: 16px">
        <n-pagination
          v-model:page="currentPage"
          :page-count="store.pagination.totalPages"
          @update:page="loadList"
        />
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { NButton, NSpace, NTag } from 'naive-ui'
import { useRouter } from 'vue-router'
import { useGenomesStore } from '~/stores/genomes'

const router = useRouter()
const store = useGenomesStore()
const currentPage = ref(1)
const filterSource = ref<string | null>(null)

const sourceOptions = [
  { label: '手动创建', value: 'manual' },
  { label: '文档提取', value: 'document' },
  { label: 'URL提取', value: 'url' },
  { label: 'CSV导入', value: 'csv' },
  { label: '自然语言', value: 'natural_language' },
  { label: '繁殖生成', value: 'breed' },
]

const sourceLabels: Record<string, string> = Object.fromEntries(sourceOptions.map(o => [o.value, o.label]))

const columns = [
  { title: '名称', key: 'name', ellipsis: { tooltip: true } },
  {
    title: '来源',
    key: 'sourceType',
    width: 120,
    render: (row: any) => h(NTag, { size: 'small', type: 'info' }, () => sourceLabels[row.sourceType] || row.sourceType),
  },
  {
    title: '标签',
    key: 'tags',
    width: 200,
    render: (row: any) => {
      const tags = row.tags || []
      return h(NSpace, { size: 'small' }, () => tags.slice(0, 3).map((t: string) => h(NTag, { size: 'tiny' }, () => t)))
    },
  },
  { title: '创建时间', key: 'createdAt', width: 180 },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render: (row: any) => h(NSpace, { size: 'small' }, () => [
      h(NButton, { text: true, type: 'primary', onClick: () => router.push(`/genomes/${row.id}`) }, () => '查看'),
      h(NButton, { text: true, type: 'error', onClick: () => handleDelete(row.id) }, () => '删除'),
    ]),
  },
]

async function loadList() {
  await store.fetchList({
    page: currentPage.value,
    sourceType: filterSource.value || undefined,
  })
}

async function handleDelete(id: string) {
  await store.remove(id)
  await loadList()
}

onMounted(() => loadList())
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/pages/genomes/index.vue
git commit -m "feat(ui): add genome list page"
```

---

## Task 12: 基因组创建页

**Files:**
- Create: `web/app/pages/genomes/create.vue`

- [ ] **Step 1: 创建基因组创建页面**

```vue
<!-- web/app/pages/genomes/create.vue -->
<template>
  <div>
    <PageHeader title="新建基因组" subtitle="从多种数据源创建人格基因组" />

    <n-card>
      <n-steps :current="step" style="margin-bottom: 24px">
        <n-step title="选择来源" />
        <n-step title="输入内容" />
        <n-step title="确认结果" />
      </n-steps>

      <!-- Step 1: 选择来源 -->
      <div v-if="step === 1">
        <n-radio-group v-model:value="sourceType" size="large">
          <n-space vertical :size="12">
            <n-radio value="natural_language">自然语言描述 — 用一段话描述人物画像</n-radio>
            <n-radio value="manual">手动配置 — 逐项填写人格参数</n-radio>
            <n-radio value="csv">CSV/JSON 导入 — 从结构化数据导入</n-radio>
          </n-space>
        </n-radio-group>
        <n-space justify="end" style="margin-top: 24px">
          <n-button type="primary" @click="step = 2">下一步</n-button>
        </n-space>
      </div>

      <!-- Step 2: 输入内容 -->
      <div v-if="step === 2">
        <n-form-item label="名称">
          <n-input v-model:value="name" placeholder="为这个基因组起个名字" />
        </n-form-item>

        <!-- 自然语言模式 -->
        <div v-if="sourceType === 'natural_language'">
          <n-form-item label="人物描述">
            <n-input
              v-model:value="textContent"
              type="textarea"
              :rows="6"
              placeholder="描述这个人物的性格、职业、兴趣、社交习惯等。例如：一个30岁的科技记者，性格外向，喜欢追踪AI和新能源领域的前沿动态，在社交媒体上非常活跃..."
            />
          </n-form-item>
        </div>

        <!-- 手动模式 -->
        <div v-if="sourceType === 'manual'">
          <n-h4>五大人格特质</n-h4>
          <n-grid :cols="2" :x-gap="16" :y-gap="8">
            <n-gi v-for="(label, key) in traitLabels" :key="key">
              <n-form-item :label="label">
                <n-slider v-model:value="manualGenome.traits[key]" :min="0" :max="1" :step="0.05" />
              </n-form-item>
            </n-gi>
          </n-grid>
          <n-h4>人口统计</n-h4>
          <n-grid :cols="2" :x-gap="16">
            <n-gi>
              <n-form-item label="职业">
                <n-input v-model:value="manualGenome.demographics.profession" />
              </n-form-item>
            </n-gi>
            <n-gi>
              <n-form-item label="MBTI">
                <n-select v-model:value="manualGenome.demographics.mbti" :options="mbtiOptions" />
              </n-form-item>
            </n-gi>
          </n-grid>
          <n-form-item label="兴趣（用逗号分隔）">
            <n-input v-model:value="interestsStr" placeholder="科技, 游戏, 金融" />
          </n-form-item>
        </div>

        <!-- CSV 模式 -->
        <div v-if="sourceType === 'csv'">
          <n-form-item label="粘贴 JSON 数据">
            <n-input
              v-model:value="csvContent"
              type="textarea"
              :rows="8"
              placeholder='{"name": "张三", "age": 30, "interests": "科技,游戏", "personality": "内向理性"}'
            />
          </n-form-item>
        </div>

        <n-space justify="space-between" style="margin-top: 24px">
          <n-button @click="step = 1">上一步</n-button>
          <n-button type="primary" :loading="extracting" @click="handleExtract">
            {{ sourceType === 'manual' ? '下一步' : 'AI 分析生成' }}
          </n-button>
        </n-space>
      </div>

      <!-- Step 3: 确认结果 -->
      <div v-if="step === 3 && resultGenome">
        <n-grid :cols="2" :x-gap="24">
          <n-gi>
            <GenomeRadar :traits="resultGenome.traits" title="人格特质雷达图" />
          </n-gi>
          <n-gi>
            <n-descriptions bordered :column="1" label-placement="left">
              <n-descriptions-item label="职业">{{ resultGenome.demographics.profession }}</n-descriptions-item>
              <n-descriptions-item label="MBTI">{{ resultGenome.demographics.mbti || '未知' }}</n-descriptions-item>
              <n-descriptions-item label="年龄范围">{{ resultGenome.demographics.age_range?.join('-') }}</n-descriptions-item>
              <n-descriptions-item label="兴趣">{{ resultGenome.demographics.interests?.join(', ') }}</n-descriptions-item>
              <n-descriptions-item label="活跃度">{{ resultGenome.social_behavior.activity_level }}</n-descriptions-item>
              <n-descriptions-item label="影响力">{{ resultGenome.social_behavior.influence_weight }}</n-descriptions-item>
            </n-descriptions>
          </n-gi>
        </n-grid>

        <n-space justify="space-between" style="margin-top: 24px">
          <n-button @click="step = 2">返回修改</n-button>
          <n-button type="primary" :loading="saving" @click="handleSave">保存基因组</n-button>
        </n-space>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useGenomesStore } from '~/stores/genomes'

const router = useRouter()
const message = useMessage()
const store = useGenomesStore()

const step = ref(1)
const sourceType = ref('natural_language')
const name = ref('')
const textContent = ref('')
const csvContent = ref('')
const extracting = ref(false)
const saving = ref(false)
const resultGenome = ref<any>(null)

const traitLabels: Record<string, string> = {
  openness: '开放性', conscientiousness: '尽责性', extraversion: '外向性',
  agreeableness: '宜人性', neuroticism: '神经质',
}

const mbtiOptions = ['INTJ','INTP','ENTJ','ENTP','INFJ','INFP','ENFJ','ENFP',
  'ISTJ','ISFJ','ESTJ','ESFJ','ISTP','ISFP','ESTP','ESFP'].map(v => ({ label: v, value: v }))

const manualGenome = ref({
  traits: { openness: 0.5, conscientiousness: 0.5, extraversion: 0.5, agreeableness: 0.5, neuroticism: 0.5 },
  social_behavior: { activity_level: 0.5, content_creation_ratio: 0.5, interaction_preference: 'balanced', influence_weight: 0.5, echo_chamber_tendency: 0.3 },
  opinion_spectrum: { topic_stances: {}, persuadability: 0.5, stance_volatility: 0.3 },
  demographics: { age_range: [20, 40], profession: '', interests: [] as string[], mbti: null as string | null },
  behavioral_patterns: { peak_activity_hours: [9, 12, 20], avg_post_length: 'medium', emoji_usage: 0.3, hashtag_usage: 0.3 },
})

const interestsStr = ref('')

async function handleExtract() {
  if (!name.value) { message.warning('请输入名称'); return }

  if (sourceType.value === 'manual') {
    manualGenome.value.demographics.interests = interestsStr.value.split(/[,，]/).map(s => s.trim()).filter(Boolean)
    resultGenome.value = manualGenome.value
    step.value = 3
    return
  }

  extracting.value = true
  try {
    const payload: any = { sourceType: sourceType.value }
    if (sourceType.value === 'natural_language') {
      payload.content = textContent.value
    } else if (sourceType.value === 'csv') {
      payload.structuredData = JSON.parse(csvContent.value)
    }
    const res = await store.extract(payload)
    if (res.code === 0) {
      resultGenome.value = res.data.genome
      step.value = 3
    } else {
      message.error(res.message)
    }
  } catch (e: any) {
    message.error('提取失败: ' + e.message)
  } finally {
    extracting.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const res = await store.create({
      name: name.value,
      sourceType: sourceType.value,
      genomeData: resultGenome.value,
    })
    if (res.code === 0) {
      message.success('基因组已保存')
      router.push('/genomes')
    } else {
      message.error(res.message)
    }
  } finally {
    saving.value = false
  }
}
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/pages/genomes/create.vue
git commit -m "feat(ui): add genome creation page with multi-source input"
```

---

## Task 13: 基因组详情页

**Files:**
- Create: `web/app/pages/genomes/[id].vue`

- [ ] **Step 1: 创建详情/编辑页面**

```vue
<!-- web/app/pages/genomes/[id].vue -->
<template>
  <div v-if="genome">
    <PageHeader :title="genome.name" :subtitle="`来源: ${sourceLabels[genome.sourceType] || genome.sourceType}`">
      <template #action>
        <n-space>
          <n-button @click="editing = !editing">{{ editing ? '取消编辑' : '编辑' }}</n-button>
          <n-button type="primary" v-if="editing" :loading="saving" @click="handleSave">保存</n-button>
        </n-space>
      </template>
    </PageHeader>

    <n-grid :cols="2" :x-gap="24">
      <n-gi>
        <n-card title="人格特质">
          <GenomeRadar :traits="genome.genomeData.traits" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="基本信息">
          <n-descriptions bordered :column="1" label-placement="left">
            <n-descriptions-item label="职业">{{ genome.genomeData.demographics?.profession }}</n-descriptions-item>
            <n-descriptions-item label="MBTI">{{ genome.genomeData.demographics?.mbti || '未知' }}</n-descriptions-item>
            <n-descriptions-item label="年龄范围">{{ genome.genomeData.demographics?.age_range?.join('-') }}</n-descriptions-item>
            <n-descriptions-item label="兴趣">{{ genome.genomeData.demographics?.interests?.join(', ') }}</n-descriptions-item>
            <n-descriptions-item label="活跃度">{{ genome.genomeData.social_behavior?.activity_level }}</n-descriptions-item>
            <n-descriptions-item label="影响力">{{ genome.genomeData.social_behavior?.influence_weight }}</n-descriptions-item>
            <n-descriptions-item label="信息茧房倾向">{{ genome.genomeData.social_behavior?.echo_chamber_tendency }}</n-descriptions-item>
          </n-descriptions>
        </n-card>
      </n-gi>
    </n-grid>

    <n-card title="原始数据" style="margin-top: 16px" v-if="!editing">
      <n-code :code="JSON.stringify(genome.genomeData, null, 2)" language="json" />
    </n-card>

    <n-card title="编辑基因组数据" style="margin-top: 16px" v-if="editing">
      <n-input
        v-model:value="editJson"
        type="textarea"
        :rows="20"
        font-family="monospace"
      />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useGenomesStore } from '~/stores/genomes'

const route = useRoute()
const message = useMessage()
const store = useGenomesStore()

const genome = ref<any>(null)
const editing = ref(false)
const saving = ref(false)
const editJson = ref('')

const sourceLabels: Record<string, string> = {
  manual: '手动创建', document: '文档提取', url: 'URL提取',
  csv: 'CSV导入', natural_language: '自然语言', breed: '繁殖生成',
}

onMounted(async () => {
  const res = await store.fetchOne(route.params.id as string)
  if (res.code === 0) {
    genome.value = res.data
    editJson.value = JSON.stringify(res.data.genomeData, null, 2)
  }
})

async function handleSave() {
  saving.value = true
  try {
    const parsed = JSON.parse(editJson.value)
    const res = await store.update(genome.value.id, { genomeData: parsed })
    if (res.code === 0) {
      genome.value.genomeData = parsed
      editing.value = false
      message.success('已保存')
    } else {
      message.error(res.message)
    }
  } catch (e: any) {
    message.error('JSON 格式错误')
  } finally {
    saving.value = false
  }
}
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/pages/genomes/[id].vue
git commit -m "feat(ui): add genome detail/edit page"
```

---

## Task 14: 群体繁殖页

**Files:**
- Create: `web/app/pages/genomes/breed.vue`

- [ ] **Step 1: 创建繁殖配置页**

```vue
<!-- web/app/pages/genomes/breed.vue -->
<template>
  <div>
    <PageHeader title="群体繁殖" subtitle="从种子基因组批量生成多样化 Agent 群体" />

    <n-grid :cols="2" :x-gap="24">
      <n-gi>
        <n-card title="繁殖配置">
          <n-form label-placement="left" label-width="100">
            <n-form-item label="批次名称">
              <n-input v-model:value="batchName" placeholder="例如：科技博主群体" />
            </n-form-item>

            <n-form-item label="种子基因组">
              <n-select
                v-model:value="selectedSeeds"
                :options="seedOptions"
                multiple
                placeholder="选择种子基因组（至少1个）"
                :loading="loadingSeeds"
              />
            </n-form-item>

            <n-form-item label="目标数量">
              <n-input-number v-model:value="targetCount" :min="1" :max="10000" />
            </n-form-item>

            <n-form-item label="突变率">
              <n-slider v-model:value="mutationRate" :min="0" :max="0.5" :step="0.01" />
              <n-text depth="3" style="margin-left: 8px">{{ mutationRate }}</n-text>
            </n-form-item>

            <n-form-item label="繁殖策略">
              <n-radio-group v-model:value="strategy">
                <n-space>
                  <n-radio value="crossover">交叉繁殖</n-radio>
                  <n-radio value="clone_mutate">克隆突变</n-radio>
                  <n-radio value="distribution">分布采样</n-radio>
                </n-space>
              </n-radio-group>
            </n-form-item>

            <n-space justify="end">
              <n-button type="primary" :loading="breeding" @click="handleBreed" :disabled="selectedSeeds.length === 0">
                开始繁殖
              </n-button>
            </n-space>
          </n-form>
        </n-card>
      </n-gi>

      <n-gi>
        <PopulationPreview :data="previewData" />

        <n-card title="繁殖结果" v-if="breedResult" style="margin-top: 16px">
          <n-space vertical>
            <n-statistic label="生成数量" :value="breedResult.count" />
            <n-statistic label="多样性指数" :value="breedResult.diversity" />
            <n-button type="primary" @click="$router.push('/genomes')">查看基因组列表</n-button>
          </n-space>
        </n-card>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useGenomesStore } from '~/stores/genomes'

const message = useMessage()
const store = useGenomesStore()

const batchName = ref('')
const selectedSeeds = ref<string[]>([])
const targetCount = ref(50)
const mutationRate = ref(0.15)
const strategy = ref('crossover')
const breeding = ref(false)
const loadingSeeds = ref(false)
const seedOptions = ref<any[]>([])
const previewData = ref<any>(null)
const breedResult = ref<any>(null)

onMounted(async () => {
  loadingSeeds.value = true
  await store.fetchList({ pageSize: 100 })
  seedOptions.value = store.items.map(g => ({ label: g.name, value: g.id }))
  loadingSeeds.value = false
})

async function handleBreed() {
  if (!batchName.value) { message.warning('请输入批次名称'); return }
  if (selectedSeeds.value.length === 0) { message.warning('请选择至少一个种子基因组'); return }

  breeding.value = true
  try {
    const res = await store.breed({
      name: batchName.value,
      seedGenomeIds: selectedSeeds.value,
      targetCount: targetCount.value,
      mutationRate: mutationRate.value,
      strategy: strategy.value,
    })
    if (res.code === 0) {
      breedResult.value = res.data
      message.success(`成功生成 ${res.data.count} 个基因组`)
      await loadPreview(res.data.genomeIds)
    } else {
      message.error(res.message)
    }
  } finally {
    breeding.value = false
  }
}

async function loadPreview(genomeIds: string[]) {
  await store.fetchList({ pageSize: 100 })
  const genomes = store.items
    .filter(g => genomeIds.includes(g.id))
    .map(g => g.genomeData)
  if (genomes.length > 0) {
    const res = await store.preview(genomes)
    if (res.code === 0) {
      previewData.value = res.data
    }
  }
}
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/pages/genomes/breed.vue
git commit -m "feat(ui): add genome breeding page with population preview"
```

---

## Task 15: 侧边栏导航更新

**Files:**
- Modify: `web/app/layouts/default.vue`

- [ ] **Step 1: 在侧边栏菜单中添加基因组导航项**

在 `web/app/layouts/default.vue` 的菜单数据中，在仿真和报告之间添加基因组菜单项：

```typescript
{
  label: '基因组',
  key: 'genomes',
  icon: renderIcon('carbon:dna'),
  children: [
    { label: '基因组列表', key: '/genomes', path: '/genomes' },
    { label: '新建基因组', key: '/genomes/create', path: '/genomes/create' },
    { label: '群体繁殖', key: '/genomes/breed', path: '/genomes/breed' },
  ],
}
```

具体位置：查看 `default.vue` 中的 `menuOptions` 数组，在 simulations 和 reports 菜单项之间插入上述对象。如果使用的是 `renderIcon` 函数，保持同样的 icon 渲染模式。

- [ ] **Step 2: 提交**

```bash
git add web/app/layouts/default.vue
git commit -m "feat(ui): add genome navigation to sidebar menu"
```

---

## Task 16: 集成测试与验证

- [ ] **Step 1: 启动 Engine 验证基因组端点**

Run: `cd D:/NLP/oasis && python -m uvicorn engine.main:app --host 0.0.0.0 --port 8000`

测试繁殖端点:
```bash
curl -X POST http://localhost:8000/engine/genomes/breed \
  -H "Content-Type: application/json" \
  -H "X-Internal-Key: dev-internal-key" \
  -d '{
    "seeds": [{"traits":{"openness":0.8,"conscientiousness":0.6,"extraversion":0.5,"agreeableness":0.5,"neuroticism":0.3},"social_behavior":{"activity_level":0.7,"content_creation_ratio":0.5,"interaction_preference":"balanced","influence_weight":0.5,"echo_chamber_tendency":0.3},"opinion_spectrum":{"topic_stances":{},"persuadability":0.5,"stance_volatility":0.3},"demographics":{"age_range":[20,30],"profession":"student","interests":["tech"],"mbti":"INTP"},"behavioral_patterns":{"peak_activity_hours":[9,21],"avg_post_length":"medium","emoji_usage":0.3,"hashtag_usage":0.3}}],
    "target_count": 5,
    "mutation_rate": 0.15,
    "strategy": "clone_mutate"
  }'
```

Expected: 200 响应，包含 5 个基因组和 diversity 分数

- [ ] **Step 2: 启动 Web 验证前端页面**

Run: `cd D:/NLP/oasis/web && npm run dev`

验证以下页面:
1. 访问 `/genomes` — 空列表正常显示
2. 访问 `/genomes/create` — 三步向导正常运行
3. 手动创建一个基因组 — 雷达图正确渲染
4. 访问 `/genomes/breed` — 繁殖配置页正常
5. 侧边栏「基因组」菜单项正确显示

- [ ] **Step 3: 运行所有 Engine 测试**

Run: `cd D:/NLP/oasis && python -m pytest engine/tests/test_genome_*.py -v`
Expected: 所有测试 PASS

- [ ] **Step 4: 提交最终集成验证**

```bash
git add -A
git commit -m "feat(genome): complete P0-1 persona genome system integration"
```
