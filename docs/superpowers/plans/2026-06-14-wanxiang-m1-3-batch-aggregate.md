# 万象 WANXIANG · M1-3 批量并发与决策聚合 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** 在 M1-2 单 agent 决策的基础上，做 (1) `BatchRunner` 用 `asyncio.gather` + 信号量并发跑 N 个 agent，(2) `aggregate()` 把 `list[DecisionResult]` 聚合成"群体决策分布"（按 kind 不同输出 counts/mean/分位数等），整套 decision_only 主链端到端跑通。仍**不依赖真实 LLM**——用 stub model 验证机制；后续 M1-4 接 camel/DeepSeek。

**Architecture:**
- `BatchRunner.run_all(personas, scenario, model_call, concurrency=N)`：内部用 `asyncio.Semaphore(N)` 限并发，逐 persona 启动 `DecisionRunner.run`，`asyncio.gather` 收齐，**永远返回 N 个 DecisionResult**（M1-2 的 runner 已保证错误装 error 不抛）。
- `aggregate(results)`：路由到按 kind 不同的聚合器：
  - CHOOSE → `{"counts": {...}, "share": {...}, "top": "..."}`
  - RATE / CLICK_PROBABILITY / SENTIMENT / WTP → `{"n": .., "mean": .., "median": .., "p25": .., "p75": ..}`
  - 同时报告 `error_count` 与 `error_rate`（解析失败的不参与数值统计但要可见）
- 所有结果在内存，不写 DB（DB 是 M0-B-3 之后的"机制层"事，本里程碑先打通主链）

**Tech Stack:** Python 3.11 + stdlib (`asyncio`, `statistics`, `collections.Counter`)。只依赖已有的 `wanxiang.personas` 和 `wanxiang.simulation.{scenario, decision}`。

---

## 文件结构
- `wanxiang/simulation/batch.py` — `BatchRunner`
- `wanxiang/simulation/aggregate.py` — `aggregate()` 函数 + `AggregateReport` dataclass
- `wanxiang/simulation/__init__.py` — 追加导出
- `test/wanxiang/test_batch_runner.py`
- `test/wanxiang/test_aggregate.py`

---

## Task 1: BatchRunner（并发执行）

**Files:**
- Create: `wanxiang/simulation/batch.py`
- Test: `test/wanxiang/test_batch_runner.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_batch_runner.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import asyncio
import itertools
import threading

import pytest

from wanxiang.personas.persona import Persona
from wanxiang.simulation.batch import BatchRunner
from wanxiang.simulation.decision import DecisionResult
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _personas(n):
    return [
        Persona(agent_id=i, name=f"p{i}",
                demographic={"年龄": 20 + i % 10},
                personality={}, media={})
        for i in range(n)
    ]


def _scenario_rate():
    return ScenarioConfig(material="m", question="q",
                          decision_kind=DecisionKind.RATE)


def test_batch_runs_one_decision_per_persona():
    personas = _personas(10)
    counter = itertools.count(start=1)

    async def call(messages):
        # 返回 {"score": 1}, {"score": 2}, ...
        return '{"score": ' + str(next(counter)) + '}'

    runner = BatchRunner(decision_concurrency=4)
    results = asyncio.run(runner.run_all(personas, _scenario_rate(), call))
    assert len(results) == 10
    assert all(isinstance(r, DecisionResult) for r in results)
    assert {r.agent_id for r in results} == set(range(10))


def test_batch_results_preserve_persona_order():
    personas = _personas(5)
    counter = itertools.count(start=100)

    async def call(messages):
        return '{"score": ' + str(next(counter)) + '}'

    runner = BatchRunner(decision_concurrency=2)
    results = asyncio.run(runner.run_all(personas, _scenario_rate(), call))
    # 顺序应与 personas 一致（agent_id 0..4）
    assert [r.agent_id for r in results] == [0, 1, 2, 3, 4]


def test_batch_concurrency_limit_is_enforced():
    """同时挂起的 model_call 数不应超过 decision_concurrency。"""
    personas = _personas(20)
    in_flight = 0
    peak = 0
    lock = threading.Lock()

    async def call(messages):
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        # 让任务真正"并发挂起"
        await asyncio.sleep(0.02)
        with lock:
            in_flight -= 1
        return '{"score": 5}'

    runner = BatchRunner(decision_concurrency=3)
    asyncio.run(runner.run_all(personas, _scenario_rate(), call))
    assert peak <= 3, f"peak in-flight {peak} exceeded concurrency limit 3"
    # 同时要证明确实并发了（否则 peak 会是 1）
    assert peak >= 2


def test_batch_does_not_raise_on_individual_failures():
    """部分 agent 模型出错；其它 agent 仍能成功，整体不抛。"""
    personas = _personas(6)

    async def call(messages):
        # 让 agent_id 是 3 的人模型抛错（用 system prompt 中的 'p3' 判别）
        system = messages[0]["content"]
        if "p3" in system:
            raise RuntimeError("boom for p3")
        return '{"score": 7}'

    runner = BatchRunner(decision_concurrency=4)
    results = asyncio.run(runner.run_all(personas, _scenario_rate(), call))
    assert len(results) == 6
    errs = [r for r in results if r.error]
    oks = [r for r in results if r.error is None]
    assert len(errs) == 1 and errs[0].agent_id == 3
    assert len(oks) == 5 and all(r.value == 7 for r in oks)


def test_batch_empty_personas_returns_empty():
    runner = BatchRunner(decision_concurrency=4)
    results = asyncio.run(runner.run_all([], _scenario_rate(),
                                          lambda m: None))  # noqa
    assert results == []
```

