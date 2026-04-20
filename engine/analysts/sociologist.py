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
