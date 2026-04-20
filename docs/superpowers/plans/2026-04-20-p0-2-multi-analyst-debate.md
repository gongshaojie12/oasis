# P0-2: 多视角辩论分析 (Multi-Analyst Debate) 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建多分析师辩论式报告生成系统，仿真完成后由 4 个 AI 分析师角色独立分析并交叉辩论，生成包含时间线叙事和交互式图表的深度报告。

**Architecture:** Engine 层新增 `analysts` 模块，包含 4 个分析师角色和辩论引擎。每个分析师读取仿真 trace 数据独立分析，辩论引擎协调 2-3 轮交叉辩论，主持人综合产出最终报告。Server 层新增 analysis_reports 表和 API。Frontend 升级报告页面支持交互式图表和辩论记录展示。

**Tech Stack:** Python (FastAPI, Pydantic, CAMEL ChatAgent), TypeScript (Nuxt 4, Naive UI, ECharts), Drizzle ORM, Zod

---

## 文件结构

### 新建文件

```
engine/
├── analysts/
│   ├── __init__.py           — 模块导出
│   ├── base.py               — 分析师基类 (BaseAnalyst)
│   ├── data_analyst.py       — 数据分析师（定量分析）
│   ├── sociologist.py        — 社会学家（群体行为）
│   ├── psychologist.py       — 心理学家（个体动机）
│   ├── devils_advocate.py    — 魔鬼代言人（反面论证）
│   ├── moderator.py          — 主持人（综合报告）
│   └── debate.py             — 辩论引擎（协调多轮辩论）

web/
├── server/
│   └── api/analysis/
│       ├── generate.post.ts  — 触发多视角分析（异步）
│       ├── [id].get.ts       — 获取完整报告
│       ├── [id]/
│       │   ├── status.get.ts — 查询分析进度
│       │   ├── timeline.get.ts — 获取时间线数据
│       │   ├── charts.get.ts  — 获取图表数据
│       │   └── debate.get.ts  — 获取辩论记录
│       └── compare.post.ts   — 多仿真对比
├── app/
│   ├── pages/analysis/
│   │   ├── [id].vue          — 多视角报告详情页
│   │   └── compare.vue       — 对比分析页
│   ├── components/
│   │   ├── TimelineNarrative.vue — 时间线叙事组件
│   │   ├── DebateLog.vue         — 辩论记录展示组件
│   │   └── AnalysisDashboard.vue — 交互式分析仪表盘
│   └── stores/
│       └── analysis.ts       — 分析报告 Pinia Store
```

### 修改文件

```
web/server/database/schema/sqlite.ts  — 添加 analysisReports, reportComparisons 表
web/server/database/schema/pg.ts      — 同上
engine/main.py                         — 添加分析相关 API 端点
web/app/layouts/default.vue            — 侧边栏添加「深度分析」导航
```

---

## Task 1: 分析师基类与数据模型

**Files:**
- Create: `engine/analysts/__init__.py`
- Create: `engine/analysts/base.py`
- Test: `engine/tests/test_analyst_base.py`

- [ ] **Step 1: 创建分析师基类**

```python
# engine/analysts/base.py
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AnalysisContext(BaseModel):
    simulation_id: str
    platform: str
    num_agents: int
    num_steps: int
    trace_data: list[dict[str, Any]] = Field(default_factory=list)
    post_data: list[dict[str, Any]] = Field(default_factory=list)
    user_data: list[dict[str, Any]] = Field(default_factory=list)
    follow_data: list[dict[str, Any]] = Field(default_factory=list)


class AnalystReport(BaseModel):
    analyst_role: str
    perspective: str
    findings: list[str] = Field(default_factory=list)
    key_insights: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    narrative: str = ""
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class DebateMessage(BaseModel):
    round_num: int
    speaker: str
    target: Optional[str] = None
    content: str
    message_type: str = "argument"  # argument, challenge, rebuttal, concession


class FinalReport(BaseModel):
    executive_summary: str = ""
    timeline_narrative: list[dict[str, Any]] = Field(default_factory=list)
    analyst_reports: dict[str, AnalystReport] = Field(default_factory=dict)
    debate_log: list[DebateMessage] = Field(default_factory=list)
    consensus: list[str] = Field(default_factory=list)
    disagreements: list[dict[str, Any]] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    chart_data: dict[str, Any] = Field(default_factory=dict)


class BaseAnalyst(ABC):
    def __init__(self, llm_call, role: str, perspective: str):
        self._llm_call = llm_call
        self.role = role
        self.perspective = perspective

    @abstractmethod
    async def analyze(self, context: AnalysisContext) -> AnalystReport:
        pass

    @abstractmethod
    async def respond_to_debate(
        self,
        own_report: AnalystReport,
        other_reports: dict[str, AnalystReport],
        debate_history: list[DebateMessage],
    ) -> DebateMessage:
        pass

    async def _call_llm(self, prompt: str) -> str:
        return await self._llm_call(prompt)

    def _build_data_summary(self, context: AnalysisContext) -> str:
        total_posts = len(context.post_data)
        total_actions = len(context.trace_data)
        action_types: dict[str, int] = {}
        for t in context.trace_data:
            a = t.get("action", "unknown")
            action_types[a] = action_types.get(a, 0) + 1

        return (
            f"仿真概况：平台={context.platform}, "
            f"Agent数={context.num_agents}, 步数={context.num_steps}, "
            f"总帖子={total_posts}, 总行为={total_actions}\n"
            f"行为分布: {action_types}"
        )
```

- [ ] **Step 2: 创建 __init__.py**

```python
# engine/analysts/__init__.py
from .base import (
    AnalysisContext,
    AnalystReport,
    BaseAnalyst,
    DebateMessage,
    FinalReport,
)

__all__ = [
    "AnalysisContext",
    "AnalystReport",
    "BaseAnalyst",
    "DebateMessage",
    "FinalReport",
]
```

- [ ] **Step 3: 编写测试**

```python
# engine/tests/test_analyst_base.py
from analysts.base import AnalysisContext, AnalystReport, DebateMessage, FinalReport


def test_analysis_context_defaults():
    ctx = AnalysisContext(
        simulation_id="sim_001",
        platform="twitter",
        num_agents=100,
        num_steps=10,
    )
    assert ctx.simulation_id == "sim_001"
    assert ctx.trace_data == []


def test_analyst_report_serialization():
    r = AnalystReport(
        analyst_role="data_analyst",
        perspective="quantitative",
        findings=["帖子数量呈上升趋势"],
        key_insights=["第5轮出现信息爆发"],
    )
    d = r.model_dump()
    assert d["analyst_role"] == "data_analyst"
    restored = AnalystReport.model_validate(d)
    assert restored.findings[0] == "帖子数量呈上升趋势"


def test_debate_message():
    msg = DebateMessage(
        round_num=1,
        speaker="sociologist",
        target="data_analyst",
        content="数据趋势并不能反映群体极化的深层原因",
        message_type="challenge",
    )
    assert msg.speaker == "sociologist"


def test_final_report_structure():
    r = FinalReport(
        executive_summary="仿真揭示了明显的群体极化趋势",
        consensus=["信息传播呈指数增长"],
        disagreements=[{"topic": "极化原因", "sides": {"sociologist": "结构性", "psychologist": "认知偏差"}}],
    )
    assert len(r.consensus) == 1
```

