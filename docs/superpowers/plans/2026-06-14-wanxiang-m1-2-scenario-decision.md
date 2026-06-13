# 万象 WANXIANG · M1-2 ScenarioConfig 与单 agent 决策运行器 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 建立 `ScenarioConfig`（场景：给虚拟人看什么 + 问什么 + 期望什么类型的决策）、`DecisionResult`（结构化决策结果）和 `DecisionRunner`（把 persona + scenario → 调用模型 → 解析为 DecisionResult）。**仍不直接依赖 camel/LLM**——`DecisionRunner` 接受一个最小的 `ModelCall` 协议（`async (messages) -> str`），真实用 camel 时由调用方做薄适配；测试用 stub。

**Architecture:** 纯数据 + 一个薄协调器：`DecisionRunner.run(persona, scenario, model_call)` 内部把 persona.render_system_prompt() 作为 system message、scenario 的材料+问题作为 user message、要求 LLM 返回严格 JSON（schema 由 scenario.decision_kind 决定），用 `json.loads` 解析，构造 `DecisionResult`。失败/格式错时返回带 `error` 字段的 DecisionResult，绝不抛异常打断批量执行（M1-3 要靠这一点）。

**Tech Stack:** Python 3.11 + stdlib (`json`, `re`, `typing.Protocol`)。**仅依赖**已有的 `wanxiang.personas.Persona`。

M1 第二个子计划。M1-3 将做"批量并发 + 聚合"，M1-4 接入轻量真实分布。

---

## 文件结构
- `wanxiang/simulation/__init__.py` — 占位（Task 1 后补全导出）
- `wanxiang/simulation/scenario.py` — `ScenarioConfig`, `DecisionKind`
- `wanxiang/simulation/decision.py` — `DecisionResult`, `ModelCall` 协议, `DecisionRunner`
- `test/wanxiang/test_scenario.py`
- `test/wanxiang/test_decision_runner.py`

---

## Task 1: ScenarioConfig + DecisionKind 枚举

**Files:**
- Create: `wanxiang/simulation/__init__.py`（占位）
- Create: `wanxiang/simulation/scenario.py`
- Test: `test/wanxiang/test_scenario.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_scenario.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import pytest

from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def test_scenario_basic_fields():
    s = ScenarioConfig(
        material="新品「轻气泡」无糖气泡水，青提口味，定价 ¥6/瓶。",
        question="你会购买吗？给出 0-10 的购买意愿评分。",
        decision_kind=DecisionKind.RATE,
    )
    assert "轻气泡" in s.material
    assert s.decision_kind is DecisionKind.RATE


def test_scenario_choose_kind_requires_options():
    s = ScenarioConfig(
        material="三种口味：青提 / 白桃 / 海盐荔枝。",
        question="你最想买哪种？",
        decision_kind=DecisionKind.CHOOSE,
        options=("青提", "白桃", "海盐荔枝"),
    )
    assert s.options == ("青提", "白桃", "海盐荔枝")


def test_choose_without_options_raises():
    with pytest.raises(ValueError, match="CHOOSE.*options"):
        ScenarioConfig(
            material="材料", question="选一个", decision_kind=DecisionKind.CHOOSE)


def test_non_choose_kinds_allow_no_options():
    # RATE/SENTIMENT/CLICK_PROBABILITY/WTP 不需要 options
    for kind in [DecisionKind.RATE, DecisionKind.SENTIMENT,
                 DecisionKind.CLICK_PROBABILITY, DecisionKind.WTP]:
        s = ScenarioConfig(material="m", question="q", decision_kind=kind)
        assert s.options is None


def test_scenario_render_user_message_includes_material_and_question():
    s = ScenarioConfig(material="材料X", question="问题Y",
                       decision_kind=DecisionKind.RATE)
    msg = s.render_user_message()
    assert "材料X" in msg and "问题Y" in msg
    # RATE 要求模型返回 JSON 含 score
    assert "score" in msg.lower() or "评分" in msg


def test_scenario_choose_render_includes_options_and_option_key():
    s = ScenarioConfig(
        material="m", question="q", decision_kind=DecisionKind.CHOOSE,
        options=("A", "B", "C"))
    msg = s.render_user_message()
    assert "A" in msg and "B" in msg and "C" in msg
    assert "option" in msg.lower() or "选项" in msg
```

