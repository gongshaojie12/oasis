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