- [ ] **Step 4: 运行测试**

Run: `cd D:/NLP/oasis && python -m pytest engine/tests/test_analyst_base.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: 提交**

```bash
git add engine/analysts/__init__.py engine/analysts/base.py engine/tests/test_analyst_base.py
git commit -m "feat(analysts): add base analyst class and data models"
```

---

## Task 2: 四个分析师角色实现

**Files:**
- Create: `engine/analysts/data_analyst.py`
- Create: `engine/analysts/sociologist.py`
- Create: `engine/analysts/psychologist.py`
- Create: `engine/analysts/devils_advocate.py`

- [ ] **Step 1: 实现数据分析师**

```python
# engine/analysts/data_analyst.py
from __future__ import annotations

import json
from .base import BaseAnalyst, AnalysisContext, AnalystReport, DebateMessage


class DataAnalyst(BaseAnalyst):
    def __init__(self, llm_call):
        super().__init__(llm_call, role="data_analyst", perspective="定量分析")

    async def analyze(self, context: AnalysisContext) -> AnalystReport:
        summary = self._build_data_summary(context)

        posts_per_step: dict[int, int] = {}
        for p in context.post_data:
            step = p.get("created_at_step", 0)
            posts_per_step[step] = posts_per_step.get(step, 0) + 1

        action_counts: dict[str, int] = {}
        for t in context.trace_data:
            a = t.get("action", "unknown")
            action_counts[a] = action_counts.get(a, 0) + 1

        top_agents: dict[int, int] = {}
        for t in context.trace_data:
            aid = t.get("agent_id", -1)
            top_agents[aid] = top_agents.get(aid, 0) + 1
        top_5 = sorted(top_agents.items(), key=lambda x: -x[1])[:5]

        prompt = f"""你是一位数据分析师，请对以下社交媒体仿真数据进行定量分析。

{summary}

每步帖子数: {json.dumps(posts_per_step)}
行为统计: {json.dumps(action_counts)}
最活跃Top5 Agent: {json.dumps(top_5)}

请输出 JSON 格式的分析报告:
{{
  "findings": ["发现1", "发现2", ...],
  "key_insights": ["洞察1", "洞察2", ...],
  "narrative": "一段200字左右的定量分析叙述"
}}

只输出 JSON。"""

        raw = await self._call_llm(prompt)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[1:-1])
            parsed = json.loads(cleaned)
            return AnalystReport(
                analyst_role=self.role,
                perspective=self.perspective,
                findings=parsed.get("findings", []),
                key_insights=parsed.get("key_insights", []),
                narrative=parsed.get("narrative", ""),
                evidence=[
                    {"type": "posts_per_step", "data": posts_per_step},
                    {"type": "action_counts", "data": action_counts},
                    {"type": "top_agents", "data": top_5},
                ],
            )
        except (json.JSONDecodeError, Exception):
            return AnalystReport(
                analyst_role=self.role,
                perspective=self.perspective,
                findings=["数据分析结果解析失败"],
                narrative=raw[:500],
            )

    async def respond_to_debate(self, own_report, other_reports, debate_history) -> DebateMessage:
        others_summary = "\n".join(
            f"- {role}: {r.key_insights[:2]}" for role, r in other_reports.items()
        )
        recent = debate_history[-3:] if debate_history else []
        recent_text = "\n".join(f"[{m.speaker}→{m.target}]: {m.content}" for m in recent)

        prompt = f"""你是数据分析师，基于你的定量分析回应辩论。

你的核心发现: {own_report.key_insights}

其他分析师的观点:
{others_summary}

最近讨论:
{recent_text}

用一段话回应，可以补充数据证据、质疑他人结论或承认对方观点的合理性。只输出回应文本。"""

        content = await self._call_llm(prompt)
        return DebateMessage(
            round_num=len(debate_history) // 4 + 1,
            speaker=self.role,
            content=content.strip(),
            message_type="argument",
        )
```

- [ ] **Step 2: 实现社会学家**

```python
# engine/analysts/sociologist.py
from __future__ import annotations

import json
from .base import BaseAnalyst, AnalysisContext, AnalystReport, DebateMessage