- [ ] **Step 2: 运行确认失败**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_scenario.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: 实现 scenario.py**

`wanxiang/simulation/__init__.py`（占位）:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""simulation: 场景配置与决策运行器（spec §M3/M4 decision_only）。"""

__all__: list[str] = []
```

`wanxiang/simulation/scenario.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""场景配置：给虚拟人看什么、问什么、期望什么类型的决策输出。

DecisionKind 对应 L1 决策响应动作（spec §5.1）：
- RATE: 0-10 整数评分 → 字段 score
- CHOOSE: 多选一 → 字段 option（必须在 options 中）
- CLICK_PROBABILITY: 0-1 → 字段 probability
- SENTIMENT: -1..1 → 字段 polarity
- WTP: 愿意支付的价格（数字） → 字段 price
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DecisionKind(Enum):
    RATE = "rate"
    CHOOSE = "choose"
    CLICK_PROBABILITY = "click_probability"
    SENTIMENT = "sentiment"
    WTP = "willingness_to_pay"


_SCHEMA_HINT = {
    DecisionKind.RATE: '{"score": <0-10 整数>}',
    DecisionKind.CHOOSE: '{"option": "<必须是给定 options 之一>"}',
    DecisionKind.CLICK_PROBABILITY: '{"probability": <0-1 小数>}',
    DecisionKind.SENTIMENT: '{"polarity": <-1 到 1 小数>}',
    DecisionKind.WTP: '{"price": <非负数字，单位元>}',
}


@dataclass(frozen=True)
class ScenarioConfig:
    material: str
    question: str
    decision_kind: DecisionKind
    options: tuple[str, ...] | None = None

    def __post_init__(self):
        if self.decision_kind is DecisionKind.CHOOSE and not self.options:
            raise ValueError(
                "CHOOSE decision_kind requires non-empty options tuple")

    def render_user_message(self) -> str:
        parts: list[str] = []
        parts.append("【材料】")
        parts.append(self.material)
        if self.decision_kind is DecisionKind.CHOOSE and self.options:
            parts.append("【可选项】" + " / ".join(self.options))
        parts.append("【问题】" + self.question)
        parts.append(
            "请只用一行严格 JSON 回答，格式："
            f"{_SCHEMA_HINT[self.decision_kind]}。"
            "不要添加任何解释、前后缀或代码块标记。")
        return "\n".join(parts)
```

- [ ] **Step 4: 运行确认通过**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_scenario.py -v` → 6 passed

- [ ] **Step 5: Commit**
```bash
cd "D:\NLp\oasis"
git add wanxiang/simulation/__init__.py wanxiang/simulation/scenario.py test/wanxiang/test_scenario.py
git commit -m "feat(wanxiang): add ScenarioConfig and DecisionKind for L1 decisions"
```
End with trailing blank line then: Co-Authored-By: Claude <noreply@anthropic.com>

---

## Task 2: DecisionResult + DecisionRunner

**Files:**
- Create: `wanxiang/simulation/decision.py`
- Modify: `wanxiang/simulation/__init__.py`（导出全部）
- Test: `test/wanxiang/test_decision_runner.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_decision_runner.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import asyncio

import pytest

from wanxiang.personas.persona import Persona
from wanxiang.simulation.decision import DecisionResult, DecisionRunner
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _persona(agent_id=0, name="阿哲"):
    return Persona(agent_id=agent_id, name=name,
                   demographic={"年龄": 25, "城市": "上海"},
                   personality={"价格敏感度": 0.4},
                   media={"小红书": 0.8})


def _scenario_rate():
    return ScenarioConfig(material="新品 ¥6", question="买不买，0-10 评分",
                          decision_kind=DecisionKind.RATE)


def _scenario_choose():
    return ScenarioConfig(material="三口味", question="挑一个",
                          decision_kind=DecisionKind.CHOOSE,
                          options=("青提", "白桃", "海盐荔枝"))


def _make_call(response_text):
    """构造一个 stub 模型调用：忽略 messages，固定返回 response_text。"""
    captured = {"messages": None}

    async def call(messages):
        captured["messages"] = messages
        return response_text

    return call, captured


# ---- 基本 happy path ----

def test_runner_returns_decision_result_for_rate():
    call, captured = _make_call('{"score": 7}')
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_rate(), call))
    assert isinstance(res, DecisionResult)
    assert res.agent_id == 0
    assert res.kind is DecisionKind.RATE
    assert res.value == 7
    assert res.error is None


def test_runner_returns_decision_result_for_choose():
    call, _ = _make_call('{"option": "白桃"}')
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_choose(), call))
    assert res.kind is DecisionKind.CHOOSE
    assert res.value == "白桃"
    assert res.error is None


def test_runner_passes_system_and_user_messages_to_model():
    call, captured = _make_call('{"score": 5}')
    runner = DecisionRunner()
    asyncio.run(runner.run(_persona(name="小张"), _scenario_rate(), call))
    msgs = captured["messages"]
    assert isinstance(msgs, list) and len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert "小张" in msgs[0]["content"]
    assert msgs[1]["role"] == "user"
    assert "新品" in msgs[1]["content"]


# ---- 容错：返回非 JSON / JSON 字段缺失 / value 非法 ----

def test_malformed_json_returns_error_result_not_raise():
    call, _ = _make_call("我觉得 6 分")  # 不是 JSON
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_rate(), call))
    assert res.value is None
    assert res.error and "json" in res.error.lower()


def test_missing_required_field_returns_error_result():
    call, _ = _make_call('{"foo": 1}')  # RATE 期望 score
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_rate(), call))
    assert res.value is None
    assert res.error and "score" in res.error


def test_choose_value_not_in_options_returns_error_result():
    call, _ = _make_call('{"option": "百香果"}')  # 不在 options 内
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_choose(), call))
    assert res.value is None
    assert res.error and "options" in res.error


# ---- json 容错：模型有时会包代码块 ```json ... ``` ----

def test_runner_strips_code_fence_around_json():
    call, _ = _make_call('```json\n{"score": 9}\n```')
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_rate(), call))
    assert res.value == 9
    assert res.error is None


# ---- 模型本身抛异常时 ----

def test_runner_captures_model_exception():
    async def call(messages):
        raise RuntimeError("network down")
    runner = DecisionRunner()
    res = asyncio.run(runner.run(_persona(), _scenario_rate(), call))
    assert res.value is None
    assert res.error and "network down" in res.error
```

- [ ] **Step 2: 运行确认失败**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_decision_runner.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: 实现 decision.py**

`wanxiang/simulation/decision.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""DecisionRunner: persona + scenario → 调模型 → 解析 → DecisionResult。

输入侧：不依赖具体 LLM SDK，只要求一个 `async (messages) -> str` 的可
调用。真实用 camel 时由调用方做一层薄适配。
输出侧：DecisionResult 永远返回，错误装入 error 字段——不抛异常打断
M1-3 的批量并发。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from wanxiang.personas.persona import Persona
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig

ModelCall = Callable[[list[dict]], Awaitable[str]]

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class DecisionResult:
    agent_id: int
    kind: DecisionKind
    value: Any  # int/str/float, 由 kind 决定；解析失败时为 None
    raw: str    # 模型原始输出（用于审计）
    error: str | None = None


# 每个 kind 期望从 JSON 里取的字段名
_FIELD_FOR_KIND = {
    DecisionKind.RATE: "score",
    DecisionKind.CHOOSE: "option",
    DecisionKind.CLICK_PROBABILITY: "probability",
    DecisionKind.SENTIMENT: "polarity",
    DecisionKind.WTP: "price",
}


class DecisionRunner:

    async def run(
        self,
        persona: Persona,
        scenario: ScenarioConfig,
        model_call: ModelCall,
    ) -> DecisionResult:
        messages = [
            {"role": "system", "content": persona.render_system_prompt()},
            {"role": "user", "content": scenario.render_user_message()},
        ]
        try:
            raw = await model_call(messages)
        except Exception as e:  # noqa: BLE001
            return DecisionResult(
                agent_id=persona.agent_id, kind=scenario.decision_kind,
                value=None, raw="", error=f"model call failed: {e}")

        # 去掉 ```json ... ``` 围栏（模型常见格式）
        stripped = _CODE_FENCE_RE.sub("", raw).strip()
        try:
            data = json.loads(stripped)
        except (json.JSONDecodeError, ValueError) as e:
            return DecisionResult(
                agent_id=persona.agent_id, kind=scenario.decision_kind,
                value=None, raw=raw, error=f"invalid json: {e}")

        field = _FIELD_FOR_KIND[scenario.decision_kind]
        if not isinstance(data, dict) or field not in data:
            return DecisionResult(
                agent_id=persona.agent_id, kind=scenario.decision_kind,
                value=None, raw=raw,
                error=f"missing required field {field!r} in model output")

        value = data[field]
        # CHOOSE 必须在 options 中
        if scenario.decision_kind is DecisionKind.CHOOSE:
            if value not in (scenario.options or ()):
                return DecisionResult(
                    agent_id=persona.agent_id, kind=scenario.decision_kind,
                    value=None, raw=raw,
                    error=(f"choice {value!r} not in declared options "
                           f"{scenario.options}"))

        return DecisionResult(
            agent_id=persona.agent_id, kind=scenario.decision_kind,
            value=value, raw=raw, error=None)
```

- [ ] **Step 4: 运行确认通过**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_decision_runner.py -v` → 8 passed

- [ ] **Step 5: 补全 simulation/__init__.py**
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""simulation: 场景配置与决策运行器（spec §M3/M4 decision_only）。"""
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig
from wanxiang.simulation.decision import (DecisionResult, DecisionRunner,
                                          ModelCall)

