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