class Sociologist(BaseAnalyst):
    def __init__(self, llm_call):
        super().__init__(llm_call, role="sociologist", perspective="群体行为分析")

    async def analyze(self, context: AnalysisContext) -> AnalystReport:
        summary = self._build_data_summary(context)

        follow_network: dict[int, list[int]] = {}
        for f in context.follow_data:
            fid = f.get("follower_id", 0)
            follow_network.setdefault(fid, []).append(f.get("followee_id", 0))

        prompt = f"""你是一位社会学家，请分析以下社交媒体仿真中的群体行为现象。

{summary}

关注网络规模: {len(follow_network)} 个活跃关注者
帖子样本: {json.dumps(context.post_data[:10], ensure_ascii=False)}

请从以下角度分析：
1. 群体极化现象（意见是否趋向两极化）
2. 信息茧房效应（是否形成封闭的信息圈）
3. 舆论领袖识别（谁在主导讨论方向）
4. 社区结构（是否形成明显的小群体）

输出 JSON:
{{
  "findings": ["发现1", ...],
  "key_insights": ["洞察1", ...],
  "narrative": "200字社会学分析叙述"
}}

只输出 JSON。"""

        raw = await self._call_llm(prompt)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[1:-1])
            parsed = json.loads(cleaned)
            return AnalystReport(
                analyst_role=self.role,
                perspective=self.perspective,
                findings=parsed.get("findings", []),
                key_insights=parsed.get("key_insights", []),
                narrative=parsed.get("narrative", ""),
            )
        except Exception:
            return AnalystReport(analyst_role=self.role, perspective=self.perspective, narrative=raw[:500])

    async def respond_to_debate(self, own_report, other_reports, debate_history) -> DebateMessage:
        others_summary = "\n".join(f"- {role}: {r.key_insights[:2]}" for role, r in other_reports.items())
        recent = debate_history[-3:] if debate_history else []
        recent_text = "\n".join(f"[{m.speaker}]: {m.content}" for m in recent)

        prompt = f"""你是社会学家，基于群体行为视角回应辩论。

你的核心发现: {own_report.key_insights}
其他观点: {others_summary}
最近讨论: {recent_text}

用社会学理论框架回应。只输出回应文本。"""

        content = await self._call_llm(prompt)
        return DebateMessage(round_num=len(debate_history) // 4 + 1, speaker=self.role, content=content.strip())
```

- [ ] **Step 3: 实现心理学家**

```python
# engine/analysts/psychologist.py
from __future__ import annotations

import json
from .base import BaseAnalyst, AnalysisContext, AnalystReport, DebateMessage


class Psychologist(BaseAnalyst):
    def __init__(self, llm_call):
        super().__init__(llm_call, role="psychologist", perspective="个体心理分析")

    async def analyze(self, context: AnalysisContext) -> AnalystReport:
        summary = self._build_data_summary(context)

        agent_behaviors: dict[int, list[str]] = {}
        for t in context.trace_data:
            aid = t.get("agent_id", -1)
            agent_behaviors.setdefault(aid, []).append(t.get("action", "unknown"))

        behavioral_patterns = {}
        for aid, actions in list(agent_behaviors.items())[:10]:
            behavioral_patterns[aid] = {
                "total_actions": len(actions),
                "action_types": list(set(actions)),
                "most_common": max(set(actions), key=actions.count) if actions else "none",
            }

        prompt = f"""你是一位心理学家，请分析仿真中 Agent 的个体行为动机和心理模式。

{summary}

典型Agent行为模式:
{json.dumps(behavioral_patterns, ensure_ascii=False)}

帖子内容样本:
{json.dumps([p.get("content", "")[:100] for p in context.post_data[:5]], ensure_ascii=False)}

请从以下角度分析：
1. 认知偏差表现（确认偏误、从众效应等）
2. 情感变化轨迹
3. 动机分析（为什么Agent做出特定行为）
4. 典型Agent行为剖析

输出 JSON:
{{
  "findings": ["发现1", ...],
  "key_insights": ["洞察1", ...],
  "narrative": "200字心理学分析叙述"
}}

只输出 JSON。"""

        raw = await self._call_llm(prompt)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[1:-1])
            parsed = json.loads(cleaned)
            return AnalystReport(
                analyst_role=self.role, perspective=self.perspective,
                findings=parsed.get("findings", []),
                key_insights=parsed.get("key_insights", []),
                narrative=parsed.get("narrative", ""),
            )
        except Exception:
            return AnalystReport(analyst_role=self.role, perspective=self.perspective, narrative=raw[:500])

    async def respond_to_debate(self, own_report, other_reports, debate_history) -> DebateMessage:
        others_summary = "\n".join(f"- {role}: {r.key_insights[:2]}" for role, r in other_reports.items())
        recent_text = "\n".join(f"[{m.speaker}]: {m.content}" for m in (debate_history[-3:] or []))

        prompt = f"""你是心理学家，基于个体心理和认知科学视角回应辩论。
你的核心发现: {own_report.key_insights}
其他观点: {others_summary}
最近讨论: {recent_text}
用心理学理论回应。只输出回应文本。"""

        content = await self._call_llm(prompt)
        return DebateMessage(round_num=len(debate_history) // 4 + 1, speaker=self.role, content=content.strip())
```

- [ ] **Step 4: 实现魔鬼代言人**

```python
# engine/analysts/devils_advocate.py
from __future__ import annotations

import json
from .base import BaseAnalyst, AnalysisContext, AnalystReport, DebateMessage


class DevilsAdvocate(BaseAnalyst):
    def __init__(self, llm_call):
        super().__init__(llm_call, role="devils_advocate", perspective="反面论证与批判")

    async def analyze(self, context: AnalysisContext) -> AnalystReport:
        return AnalystReport(
            analyst_role=self.role,
            perspective=self.perspective,
            findings=["等待其他分析师的初步结论后进行反面论证"],
            narrative="魔鬼代言人将在辩论阶段提出挑战性观点。",
        )

    async def challenge(self, other_reports: dict[str, AnalystReport], context: AnalysisContext) -> AnalystReport:
        reports_text = "\n\n".join(
            f"【{role}】\n发现: {r.findings}\n洞察: {r.key_insights}"
            for role, r in other_reports.items()
        )

        prompt = f"""你是一位"魔鬼代言人"，你的职责是挑战其他分析师的结论，提出替代解释和被忽略的风险。

以下是其他三位分析师的分析结果：
{reports_text}

仿真基本信息: 平台={context.platform}, Agent数={context.num_agents}, 步数={context.num_steps}

请从以下角度提出挑战：
1. 指出每位分析师结论中可能的偏差或过度推断
2. 提出至少2个替代解释
3. 指出被忽视的因素或风险
4. 质疑数据的局限性

输出 JSON:
{{
  "findings": ["挑战/反驳1", ...],
  "key_insights": ["替代解释1", ...],
  "narrative": "200字反面论证叙述"
}}

只输出 JSON。"""

        raw = await self._call_llm(prompt)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[1:-1])
            parsed = json.loads(cleaned)
            return AnalystReport(
                analyst_role=self.role, perspective=self.perspective,
                findings=parsed.get("findings", []),
                key_insights=parsed.get("key_insights", []),
                narrative=parsed.get("narrative", ""),
            )
        except Exception:
            return AnalystReport(analyst_role=self.role, perspective=self.perspective, narrative=raw[:500])

    async def respond_to_debate(self, own_report, other_reports, debate_history) -> DebateMessage:
        recent_text = "\n".join(f"[{m.speaker}]: {m.content}" for m in (debate_history[-4:] or []))

        prompt = f"""你是魔鬼代言人，你的职责是继续挑战和质疑。
你之前的挑战: {own_report.findings[:3]}
最近讨论: {recent_text}
提出新的挑战或质疑。只输出回应文本。"""

        content = await self._call_llm(prompt)
        return DebateMessage(
            round_num=len(debate_history) // 4 + 1, speaker=self.role,
            content=content.strip(), message_type="challenge",
        )
```

- [ ] **Step 5: 提交**

```bash
git add engine/analysts/data_analyst.py engine/analysts/sociologist.py engine/analysts/psychologist.py engine/analysts/devils_advocate.py
git commit -m "feat(analysts): implement 4 analyst roles (data/sociologist/psychologist/devil)"
```

---

## Task 3: 主持人与辩论引擎

**Files:**
- Create: `engine/analysts/moderator.py`
- Create: `engine/analysts/debate.py`
- Test: `engine/tests/test_debate_engine.py`

- [ ] **Step 1: 实现主持人**

```python
# engine/analysts/moderator.py
from __future__ import annotations

import json
from .base import AnalystReport, DebateMessage, FinalReport, AnalysisContext