- [ ] **Step 2: 运行确认失败**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_batch_runner.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: 实现 batch.py**

`wanxiang/simulation/batch.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""BatchRunner: 并发跑 N 个 agent 的 decision_only 模拟。

用 asyncio.Semaphore 限制同时挂起的 model 调用数。永远返回 N 个
DecisionResult（DecisionRunner 已保证错误装 error 不抛），调用方按
result.error is None 过滤。
"""
from __future__ import annotations

import asyncio
from typing import Iterable

from wanxiang.personas.persona import Persona
from wanxiang.simulation.decision import (DecisionResult, DecisionRunner,
                                          ModelCall)
from wanxiang.simulation.scenario import ScenarioConfig


class BatchRunner:

    def __init__(self, decision_concurrency: int = 16):
        if decision_concurrency < 1:
            raise ValueError("decision_concurrency must be >= 1")
        self.decision_concurrency = decision_concurrency
        self._runner = DecisionRunner()

    async def run_all(
        self,
        personas: Iterable[Persona],
        scenario: ScenarioConfig,
        model_call: ModelCall,
    ) -> list[DecisionResult]:
        personas_list = list(personas)
        if not personas_list:
            return []
        sem = asyncio.Semaphore(self.decision_concurrency)

        async def one(p: Persona) -> DecisionResult:
            async with sem:
                return await self._runner.run(p, scenario, model_call)

        return await asyncio.gather(*(one(p) for p in personas_list))
```

- [ ] **Step 4: 运行确认通过**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_batch_runner.py -v` → 5 passed

- [ ] **Step 5: Commit**
```bash
cd "D:\NLp\oasis"
git add wanxiang/simulation/batch.py test/wanxiang/test_batch_runner.py
git commit -m "feat(wanxiang): add BatchRunner with semaphore-limited concurrency"
```
End with trailing blank line then: Co-Authored-By: Claude <noreply@anthropic.com>

---

## Task 2: aggregate() + AggregateReport

**Files:**
- Create: `wanxiang/simulation/aggregate.py`
- Modify: `wanxiang/simulation/__init__.py`（追加导出）
- Test: `test/wanxiang/test_aggregate.py`

- [ ] **Step 1: 写失败测试**

`test/wanxiang/test_aggregate.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import pytest

from wanxiang.simulation.aggregate import AggregateReport, aggregate
from wanxiang.simulation.decision import DecisionResult
from wanxiang.simulation.scenario import DecisionKind


def _rate(score, aid=0, err=None):
    return DecisionResult(agent_id=aid, kind=DecisionKind.RATE,
                          value=score, raw="", error=err)


def _choose(opt, aid=0, err=None):
    return DecisionResult(agent_id=aid, kind=DecisionKind.CHOOSE,
                          value=opt, raw="", error=err)


def test_aggregate_rate_returns_numeric_stats():
    results = [_rate(s, aid=i) for i, s in enumerate([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])]
    report = aggregate(results)
    assert isinstance(report, AggregateReport)
    assert report.kind is DecisionKind.RATE
    assert report.n_total == 10
    assert report.n_valid == 10
    assert report.error_count == 0
    s = report.stats
    assert s["mean"] == pytest.approx(5.5)
    assert s["median"] == pytest.approx(5.5)
    # 10 个均匀分布：p25 ≈ 3, p75 ≈ 8（按 statistics.quantiles 默认 exclusive 算法）
    assert 2 <= s["p25"] <= 4
    assert 7 <= s["p75"] <= 9


def test_aggregate_choose_returns_counts_and_share():
    results = [_choose("A", 0), _choose("A", 1), _choose("B", 2),
               _choose("A", 3), _choose("C", 4)]
    report = aggregate(results)
    assert report.kind is DecisionKind.CHOOSE
    assert report.n_total == 5
    assert report.n_valid == 5
    counts = report.stats["counts"]
    share = report.stats["share"]
    assert counts == {"A": 3, "B": 1, "C": 1}
    assert share["A"] == pytest.approx(0.6)
    assert report.stats["top"] == "A"


