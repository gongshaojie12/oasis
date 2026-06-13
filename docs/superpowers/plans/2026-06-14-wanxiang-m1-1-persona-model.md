# 万象 WANXIANG · M1-1 Persona 数据模型与简单建造器 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 建立 `Persona`（虚拟人画像）数据模型与 `PersonaBuilder`（从配置字典/分布抽样批量造人），把 spec §M2 设计的"220+ 维特质（人口标签 + 个性向量 + 媒体消费习惯）"固化为可单元测试的纯 Python 数据契约，并能拼出供 LLM 使用的 system prompt 文本。**不接 LLM、不接 DB、不接 OASIS**，纯数据层。

**Architecture:** `Persona` 是冻结 `@dataclass`，三组特质各自一个 `dict[str, Any]`（demographic / personality / media）+ 一个 `name`/`agent_id`。`render_system_prompt()` 把画像按一致格式拼成中文 system prompt 文本，供后续 LLM 调用（spec §6 路径"NL → SimulationConfig → 造人 → 模拟"的左半侧）。`PersonaBuilder` 提供两种造人方式：(1) 单个 `build(spec)` 从精确字典造一个；(2) `sample(distribution, n, seed)` 按各维度独立分布抽样造 N 个（含确定性随机种子，方便测试）。

**Tech Stack:** Python 3.11（oasis conda 环境），dataclasses, random（stdlib only）。运行解释器：`/d/software/conda_data/envs/oasis/python.exe`（见记忆 python-env）。

M1 的**第一个子计划**。后续：M1-2（场景配置 + decision_only 单 agent LLM 调用），M1-3（批量并发 + 聚合成分布），M1-4（接入轻量真实分布数据：国家统计局年鉴片段）。每个独立交付。

---

## 文件结构

- `wanxiang/personas/__init__.py` — 导出 `Persona`, `PersonaBuilder`
- `wanxiang/personas/persona.py` — `Persona` 冻结 dataclass + `render_system_prompt()`
- `wanxiang/personas/builder.py` — `PersonaBuilder` 单造 + 批量抽样
- `test/wanxiang/test_persona.py` — Persona 行为与 render
- `test/wanxiang/test_persona_builder.py` — 单造 + 抽样确定性

---

## Task 1: Persona 数据模型 + 渲染

**Files:**
- Create: `wanxiang/personas/__init__.py` —— 占位（仅 docstring + `__all__ = []`），Task 2 完成后再补
- Create: `wanxiang/personas/persona.py`
- Test: `test/wanxiang/test_persona.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_persona.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import pytest

from wanxiang.personas.persona import Persona


def make_basic(**overrides):
    base = dict(
        agent_id=0,
        name="小张",
        demographic={"年龄": 25, "性别": "男", "城市": "上海", "月收入": 12000},
        personality={"价格敏感度": 0.4, "尝鲜意愿": 0.7, "健康意识": 0.6},
        media={"小红书": 0.5, "抖音": 0.8, "微信": 0.9},
    )
    base.update(overrides)
    return Persona(**base)


def test_persona_is_frozen():
    p = make_basic()
    with pytest.raises(Exception):  # FrozenInstanceError
        p.name = "改了"  # type: ignore


def test_persona_trait_count_exposes_total_dimensions():
    p = make_basic()
    # 4 人口 + 3 个性 + 3 媒体 = 10
    assert p.trait_count() == 10


def test_render_system_prompt_includes_name_and_key_traits():
    p = make_basic()
    prompt = p.render_system_prompt()
    # 名字与关键字段都应出现在 prompt 中
    assert "小张" in prompt
    assert "25" in prompt
    assert "上海" in prompt
    assert "价格敏感度" in prompt
    assert "小红书" in prompt


def test_render_system_prompt_returns_str():
    p = make_basic()
    assert isinstance(p.render_system_prompt(), str)


def test_empty_trait_groups_render_safely():
    p = Persona(agent_id=1, name="阿哲",
                demographic={}, personality={}, media={})
    out = p.render_system_prompt()
    assert "阿哲" in out
    # 空组不应崩，但应有可识别的占位文案
    assert isinstance(out, str) and len(out) > 0


def test_persona_equality_by_value():
    a = make_basic()
    b = make_basic()
    assert a == b
    c = make_basic(name="不同")
    assert a != c
```