class Moderator:
    def __init__(self, llm_call):
        self._llm_call = llm_call

    async def synthesize(
        self,
        context: AnalysisContext,
        analyst_reports: dict[str, AnalystReport],
        debate_log: list[DebateMessage],
    ) -> FinalReport:
        reports_text = "\n\n".join(
            f"【{role} - {r.perspective}】\n发现: {r.findings}\n洞察: {r.key_insights}\n叙述: {r.narrative}"
            for role, r in analyst_reports.items()
        )

        debate_text = "\n".join(
            f"[第{m.round_num}轮 {m.speaker}→{m.target or '全体'}]: {m.content}"
            for m in debate_log
        )

        prompt = f"""你是仿真分析报告的主持人。请综合以下分析师的报告和辩论记录，生成最终的综合分析报告。

仿真信息: 平台={context.platform}, Agent数={context.num_agents}, 步数={context.num_steps}

各分析师报告:
{reports_text}

辩论记录:
{debate_text}

请输出 JSON:
{{
  "executive_summary": "200字执行摘要，概述核心发现",
  "consensus": ["所有分析师达成共识的结论1", "结论2", ...],
  "disagreements": [
    {{"topic": "分歧话题", "sides": {{"角色A": "观点A", "角色B": "观点B"}}, "assessment": "主持人评估"}}
  ],
  "open_questions": ["尚待解答的问题1", ...],
  "timeline_narrative": [
    {{"step": 1, "title": "阶段标题", "description": "描述", "significance": "high/medium/low"}},
    ...
  ]
}}

只输出 JSON。"""

        raw = await self._llm_call(prompt)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[1:-1])
            parsed = json.loads(cleaned)

            return FinalReport(
                executive_summary=parsed.get("executive_summary", ""),
                timeline_narrative=parsed.get("timeline_narrative", []),
                analyst_reports=analyst_reports,
                debate_log=debate_log,
                consensus=parsed.get("consensus", []),
                disagreements=parsed.get("disagreements", []),
                open_questions=parsed.get("open_questions", []),
            )
        except Exception:
            return FinalReport(
                executive_summary=raw[:500],
                analyst_reports=analyst_reports,
                debate_log=debate_log,
            )
```

- [ ] **Step 2: 实现辩论引擎**

```python
# engine/analysts/debate.py
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Awaitable, Optional

from .base import AnalysisContext, AnalystReport, DebateMessage, FinalReport, BaseAnalyst
from .data_analyst import DataAnalyst
from .sociologist import Sociologist
from .psychologist import Psychologist
from .devils_advocate import DevilsAdvocate
from .moderator import Moderator

logger = logging.getLogger(__name__)


class DebateEngine:
    def __init__(
        self,
        llm_call: Callable[[str], Awaitable[str]],
        debate_rounds: int = 2,
        on_progress: Optional[Callable[[str, float], Awaitable[None]]] = None,
    ):
        self._llm_call = llm_call
        self._debate_rounds = debate_rounds
        self._on_progress = on_progress

        self._analysts: dict[str, BaseAnalyst] = {
            "data_analyst": DataAnalyst(llm_call),
            "sociologist": Sociologist(llm_call),
            "psychologist": Psychologist(llm_call),
        }
        self._devils_advocate = DevilsAdvocate(llm_call)
        self._moderator = Moderator(llm_call)

    async def _report_progress(self, phase: str, progress: float) -> None:
        if self._on_progress:
            await self._on_progress(phase, progress)

    async def run(self, context: AnalysisContext) -> FinalReport:
        await self._report_progress("independent_analysis", 0.0)

        # Phase 1: Independent analysis (parallel)
        analyst_reports: dict[str, AnalystReport] = {}
        tasks = {
            role: asyncio.create_task(analyst.analyze(context))
            for role, analyst in self._analysts.items()
        }
        for role, task in tasks.items():
            analyst_reports[role] = await task
            logger.info("Analyst %s completed analysis", role)

        await self._report_progress("independent_analysis", 0.3)

        # Devil's advocate challenges based on others' reports
        devil_report = await self._devils_advocate.challenge(analyst_reports, context)
        analyst_reports["devils_advocate"] = devil_report
        logger.info("Devil's advocate completed challenges")

        await self._report_progress("debate", 0.4)

        # Phase 2: Debate rounds
        debate_log: list[DebateMessage] = []
        all_analysts = {**self._analysts, "devils_advocate": self._devils_advocate}

        for round_num in range(1, self._debate_rounds + 1):
            logger.info("Debate round %d/%d", round_num, self._debate_rounds)
            for role, analyst in all_analysts.items():
                others = {r: rpt for r, rpt in analyst_reports.items() if r != role}
                msg = await analyst.respond_to_debate(
                    own_report=analyst_reports[role],
                    other_reports=others,
                    debate_history=debate_log,
                )
                msg.round_num = round_num
                debate_log.append(msg)

            progress = 0.4 + (round_num / self._debate_rounds) * 0.3
            await self._report_progress("debate", progress)

        await self._report_progress("synthesis", 0.7)

        # Phase 3: Synthesis
        final_report = await self._moderator.synthesize(context, analyst_reports, debate_log)

        # Build chart data
        final_report.chart_data = self._build_chart_data(context)

        await self._report_progress("complete", 1.0)
        logger.info("Analysis complete")

        return final_report

    def _build_chart_data(self, context: AnalysisContext) -> dict[str, Any]:
        posts_per_step: dict[int, int] = {}
        for p in context.post_data:
            step = p.get("created_at_step", 0)
            posts_per_step[step] = posts_per_step.get(step, 0) + 1

        action_counts: dict[str, int] = {}
        for t in context.trace_data:
            a = t.get("action", "unknown")
            action_counts[a] = action_counts.get(a, 0) + 1

        agent_activity: dict[int, int] = {}
        for t in context.trace_data:
            aid = t.get("agent_id", -1)
            agent_activity[aid] = agent_activity.get(aid, 0) + 1

        top_agents = sorted(agent_activity.items(), key=lambda x: -x[1])[:20]

        return {
            "posts_timeline": [{"step": k, "count": v} for k, v in sorted(posts_per_step.items())],
            "action_distribution": [{"action": k, "count": v} for k, v in action_counts.items()],
            "top_agents": [{"agent_id": k, "actions": v} for k, v in top_agents],
        }
```

- [ ] **Step 3: 编写辩论引擎测试**

```python
# engine/tests/test_debate_engine.py
import pytest
from unittest.mock import AsyncMock
import json
from analysts.debate import DebateEngine
from analysts.base import AnalysisContext


MOCK_ANALYSIS_RESPONSE = json.dumps({
    "findings": ["发现测试数据"],
    "key_insights": ["测试洞察"],
    "narrative": "测试叙述",
})

MOCK_CHALLENGE_RESPONSE = json.dumps({
    "findings": ["挑战观点1"],
    "key_insights": ["替代解释1"],
    "narrative": "测试反面论证",
})

MOCK_SYNTHESIS_RESPONSE = json.dumps({
    "executive_summary": "测试执行摘要",
    "consensus": ["共识1"],
    "disagreements": [],
    "open_questions": ["问题1"],
    "timeline_narrative": [{"step": 1, "title": "开始", "description": "仿真启动", "significance": "high"}],
})


