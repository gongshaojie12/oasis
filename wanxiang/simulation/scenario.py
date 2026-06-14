# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""场景配置：给虚拟人看什么、问什么、期望什么类型的决策输出。

DecisionKind 对应 L1 决策响应动作（spec §5.1）：
- RATE: 0-10 整数评分 → 字段 score
- CHOOSE: 多选一 → 字段 option（必须在 options 中）
- CLICK_PROBABILITY: 0-1 → 字段 probability
- SENTIMENT: -1..1 → 字段 polarity
- WTP: 愿意支付的价格（数字） → 字段 price
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from wanxiang.media.environment import MediaItem


class DecisionKind(Enum):
    RATE = "rate"
    CHOOSE = "choose"
    CLICK_PROBABILITY = "click_probability"
    SENTIMENT = "sentiment"
    WTP = "willingness_to_pay"


_SCHEMA_HINT = {
    DecisionKind.RATE: '{"score": <0-10 整数>}',
    DecisionKind.CHOOSE: '{"option": "<必须是给定 options 之一>"}',
    DecisionKind.CLICK_PROBABILITY: '{"probability": <0-1 小数>}',
    DecisionKind.SENTIMENT: '{"polarity": <-1 到 1 小数>}',
    DecisionKind.WTP: '{"price": <非负数字，单位元>}',
}


@dataclass(frozen=True)
class ScenarioConfig:
    material: str
    question: str
    decision_kind: DecisionKind
    options: tuple[str, ...] | None = None
    # M4 MVP: 动态信息流（每个 persona 决策前看到的内容）
    media_pool: tuple[MediaItem, ...] = ()
    feed_k: int = 0

    def __post_init__(self):
        if self.decision_kind is DecisionKind.CHOOSE and not self.options:
            raise ValueError(
                "CHOOSE decision_kind requires non-empty options tuple")
        if self.feed_k < 0:
            raise ValueError("feed_k must be >= 0")

    def render_user_message(self) -> str:
        parts: list[str] = []
        parts.append("【材料】")
        parts.append(self.material)
        if self.decision_kind is DecisionKind.CHOOSE and self.options:
            parts.append("【可选项】" + " / ".join(self.options))
        parts.append("【问题】" + self.question)
        parts.append(
            "请只用一行严格 JSON 回答，格式："
            f"{_SCHEMA_HINT[self.decision_kind]}。"
            "不要添加任何解释、前后缀或代码块标记。")
        return "\n".join(parts)