__all__ = ["DecisionKind", "ScenarioConfig",
           "DecisionResult", "DecisionRunner", "ModelCall"]
```
验证：`/d/software/conda_data/envs/oasis/python.exe -c "from wanxiang.simulation import DecisionRunner, ScenarioConfig, DecisionKind; print('OK')"` → `OK`

- [ ] **Step 6: 全量回归**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/ -q` → 73 + 6 + 8 = 87 passed

- [ ] **Step 7: Commit**
```bash
cd "D:\NLp\oasis"
git add wanxiang/simulation/decision.py wanxiang/simulation/__init__.py test/wanxiang/test_decision_runner.py
git commit -m "feat(wanxiang): add DecisionRunner with robust JSON parsing"
```
End with trailing blank line then: Co-Authored-By: Claude <noreply@anthropic.com>

---

## 完成标准（Definition of Done）
- [ ] `from wanxiang.simulation import ScenarioConfig, DecisionKind, DecisionRunner, DecisionResult, ModelCall` 可用
- [ ] `ScenarioConfig` 五种 DecisionKind 都能渲染合法 user message
- [ ] `DecisionRunner.run()` 能从 stub model 解析 JSON 决策；JSON 错/字段缺/选项非法/模型异常 → 返回带 error 的 DecisionResult，不抛
- [ ] `test/wanxiang/` 87 passed
- [ ] 仍不依赖 camel/oasis/LLM 真实调用