@pytest.mark.asyncio
async def test_debate_engine_full_run():
    call_count = 0

    async def mock_llm(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        if "综合" in prompt or "主持人" in prompt:
            return MOCK_SYNTHESIS_RESPONSE
        if "魔鬼代言人" in prompt or "挑战" in prompt:
            return MOCK_CHALLENGE_RESPONSE
        if "回应" in prompt or "辩论" in prompt:
            return "这是辩论回应内容"
        return MOCK_ANALYSIS_RESPONSE

    context = AnalysisContext(
        simulation_id="test_sim",
        platform="twitter",
        num_agents=10,
        num_steps=5,
        trace_data=[{"agent_id": i, "action": "create_post"} for i in range(20)],
        post_data=[{"content": f"test post {i}", "created_at_step": i % 5} for i in range(15)],
    )

    engine = DebateEngine(llm_call=mock_llm, debate_rounds=1)
    report = engine.run(context)
    result = await report

    assert result.executive_summary != ""
    assert "data_analyst" in result.analyst_reports
    assert "sociologist" in result.analyst_reports
    assert "psychologist" in result.analyst_reports
    assert "devils_advocate" in result.analyst_reports
    assert len(result.debate_log) > 0
    assert "posts_timeline" in result.chart_data


@pytest.mark.asyncio
async def test_debate_engine_progress_reporting():
    phases: list[tuple[str, float]] = []

    async def mock_llm(prompt: str) -> str:
        return MOCK_ANALYSIS_RESPONSE

    async def on_progress(phase: str, progress: float) -> None:
        phases.append((phase, progress))

    context = AnalysisContext(simulation_id="test", platform="twitter", num_agents=5, num_steps=3)
    engine = DebateEngine(llm_call=mock_llm, debate_rounds=1, on_progress=on_progress)
    await engine.run(context)

    phase_names = [p[0] for p in phases]
    assert "independent_analysis" in phase_names
    assert "debate" in phase_names
    assert "complete" in phase_names
```

- [ ] **Step 4: 运行测试**

Run: `cd D:/NLP/oasis && python -m pytest engine/tests/test_debate_engine.py -v`
Expected: 2 tests PASS

- [ ] **Step 5: 更新导出并提交**

在 `engine/analysts/__init__.py` 添加:
```python
from .data_analyst import DataAnalyst
from .sociologist import Sociologist
from .psychologist import Psychologist
from .devils_advocate import DevilsAdvocate
from .moderator import Moderator
from .debate import DebateEngine
```

```bash
git add engine/analysts/ engine/tests/test_debate_engine.py
git commit -m "feat(analysts): implement debate engine with 4 analysts + moderator"
```

---

## Task 4: Engine 分析 API 端点

**Files:**
- Modify: `engine/main.py`

- [ ] **Step 1: 在 main.py 添加分析端点**

在 `engine/main.py` 中添加：

```python
# === 新增 import ===
from analysts.debate import DebateEngine
from analysts.base import AnalysisContext, FinalReport

# === 新增请求模型 ===
class AnalysisRequest(BaseModel):
    simulation_id: str
    platform: str = "twitter"
    num_agents: int = 10
    num_steps: int = 5
    db_path: str
    debate_rounds: int = Field(default=2, ge=1, le=5)

# === 新增端点 ===
@app.post(
    "/engine/analysis/run",
    dependencies=[Depends(verify_internal_key)],
)
async def run_analysis(body: AnalysisRequest, request: Request):
    settings = request.app.state.settings
    qm: TaskQueueManager = request.app.state.queue_manager

    async def analysis_executor(task_info: TaskInfo, params: dict[str, Any]):
        import sqlite3

        db_path = params["db_path"]
        conn = sqlite3.connect(db_path)
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
            simulation_id=params["simulation_id"],
            platform=params["platform"],
            num_agents=params["num_agents"],
            num_steps=params["num_steps"],
            trace_data=trace_data,
            post_data=post_data,
            user_data=user_data,
            follow_data=follow_data,
        )

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

        async def on_progress(phase: str, progress: float) -> None:
            reporter = request.app.state.reporter if hasattr(request.app.state, 'reporter') else None
            if reporter:
                await reporter.report_progress(
                    task_info,
                    current_step=int(progress * 100),
                    total_steps=100,
                    data={"phase": phase},
                )

        engine = DebateEngine(
            llm_call=llm_call,
            debate_rounds=params.get("debate_rounds", 2),
            on_progress=on_progress,
        )
        report = await engine.run(context)
        return report.model_dump()

    params = body.model_dump()
    task_info = await qm.submit(params)

    # Temporarily swap executor for this analysis task
    original_executor = qm._executor
    qm.set_executor(analysis_executor)

    return {"task_id": task_info.task_id, "status": task_info.status.value}
```

- [ ] **Step 2: 提交**

```bash
git add engine/main.py
git commit -m "feat(engine): add analysis run API endpoint with debate engine"
```

---

## Task 5: 数据库表定义

**Files:**
- Modify: `web/server/database/schema/sqlite.ts`
- Modify: `web/server/database/schema/pg.ts`

- [ ] **Step 1: 在 sqlite.ts 添加分析报告表**

```typescript
export const analysisReports = sqliteTable('analysis_reports', {
  id: text('id').primaryKey(),
  simulationId: text('simulation_id').notNull().references(() => simulations.id),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  status: text('status').default('pending').notNull(),
  analystReports: text('analyst_reports'),
  debateLog: text('debate_log'),
  finalReport: text('final_report'),
  chartData: text('chart_data'),
  timelineData: text('timeline_data'),
  engineTaskId: text('engine_task_id'),
  createdAt: text('created_at').notNull(),
  completedAt: text('completed_at'),
})