def test_aggregate_excludes_errors_from_stats_but_counts_them():
    results = [_rate(5, 0), _rate(7, 1), _rate(None, 2, err="json bad"),
               _rate(None, 3, err="missing field")]
    report = aggregate(results)
    assert report.n_total == 4
    assert report.n_valid == 2
    assert report.error_count == 2
    assert report.error_rate == pytest.approx(0.5)
    assert report.stats["mean"] == pytest.approx(6.0)


def test_aggregate_empty_list_returns_empty_report():
    report = aggregate([])
    assert report.n_total == 0
    assert report.n_valid == 0
    assert report.error_count == 0
    assert report.stats == {}
    assert report.kind is None


def test_aggregate_all_errors_returns_empty_stats():
    results = [_rate(None, i, err="bad") for i in range(3)]
    report = aggregate(results)
    assert report.n_total == 3
    assert report.n_valid == 0
    assert report.error_count == 3
    assert report.error_rate == pytest.approx(1.0)
    assert report.stats == {}
    assert report.kind is DecisionKind.RATE


def test_aggregate_rejects_mixed_kinds():
    """聚合不应跨 kind；混类型直接抛。"""
    results = [_rate(5, 0), _choose("A", 1)]
    with pytest.raises(ValueError, match="mixed.*kind"):
        aggregate(results)
```

- [ ] **Step 2: 运行确认失败**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_aggregate.py -v` → `ModuleNotFoundError`

- [ ] **Step 3: 实现 aggregate.py**

`wanxiang/simulation/aggregate.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""把 list[DecisionResult] 聚合成群体分布报告。

数值 kind (RATE/CLICK_PROBABILITY/SENTIMENT/WTP) → mean/median/p25/p75
枚举 kind (CHOOSE) → counts/share/top
始终报告 error_count / error_rate；错误样本不参与数值统计。
"""
from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable

from wanxiang.simulation.decision import DecisionResult
from wanxiang.simulation.scenario import DecisionKind

_NUMERIC_KINDS = {
    DecisionKind.RATE,
    DecisionKind.CLICK_PROBABILITY,
    DecisionKind.SENTIMENT,
    DecisionKind.WTP,
}


@dataclass(frozen=True)
class AggregateReport:
    kind: DecisionKind | None
    n_total: int
    n_valid: int
    error_count: int
    error_rate: float
    stats: dict[str, Any] = field(default_factory=dict)


def _quantiles(values: list[float]) -> tuple[float, float, float]:
    """返回 (p25, median, p75)。values 必须非空。"""
    if len(values) == 1:
        v = float(values[0])
        return v, v, v
    qs = statistics.quantiles(values, n=4, method="exclusive")
    # qs = [q25, q50, q75]
    return qs[0], qs[1], qs[2]


def aggregate(results: Iterable[DecisionResult]) -> AggregateReport:
    items = list(results)
    n_total = len(items)
    if n_total == 0:
        return AggregateReport(kind=None, n_total=0, n_valid=0,
                                error_count=0, error_rate=0.0, stats={})

    kinds = {r.kind for r in items}
    if len(kinds) > 1:
        raise ValueError(f"cannot aggregate mixed decision kinds: {kinds}")
    kind = next(iter(kinds))

    valid = [r for r in items if r.error is None]
    n_valid = len(valid)
    n_err = n_total - n_valid
    error_rate = n_err / n_total

    if n_valid == 0:
        return AggregateReport(kind=kind, n_total=n_total, n_valid=0,
                                error_count=n_err, error_rate=error_rate,
                                stats={})

    stats: dict[str, Any] = {}
    if kind in _NUMERIC_KINDS:
        nums = [float(r.value) for r in valid]
        p25, median, p75 = _quantiles(nums)
        stats = {
            "mean": statistics.fmean(nums),
            "median": median,
            "p25": p25,
            "p75": p75,
            "min": min(nums),
            "max": max(nums),
        }
    elif kind is DecisionKind.CHOOSE:
        counter = Counter(r.value for r in valid)
        total = sum(counter.values())
        share = {k: v / total for k, v in counter.items()}
        # top: 多数情况下唯一；并列时取字母序最小（确定性）
        top_count = max(counter.values())
        top = sorted([k for k, v in counter.items() if v == top_count])[0]
        stats = {"counts": dict(counter), "share": share, "top": top}
    else:
        # 防御：未来加新 kind 时给个明确错误
        raise ValueError(f"no aggregator implemented for kind {kind}")

    return AggregateReport(kind=kind, n_total=n_total, n_valid=n_valid,
                            error_count=n_err, error_rate=error_rate,
                            stats=stats)
```

