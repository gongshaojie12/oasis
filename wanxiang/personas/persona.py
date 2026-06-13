# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Persona: 一个虚拟人的完整画像（冻结、可值比较）。

spec §M2 三组特质：
- demographic: 人口标签（年龄/性别/城市/收入/职业/教育 …）
- personality: 个性向量（价格敏感度/尝鲜意愿/健康意识/从众倾向 …）
- media:       媒体消费习惯（小红书/抖音/微信/B站/微博 … 权重 0-1）

每个 group 是 dict[str, Any]，键名由调用方决定（spec 目标 220+ 维，
本数据层不约束维度数，只提供容器与一致的 system prompt 渲染）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Persona:
    agent_id: int
    name: str
    demographic: dict[str, Any] = field(default_factory=dict)
    personality: dict[str, Any] = field(default_factory=dict)
    media: dict[str, Any] = field(default_factory=dict)

    def trait_count(self) -> int:
        """三组特质合计维数（不含 name/agent_id）。"""
        return len(self.demographic) + len(self.personality) + len(self.media)

    def render_system_prompt(self) -> str:
        """把画像渲染为中文 system prompt 文本，供 LLM 调用。"""
        parts: list[str] = []
        parts.append(f"你是「{self.name}」。")
        if self.demographic:
            parts.append("【人口特征】")
            for k, v in self.demographic.items():
                parts.append(f"- {k}：{v}")
        else:
            parts.append("【人口特征】（未提供）")
        if self.personality:
            parts.append("【个性与决策倾向】（0-1 区间，越大越显著）")
            for k, v in self.personality.items():
                parts.append(f"- {k}：{v}")
        else:
            parts.append("【个性与决策倾向】（未提供）")
        if self.media:
            parts.append("【媒体消费习惯】（0-1 区间，越大越常用/越信任）")
            for k, v in self.media.items():
                parts.append(f"- {k}：{v}")
        else:
            parts.append("【媒体消费习惯】（未提供）")
        parts.append(
            "请基于以上画像，在被问到任何决策、态度或选择时，按这个人的"
            "真实视角作答；不要解释你是 AI，不要复述画像。")
        return "\n".join(parts)