- [ ] **Step 2: 运行确认失败**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_persona.py -v`
Expected: `ModuleNotFoundError: No module named 'wanxiang.personas'`

- [ ] **Step 3: 创建包占位 + 实现 persona.py**

`wanxiang/personas/__init__.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""personas: 虚拟人画像与建造器（spec §M2）。"""

__all__: list[str] = []
```

`wanxiang/personas/persona.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Persona: 一个虚拟人的完整画像（冻结、可值比较）。

spec §M2 三组特质：
- demographic: 人口标签（年龄/性别/城市/收入/职业/教育 …）
- personality: 个性向量（价格敏感度/尝鲜意愿/健康意识/从众倾向 …）
- media:       媒体消费习惯（小红书/抖音/微信/B站/微博 … 权重 0-1）

每个 group 是 dict[str, Any]，键名由调用方决定（spec 目标 220+ 维，
本数据层不约束维度数，只提供容器与一致的 system prompt 渲染）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Persona:
    agent_id: int
    name: str
    demographic: dict[str, Any] = field(default_factory=dict)
    personality: dict[str, Any] = field(default_factory=dict)
    media: dict[str, Any] = field(default_factory=dict)

    def trait_count(self) -> int:
        """三组特质合计维数（不含 name/agent_id）。"""
        return len(self.demographic) + len(self.personality) + len(self.media)

    def render_system_prompt(self) -> str:
        """把画像渲染为中文 system prompt 文本，供 LLM 调用。"""
        parts: list[str] = []
        parts.append(f"你是「{self.name}」。")
        if self.demographic:
            parts.append("【人口特征】")
            for k, v in self.demographic.items():
                parts.append(f"- {k}：{v}")
        else:
            parts.append("【人口特征】（未提供）")
        if self.personality:
            parts.append("【个性与决策倾向】（0-1 区间，越大越显著）")
            for k, v in self.personality.items():
                parts.append(f"- {k}：{v}")
        else:
            parts.append("【个性与决策倾向】（未提供）")
        if self.media:
            parts.append("【媒体消费习惯】（0-1 区间，越大越常用/越信任）")
            for k, v in self.media.items():
                parts.append(f"- {k}：{v}")
        else:
            parts.append("【媒体消费习惯】（未提供）")
        parts.append(
            "请基于以上画像，在被问到任何决策、态度或选择时，按这个人的"
            "真实视角作答；不要解释你是 AI，不要复述画像。")
        return "\n".join(parts)
```

- [ ] **Step 4: 运行确认通过**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_persona.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
cd "D:\NLp\oasis"
git add wanxiang/personas/__init__.py wanxiang/personas/persona.py test/wanxiang/test_persona.py
git commit -m "feat(wanxiang): add Persona dataclass with system-prompt rendering"
```
End commit message with trailing blank line then:
Co-Authored-By: Claude <noreply@anthropic.com>

---

## Task 2: PersonaBuilder 单造 + 抽样

**Files:**
- Create: `wanxiang/personas/builder.py`
- Modify: `wanxiang/personas/__init__.py`（导出 Persona + PersonaBuilder）
- Test: `test/wanxiang/test_persona_builder.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_persona_builder.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from collections import Counter

import pytest

from wanxiang.personas.builder import PersonaBuilder
from wanxiang.personas.persona import Persona


# ---- 单个 build ----

def test_build_single_persona_from_spec():
    pb = PersonaBuilder()
    p = pb.build(
        agent_id=42,
        name="小K",
        demographic={"年龄": 22, "城市": "北京"},
        personality={"尝鲜意愿": 0.8},
        media={"小红书": 0.6},
    )
    assert isinstance(p, Persona)
    assert p.agent_id == 42
    assert p.name == "小K"
    assert p.demographic["城市"] == "北京"


# ---- 批量 sample ----

# 一个最小可用的分布配置：
# 每个 group 内每个特质 -> 候选 (value, weight) 列表；权重和无需为 1，按比例归一。
SIMPLE_DIST = {
    "demographic": {
        "性别": [("男", 0.5), ("女", 0.5)],
        "城市": [("北京", 0.4), ("上海", 0.6)],
    },
    "personality": {
        "价格敏感度": [(0.2, 0.3), (0.5, 0.4), (0.8, 0.3)],
    },
    "media": {
        "小红书": [(0.0, 0.5), (0.7, 0.5)],
    },
}


def test_sample_returns_n_personas():
    pb = PersonaBuilder()
    ps = pb.sample(SIMPLE_DIST, n=20, seed=123)
    assert len(ps) == 20
    assert all(isinstance(p, Persona) for p in ps)


def test_sample_assigns_unique_sequential_ids_starting_from_zero():
    pb = PersonaBuilder()
    ps = pb.sample(SIMPLE_DIST, n=5, seed=7)
    ids = [p.agent_id for p in ps]
    assert ids == [0, 1, 2, 3, 4]


def test_sample_is_deterministic_with_same_seed():
    pb = PersonaBuilder()
    a = pb.sample(SIMPLE_DIST, n=50, seed=2026)
    b = pb.sample(SIMPLE_DIST, n=50, seed=2026)
    # 完全相同
    assert [p.demographic for p in a] == [p.demographic for p in b]
    assert [p.personality for p in a] == [p.personality for p in b]
    assert [p.media for p in a] == [p.media for p in b]


def test_sample_different_seeds_produce_different_results():
    pb = PersonaBuilder()
    a = pb.sample(SIMPLE_DIST, n=50, seed=1)
    b = pb.sample(SIMPLE_DIST, n=50, seed=2)
    assert [p.demographic for p in a] != [p.demographic for p in b]


def test_sample_distribution_approximates_weights():
    """20000 次抽样后，城市'上海'的占比应接近 0.6（±0.03）。"""
    pb = PersonaBuilder()
    ps = pb.sample(SIMPLE_DIST, n=20000, seed=999)
    counter = Counter(p.demographic["城市"] for p in ps)
    shanghai_ratio = counter["上海"] / 20000
    assert 0.57 <= shanghai_ratio <= 0.63, (
        f"shanghai_ratio={shanghai_ratio} 不在 0.6±0.03 范围内")


def test_sample_default_name_template():
    """未指定 name_prefix 时，name 按默认模板生成且包含 agent_id。"""
    pb = PersonaBuilder()
    ps = pb.sample(SIMPLE_DIST, n=3, seed=1)
    names = [p.name for p in ps]
    assert all(str(p.agent_id) in p.name for p in ps), names


def test_sample_with_name_prefix():
    pb = PersonaBuilder()
    ps = pb.sample(SIMPLE_DIST, n=3, seed=1, name_prefix="测试")
    for p in ps:
        assert p.name.startswith("测试")
```

- [ ] **Step 2: 运行确认失败**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_persona_builder.py -v`
Expected: `ModuleNotFoundError: No module named 'wanxiang.personas.builder'`

- [ ] **Step 3: 实现 builder.py**

`wanxiang/personas/builder.py`：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PersonaBuilder: 从精确字典或加权分布造虚拟人。

分布字典格式（每个 group 内每个特质独立给候选 (value, weight)）：

    {
        "demographic": {"性别": [("男", 0.5), ("女", 0.5)], ...},
        "personality": {"价格敏感度": [(0.2, 0.3), (0.5, 0.4), (0.8, 0.3)], ...},
        "media":       {"小红书": [(0.0, 0.5), (0.7, 0.5)], ...},
    }

权重无需归一；按比例使用。`sample(..., seed=...)` 保证完全确定性。
"""
from __future__ import annotations