- [ ] **Step 4: 运行确认通过**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_aggregate.py -v` → 6 passed

- [ ] **Step 5: 追加导出**

把 `wanxiang/simulation/__init__.py` 改为：
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""simulation: 场景配置 / 决策运行器 / 批量并发 / 聚合（spec §M3/M4 decision_only）。"""
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig
from wanxiang.simulation.decision import (DecisionResult, DecisionRunner,
                                          ModelCall)
from wanxiang.simulation.batch import BatchRunner
from wanxiang.simulation.aggregate import AggregateReport, aggregate

__all__ = [
    "DecisionKind", "ScenarioConfig",
    "DecisionResult", "DecisionRunner", "ModelCall",
    "BatchRunner", "AggregateReport", "aggregate",
]
```
验证：`/d/software/conda_data/envs/oasis/python.exe -c "from wanxiang.simulation import BatchRunner, aggregate, AggregateReport; print('OK')"` → `OK`

- [ ] **Step 6: 全量回归**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/ -q` → 87 + 5 + 6 = 98 passed

- [ ] **Step 7: Commit**
```bash
cd "D:\NLp\oasis"
git add wanxiang/simulation/aggregate.py wanxiang/simulation/__init__.py test/wanxiang/test_aggregate.py
git commit -m "feat(wanxiang): add aggregate() distribution reporter (numeric+choose)"
```
End with trailing blank line then: Co-Authored-By: Claude <noreply@anthropic.com>

---

## Task 3: 端到端冒烟测试（无 LLM，用 stub）

**Files:**
- Test: `test/wanxiang/test_decision_only_e2e.py`

- [ ] **Step 1: 写测试 + 直接跑（无新代码，组装已有件）**

`test/wanxiang/test_decision_only_e2e.py`:
```python
# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""decision_only 模式端到端冒烟：分布→造人→并发模拟→聚合。

不接真实 LLM；用一个会"参考画像"决定输出的 stub 来证明主链
能跑通且 BatchRunner+aggregate 给出合理分布。
"""
import asyncio

import pytest

from wanxiang.personas import PersonaBuilder
from wanxiang.simulation import (BatchRunner, DecisionKind, ScenarioConfig,
                                 aggregate)


SIMPLE_DIST = {
    "demographic": {
        "城市": [("北京", 0.5), ("上海", 0.5)],
    },
    "personality": {
        # 价格敏感度：高 (>=0.7) 的人会评低分，低的人会评高分
        "价格敏感度": [(0.2, 0.5), (0.8, 0.5)],
    },
    "media": {},
}


def test_decision_only_main_chain_end_to_end():
    # 1) 造人：1000 个，确定性 seed
    pb = PersonaBuilder()
    personas = pb.sample(SIMPLE_DIST, n=1000, seed=2026)

    # 2) 场景：定价 ¥10 评分
    scenario = ScenarioConfig(
        material="新品定价 ¥10", question="给出 0-10 购买意愿评分",
        decision_kind=DecisionKind.RATE)

    # 3) Stub 模型：从 system prompt 里读价格敏感度，越敏感分越低
    async def stub_call(messages):
        sys = messages[0]["content"]
        if "价格敏感度：0.8" in sys:
            return '{"score": 2}'
        return '{"score": 8}'

    # 4) 跑
    runner = BatchRunner(decision_concurrency=32)
    results = asyncio.run(runner.run_all(personas, scenario, stub_call))

    # 5) 聚合
    report = aggregate(results)
    assert report.n_total == 1000
    assert report.error_count == 0
    # 两类各占约一半：均值应接近 (2+8)/2 = 5
    assert 4.7 <= report.stats["mean"] <= 5.3
    # min/max 反映出"分布"
    assert report.stats["min"] == 2
    assert report.stats["max"] == 8
```

- [ ] **Step 2: 运行确认通过（一次写完即过）**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/test_decision_only_e2e.py -v` → 1 passed

- [ ] **Step 3: 全量回归 + commit**
`/d/software/conda_data/envs/oasis/python.exe -m pytest test/wanxiang/ -q` → 99 passed

```bash
cd "D:\NLp\oasis"
git add test/wanxiang/test_decision_only_e2e.py
git commit -m "test(wanxiang): decision_only main chain end-to-end smoke (no LLM)"
```
End with trailing blank line then: Co-Authored-By: Claude <noreply@anthropic.com>

---

## 完成标准（Definition of Done）
- [ ] `from wanxiang.simulation import BatchRunner, aggregate, AggregateReport` 可用
- [ ] BatchRunner 并发上限被 semaphore 严格遵守，单个失败不影响其它
- [ ] aggregate 区分数值/枚举 kind，混 kind 抛错，空/全错有合理回退
- [ ] e2e 冒烟用 stub 模型走通"分布→造人→并发→聚合"
- [ ] `test/wanxiang/` 99 passed（87 + 5 + 6 + 1）
- [ ] 仍 0 LLM 调用，纯 Python stdlib
