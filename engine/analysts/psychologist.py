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