import random
from typing import Any

from wanxiang.personas.persona import Persona

_GROUP_NAMES = ("demographic", "personality", "media")


class PersonaBuilder:

    def build(
        self,
        agent_id: int,
        name: str,
        demographic: dict[str, Any] | None = None,
        personality: dict[str, Any] | None = None,
        media: dict[str, Any] | None = None,
    ) -> Persona:
        """从精确字典造一个 Persona。"""
        return Persona(
            agent_id=agent_id,
            name=name,
            demographic=dict(demographic or {}),
            personality=dict(personality or {}),
            media=dict(media or {}),
        )

    def sample(
        self,
        distribution: dict[str, dict[str, list[tuple[Any, float]]]],
        n: int,
        seed: int,
        name_prefix: str | None = None,
    ) -> list[Persona]:
        """按各维度独立分布抽样造 N 个 Persona。

        ID 从 0 起递增；name 默认形如 'agent#0' 或 '<prefix>#0'。
        """
        rng = random.Random(seed)
        # 预先把每个特质的 (values, weights) 抽出来，避免内循环重复构建
        prepared: dict[str, dict[str, tuple[list[Any], list[float]]]] = {}
        for group in _GROUP_NAMES:
            grp_dist = distribution.get(group, {}) or {}
            prepared[group] = {}
            for trait, choices in grp_dist.items():
                values = [v for v, _ in choices]
                weights = [w for _, w in choices]
                prepared[group][trait] = (values, weights)

        personas: list[Persona] = []
        for i in range(n):
            traits: dict[str, dict[str, Any]] = {g: {} for g in _GROUP_NAMES}
            for group, traits_map in prepared.items():
                for trait, (values, weights) in traits_map.items():
                    picked = rng.choices(values, weights=weights, k=1)[0]
                    traits[group][trait] = picked
            label = name_prefix if name_prefix is not None else "agent"
            personas.append(
                Persona(
                    agent_id=i,
                    name=f"{label}#{i}",
                    demographic=traits["demographic"],
                    personality=traits["personality"],
                    media=traits["media"],
                ))
        return personas
