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