export const reportComparisons = sqliteTable('report_comparisons', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  reportIds: text('report_ids').notNull(),
  comparisonData: text('comparison_data'),
  createdAt: text('created_at').notNull(),
})
```

- [ ] **Step 2: 在 pg.ts 添加同样的表（用 pgTable）**

同 sqlite 结构，使用 `pgTable` 替换 `sqliteTable`。

- [ ] **Step 3: 生成迁移并提交**

```bash
cd D:/NLP/oasis/web && npx drizzle-kit generate
git add web/server/database/schema/ web/drizzle/
git commit -m "feat(db): add analysis_reports and report_comparisons tables"
```

---

## Task 6: Server 端分析 API

**Files:**
- Create: `web/server/api/analysis/generate.post.ts`
- Create: `web/server/api/analysis/[id].get.ts`
- Create: `web/server/api/analysis/[id]/status.get.ts`
- Create: `web/server/api/analysis/[id]/timeline.get.ts`
- Create: `web/server/api/analysis/[id]/charts.get.ts`
- Create: `web/server/api/analysis/[id]/debate.get.ts`
- Create: `web/server/api/analysis/compare.post.ts`

- [ ] **Step 1: 创建触发分析 API**

```typescript
// web/server/api/analysis/generate.post.ts
import { z } from 'zod'
import { eq } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { simulations, analysisReports, operationLogs } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  simulationId: z.string().min(1),
  debateRounds: z.number().int().min(1).max(5).default(2),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const { userId, enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const sim = await db.select().from(simulations).where(eq(simulations.id, parsed.data.simulationId)).limit(1)
  if (sim.length === 0) return error(ErrorCodes.NOT_FOUND, '仿真不存在')
  if (sim[0].status !== 'completed') return error(ErrorCodes.VALIDATION_ERROR, '仿真尚未完成')

  const analysisId = generateId()
  const timestamp = now()

  const simConfig = JSON.parse(sim[0].config || '{}')
  const dbPath = simConfig.engineTaskId ? `./data/${simConfig.engineTaskId}.db` : ''

  await db.insert(analysisReports).values({
    id: analysisId, simulationId: parsed.data.simulationId, enterpriseId,
    status: 'analyzing', createdAt: timestamp,
  })

  try {
    const result: any = await $fetch(`${config.engineUrl}/engine/analysis/run`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: {
        simulation_id: parsed.data.simulationId,
        platform: sim[0].platform,
        num_agents: sim[0].agentCount || 10,
        num_steps: sim[0].timeSteps || 5,
        db_path: dbPath,
        debate_rounds: parsed.data.debateRounds,
      },
    })

    await db.update(analysisReports).set({
      engineTaskId: result.task_id,
    }).where(eq(analysisReports.id, analysisId))

    await db.insert(operationLogs).values({
      id: generateId(), enterpriseId, userId,
      action: 'generate_analysis', resourceType: 'analysis', resourceId: analysisId,
      createdAt: timestamp,
    })

    return success({ id: analysisId, taskId: result.task_id, status: 'analyzing' })
  } catch (e: any) {
    await db.update(analysisReports).set({ status: 'failed' }).where(eq(analysisReports.id, analysisId))
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '分析启动失败: ' + (e.message || ''))
  }
})
```

- [ ] **Step 2: 创建获取完整报告 API**

```typescript
// web/server/api/analysis/[id].get.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { analysisReports } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select().from(analysisReports)
    .where(and(eq(analysisReports.id, id), eq(analysisReports.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '分析报告不存在')

  const item = items[0]
  return success({
    ...item,
    analystReports: item.analystReports ? JSON.parse(item.analystReports) : null,
    debateLog: item.debateLog ? JSON.parse(item.debateLog) : null,
    finalReport: item.finalReport ? JSON.parse(item.finalReport) : null,
    chartData: item.chartData ? JSON.parse(item.chartData) : null,
    timelineData: item.timelineData ? JSON.parse(item.timelineData) : null,
  })
})
```

- [ ] **Step 3: 创建状态、时间线、图表、辩论子 API**

```typescript
// web/server/api/analysis/[id]/status.get.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { analysisReports } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select({
    id: analysisReports.id,
    status: analysisReports.status,
    engineTaskId: analysisReports.engineTaskId,
  }).from(analysisReports)
    .where(and(eq(analysisReports.id, id), eq(analysisReports.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '不存在')

  const config = useRuntimeConfig()
  let engineStatus = null
  if (items[0].engineTaskId) {
    try {
      engineStatus = await $fetch(`${config.engineUrl}/engine/tasks/${items[0].engineTaskId}`, {
        headers: { 'X-Internal-Key': config.internalApiKey },
      })
    } catch {}
  }

  return success({ ...items[0], engineStatus })
})
```

```typescript
// web/server/api/analysis/[id]/timeline.get.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { analysisReports } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select({ timelineData: analysisReports.timelineData })
    .from(analysisReports)
    .where(and(eq(analysisReports.id, id), eq(analysisReports.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '不存在')
  return success(items[0].timelineData ? JSON.parse(items[0].timelineData) : [])
})
```

```typescript
// web/server/api/analysis/[id]/charts.get.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { analysisReports } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select({ chartData: analysisReports.chartData })
    .from(analysisReports)
    .where(and(eq(analysisReports.id, id), eq(analysisReports.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '不存在')
  return success(items[0].chartData ? JSON.parse(items[0].chartData) : {})
})
```

```typescript
// web/server/api/analysis/[id]/debate.get.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { analysisReports } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select({ debateLog: analysisReports.debateLog })
    .from(analysisReports)
    .where(and(eq(analysisReports.id, id), eq(analysisReports.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '不存在')
  return success(items[0].debateLog ? JSON.parse(items[0].debateLog) : [])
})
```

- [ ] **Step 4: 创建对比分析 API**

```typescript
// web/server/api/analysis/compare.post.ts
import { z } from 'zod'
import { eq, inArray } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { analysisReports, reportComparisons } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  reportIds: z.array(z.string()).min(2).max(5),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '请选择2-5份报告')

  const { enterpriseId } = event.context.user!
  const db = useDB()

  const reports = await db.select().from(analysisReports)
    .where(inArray(analysisReports.id, parsed.data.reportIds))

  if (reports.length < 2) return error(ErrorCodes.NOT_FOUND, '部分报告不存在')

  const comparisonData: any = { reports: [] }
  for (const r of reports) {
    const chartData = r.chartData ? JSON.parse(r.chartData) : {}
    const finalReport = r.finalReport ? JSON.parse(r.finalReport) : {}
    comparisonData.reports.push({
      id: r.id,
      simulationId: r.simulationId,
      executive_summary: finalReport.executive_summary || '',
      chart_data: chartData,
    })
  }

  const compId = generateId()
  await db.insert(reportComparisons).values({
    id: compId, enterpriseId,
    reportIds: JSON.stringify(parsed.data.reportIds),
    comparisonData: JSON.stringify(comparisonData),
    createdAt: now(),
  })

  return success({ id: compId, comparison: comparisonData })
})
```

- [ ] **Step 5: 提交**

```bash
git add web/server/api/analysis/
git commit -m "feat(api): add analysis generation, detail, comparison endpoints"
```

---

## Task 7: Frontend 分析 Store

**Files:**
- Create: `web/app/stores/analysis.ts`

- [ ] **Step 1: 创建 Store**

```typescript
// web/app/stores/analysis.ts
import { defineStore } from 'pinia'