```

- [ ] **Step 4: 运行确认通过**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_persona_builder.py -v`
Expected: 8 passed

- [ ] **Step 5: 补全 personas/__init__.py 导出**

把 `wanxiang/personas/__init__.py` 改为：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""personas: 虚拟人画像与建造器（spec §M2）。"""
from wanxiang.personas.persona import Persona
from wanxiang.personas.builder import PersonaBuilder

__all__ = ["Persona", "PersonaBuilder"]
```

验证：`/d/software/conda_data/envs/oasis/python.exe -c "from wanxiang.personas import Persona, PersonaBuilder; print('OK')"` → 期望 `OK`

- [ ] **Step 6: 全量回归（确认未破坏 wanxiang 既有 59 + engine 子模块）**

Run: `/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/ -q`
Expected: 59 + 6 + 8 = 73 passed

- [ ] **Step 7: Commit**

```bash
cd "D:\NLp\oasis"
git add wanxiang/personas/builder.py wanxiang/personas/__init__.py test/wanxiang/test_persona_builder.py
git commit -m "feat(wanxiang): add PersonaBuilder with deterministic weighted sampling"
```
End commit message with trailing blank line then:
Co-Authored-By: Claude <noreply@anthropic.com>

---

## 完成标准（Definition of Done）

- [ ] `from wanxiang.personas import Persona, PersonaBuilder` 可用
- [ ] `Persona` 是冻结 dataclass，可值比较，能渲染中文 system prompt
- [ ] `PersonaBuilder.build()` 单造、`PersonaBuilder.sample()` 批量加权抽样确定性
- [ ] `test/wanxiang/` 73 passed（59 之前 + 6 persona + 8 builder）
- [ ] 不依赖 LLM/DB/oasis/camel；纯 Python stdlib + 已有 wanxiang 模块

## 下一个子计划（不在本计划范围）
- **M1-2**: ScenarioConfig + decision_only 单 agent LLM 调用（接入 camel ModelFactory，把 persona 的 system_prompt 喂给 LLM，解析结构化决策输出）
- **M1-3**: 批量并发 + 聚合（N 个 agent 并发跑 → 群体决策分布）
- **M1-4**: 接入轻量真实分布（国家统计局年鉴片段 → 校准 sample 输出）
