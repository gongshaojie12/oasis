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