export interface AnalysisReport {
  id: string
  simulationId: string
  status: string
  analystReports: any
  debateLog: any[]
  finalReport: any
  chartData: any
  timelineData: any[]
  createdAt: string
  completedAt: string | null
}

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    currentReport: null as AnalysisReport | null,
    loading: false,
  }),

  actions: {
    async generate(simulationId: string, debateRounds: number = 2) {
      const { $api } = useApi()
      return await $api<any>('/api/analysis/generate', {
        method: 'POST',
        body: { simulationId, debateRounds },
      })
    },

    async fetchOne(id: string) {
      this.loading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/analysis/${id}`)
        if (res.code === 0) this.currentReport = res.data
        return res
      } finally {
        this.loading = false
      }
    },

    async fetchStatus(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/analysis/${id}/status`)
    },

    async fetchTimeline(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/analysis/${id}/timeline`)
    },

    async fetchCharts(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/analysis/${id}/charts`)
    },

    async fetchDebate(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/analysis/${id}/debate`)
    },

    async compare(reportIds: string[]) {
      const { $api } = useApi()
      return await $api<any>('/api/analysis/compare', {
        method: 'POST',
        body: { reportIds },
      })
    },
  },
})
```

- [ ] **Step 2: 提交**

```bash
git add web/app/stores/analysis.ts
git commit -m "feat(store): add analysis Pinia store"
```

---

## Task 8: 时间线叙事组件

**Files:**
- Create: `web/app/components/TimelineNarrative.vue`

- [ ] **Step 1: 创建时间线组件**

```vue
<!-- web/app/components/TimelineNarrative.vue -->
<template>
  <n-card title="时间线叙事">
    <n-timeline>
      <n-timeline-item
        v-for="(item, index) in timeline"
        :key="index"
        :type="significanceType(item.significance)"
        :title="item.title"
        :content="item.description"
        :time="`第 ${item.step} 轮`"
      />
    </n-timeline>
    <n-empty v-if="!timeline.length" description="暂无时间线数据" />
  </n-card>
</template>

<script setup lang="ts">
interface TimelineItem {
  step: number
  title: string
  description: string
  significance: 'high' | 'medium' | 'low'
}

defineProps<{ timeline: TimelineItem[] }>()

function significanceType(sig: string): 'error' | 'warning' | 'info' {
  if (sig === 'high') return 'error'
  if (sig === 'medium') return 'warning'
  return 'info'
}
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/components/TimelineNarrative.vue
git commit -m "feat(ui): add TimelineNarrative component"
```

---

## Task 9: 辩论记录组件

**Files:**
- Create: `web/app/components/DebateLog.vue`

- [ ] **Step 1: 创建辩论记录组件**

```vue
<!-- web/app/components/DebateLog.vue -->
<template>
  <n-card title="分析师辩论记录">
    <n-collapse>
      <n-collapse-item
        v-for="round in rounds"
        :key="round"
        :title="`第 ${round} 轮辩论`"
      >
        <div v-for="(msg, i) in getMessagesForRound(round)" :key="i" style="margin-bottom: 12px">
          <n-card size="small" :bordered="true">
            <template #header>
              <n-space align="center">
                <n-tag :type="roleColor(msg.speaker)" size="small">{{ roleLabel(msg.speaker) }}</n-tag>
                <n-tag v-if="msg.message_type === 'challenge'" type="warning" size="tiny">挑战</n-tag>
                <n-tag v-if="msg.target" size="tiny">→ {{ roleLabel(msg.target) }}</n-tag>
              </n-space>
            </template>
            <n-text>{{ msg.content }}</n-text>
          </n-card>
        </div>
      </n-collapse-item>
    </n-collapse>
    <n-empty v-if="!messages.length" description="暂无辩论记录" />
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface DebateMsg {
  round_num: number
  speaker: string
  target?: string
  content: string
  message_type: string
}

const props = defineProps<{ messages: DebateMsg[] }>()

const roleLabels: Record<string, string> = {
  data_analyst: '数据分析师',
  sociologist: '社会学家',
  psychologist: '心理学家',
  devils_advocate: '魔鬼代言人',
}

const roleColors: Record<string, string> = {
  data_analyst: 'info',
  sociologist: 'success',
  psychologist: 'warning',
  devils_advocate: 'error',
}

function roleLabel(role: string) { return roleLabels[role] || role }
function roleColor(role: string): any { return roleColors[role] || 'default' }

const rounds = computed(() => [...new Set(props.messages.map(m => m.round_num))].sort())

function getMessagesForRound(round: number) {
  return props.messages.filter(m => m.round_num === round)
}
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/components/DebateLog.vue
git commit -m "feat(ui): add DebateLog component"
```

---

## Task 10: 分析仪表盘组件

**Files:**
- Create: `web/app/components/AnalysisDashboard.vue`

- [ ] **Step 1: 创建交互式仪表盘**

```vue
<!-- web/app/components/AnalysisDashboard.vue -->
<template>
  <n-card title="数据仪表盘">
    <n-grid :cols="2" :x-gap="16" :y-gap="16">
      <n-gi>
        <n-card title="帖子数量趋势" size="small">
          <div ref="timelineChartRef" style="height: 250px" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="行为类型分布" size="small">
          <div ref="actionChartRef" style="height: 250px" />
        </n-card>
      </n-gi>
      <n-gi :span="2">
        <n-card title="Agent 活跃度排行" size="small">
          <div ref="agentChartRef" style="height: 250px" />
        </n-card>
      </n-gi>
    </n-grid>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, TitleComponent, LegendComponent } from 'echarts/components'

echarts.use([CanvasRenderer, LineChart, PieChart, BarChart, GridComponent, TooltipComponent, TitleComponent, LegendComponent])

interface ChartData {
  posts_timeline: { step: number; count: number }[]
  action_distribution: { action: string; count: number }[]
  top_agents: { agent_id: number; actions: number }[]
}

const props = defineProps<{ data: ChartData | null }>()

const timelineChartRef = ref<HTMLElement>()
const actionChartRef = ref<HTMLElement>()
const agentChartRef = ref<HTMLElement>()

function render() {
  if (!props.data) return

  if (timelineChartRef.value) {
    const chart = echarts.init(timelineChartRef.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: props.data.posts_timeline.map(d => `第${d.step}轮`) },
      yAxis: { type: 'value' },
      series: [{ type: 'line', data: props.data.posts_timeline.map(d => d.count), smooth: true, areaStyle: { opacity: 0.3 } }],
    })
  }

  if (actionChartRef.value) {
    const chart = echarts.init(actionChartRef.value)
    chart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie', radius: ['40%', '70%'],
        data: props.data.action_distribution.map(d => ({ name: d.action, value: d.count })),
      }],
    })
  }

  if (agentChartRef.value) {
    const chart = echarts.init(agentChartRef.value)
    chart.setOption({
      tooltip: {},
      xAxis: { type: 'category', data: props.data.top_agents.map(d => `Agent ${d.agent_id}`) },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: props.data.top_agents.map(d => d.actions), itemStyle: { color: '#2080f0' } }],
    })
  }
}

onMounted(() => nextTick(render))
watch(() => props.data, () => nextTick(render), { deep: true })
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/components/AnalysisDashboard.vue
git commit -m "feat(ui): add AnalysisDashboard interactive charts component"
```

---

## Task 11: 多视角报告详情页

**Files:**
- Create: `web/app/pages/analysis/[id].vue`

- [ ] **Step 1: 创建报告详情页**

```vue
<!-- web/app/pages/analysis/[id].vue -->
<template>
  <div>
    <PageHeader title="深度分析报告" :subtitle="report?.status === 'completed' ? '分析完成' : '分析中...'">
      <template #action>
        <n-button v-if="report?.status === 'analyzing'" :loading="true" disabled>分析进行中</n-button>
      </template>
    </PageHeader>

    <div v-if="report?.status === 'analyzing'">
      <n-card>
        <n-space vertical align="center">
          <n-spin size="large" />
          <n-text>正在进行多视角分析和辩论...</n-text>
          <n-progress type="line" :percentage="progress" style="width: 400px" />
        </n-space>
      </n-card>
    </div>

    <div v-if="report?.status === 'completed' && report.finalReport">
      <!-- 执行摘要 -->
      <n-card title="执行摘要" style="margin-bottom: 16px">
        <n-text>{{ report.finalReport.executive_summary }}</n-text>
      </n-card>

      <!-- 共识与分歧 -->
      <n-grid :cols="2" :x-gap="16" style="margin-bottom: 16px">
        <n-gi>
          <n-card title="共识结论">
            <n-ul>
              <n-li v-for="(c, i) in report.finalReport.consensus" :key="i">{{ c }}</n-li>
            </n-ul>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card title="分歧观点">
            <div v-for="(d, i) in report.finalReport.disagreements" :key="i" style="margin-bottom: 8px">
              <n-tag type="warning" size="small">{{ d.topic }}</n-tag>
              <div v-for="(view, role) in d.sides" :key="role" style="margin-left: 16px; margin-top: 4px">
                <n-text depth="3">{{ roleLabel(role as string) }}：</n-text>
                <n-text>{{ view }}</n-text>
              </div>
            </div>
          </n-card>
        </n-gi>
      </n-grid>

      <!-- 时间线 -->
      <TimelineNarrative :timeline="report.finalReport.timeline_narrative || []" style="margin-bottom: 16px" />

      <!-- 仪表盘 -->
      <AnalysisDashboard :data="report.chartData" style="margin-bottom: 16px" />

      <!-- 各分析师报告 -->
      <n-card title="各分析师报告" style="margin-bottom: 16px">
        <n-tabs type="line">
          <n-tab-pane
            v-for="(ar, role) in report.analystReports"
            :key="role"
            :name="role"
            :tab="roleLabel(role)"
          >
            <n-h4>核心发现</n-h4>
            <n-ul>
              <n-li v-for="(f, i) in ar.findings" :key="i">{{ f }}</n-li>
            </n-ul>
            <n-h4>关键洞察</n-h4>
            <n-ul>
              <n-li v-for="(ins, i) in ar.key_insights" :key="i">{{ ins }}</n-li>
            </n-ul>
            <n-h4>分析叙述</n-h4>
            <n-text>{{ ar.narrative }}</n-text>
          </n-tab-pane>
        </n-tabs>
      </n-card>

      <!-- 辩论记录 -->
      <DebateLog :messages="report.debateLog || []" />

      <!-- 开放问题 -->
      <n-card title="待探索问题" v-if="report.finalReport.open_questions?.length" style="margin-top: 16px">
        <n-ul>
          <n-li v-for="(q, i) in report.finalReport.open_questions" :key="i">{{ q }}</n-li>
        </n-ul>
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAnalysisStore } from '~/stores/analysis'

const route = useRoute()
const store = useAnalysisStore()

const report = ref<any>(null)
const progress = ref(0)
let pollTimer: any = null

const roleLabels: Record<string, string> = {
  data_analyst: '数据分析师',
  sociologist: '社会学家',
  psychologist: '心理学家',
  devils_advocate: '魔鬼代言人',
}

function roleLabel(role: string) { return roleLabels[role] || role }

async function loadReport() {
  const res = await store.fetchOne(route.params.id as string)
  if (res.code === 0) {
    report.value = res.data
    if (res.data.status === 'analyzing') {
      startPolling()
    }
  }
}

function startPolling() {
  pollTimer = setInterval(async () => {
    const res = await store.fetchStatus(route.params.id as string)
    if (res.code === 0) {
      const engineStatus = res.data.engineStatus
      if (engineStatus) {
        progress.value = Math.round((engineStatus.progress || 0) * 100)
      }
      if (res.data.status === 'completed' || res.data.status === 'failed') {
        clearInterval(pollTimer)
        await loadReport()
      }
    }
  }, 3000)
}

onMounted(() => loadReport())
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/pages/analysis/[id].vue
git commit -m "feat(ui): add multi-perspective analysis report page"
```

---

## Task 12: 侧边栏导航与仿真页面集成

**Files:**
- Modify: `web/app/layouts/default.vue`
- Modify: `web/app/pages/simulations/[id].vue`

- [ ] **Step 1: 在侧边栏添加「深度分析」导航**

在 `web/app/layouts/default.vue` 的 menuOptions 中添加：

```typescript
{
  label: '深度分析',
  key: 'analysis',
  icon: renderIcon('carbon:analytics'),
  path: '/analysis',
}
```

- [ ] **Step 2: 在仿真详情页添加「生成深度分析」按钮**

在 `web/app/pages/simulations/[id].vue` 中，当仿真状态为 `completed` 时，添加按钮：

```vue
<n-button
  v-if="simulation?.status === 'completed'"
  type="primary"
  @click="generateAnalysis"
>
  生成深度分析报告
</n-button>
```

对应方法：
```typescript
async function generateAnalysis() {
  const analysisStore = useAnalysisStore()
  const res = await analysisStore.generate(simulation.value.id)
  if (res.code === 0) {
    router.push(`/analysis/${res.data.id}`)
  }
}
```

- [ ] **Step 3: 提交**

```bash
git add web/app/layouts/default.vue web/app/pages/simulations/[id].vue
git commit -m "feat(ui): integrate analysis into navigation and simulation detail page"
```

---

## Task 13: 集成测试

- [ ] **Step 1: 运行所有 Engine 分析师测试**

Run: `cd D:/NLP/oasis && python -m pytest engine/tests/test_analyst_base.py engine/tests/test_debate_engine.py -v`
Expected: 所有测试 PASS

- [ ] **Step 2: 启动 Engine 验证分析端点**

Run: `cd D:/NLP/oasis && python -m uvicorn engine.main:app --port 8000`

- [ ] **Step 3: 启动 Web 验证前端**

Run: `cd D:/NLP/oasis/web && npm run dev`

验证:
1. 侧边栏「深度分析」菜单显示
2. 仿真完成后「生成深度分析报告」按钮可见
3. 分析报告页面正确渲染（时间线、辩论记录、图表）

- [ ] **Step 4: 提交**

```bash
git add -A
git commit -m "feat(analysis): complete P0-2 multi-analyst debate report system"
```
