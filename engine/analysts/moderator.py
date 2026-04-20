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
