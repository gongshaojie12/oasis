# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""场景配置：给虚拟人看什么、问什么、期望什么类型的决策输出。

DecisionKind 对应 L1 决策响应动作（spec §5.1）：
- RATE: 0-10 整数评分 → 字段 score
- CHOOSE: 多选一 → 字段 option（必须在 options 中）
- CLICK_PROBABILITY: 0-1 → 字段 probability
- SENTIMENT: -1..1 → 字段 polarity
- WTP: 愿意支付的价格（数字） → 字段 price

P4 i18n: ScenarioConfig.locale = "zh"|"en"。决定 render_user_message()
输出语言。默认 zh（向后兼容所有现有调用）。
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


# Schema hints embedded in user prompt. zh keeps original wording; en is fresh.
_SCHEMA_HINT = {
    "zh": {
        DecisionKind.RATE: '{"score": <0-10 整数>}',
        DecisionKind.CHOOSE: '{"option": "<必须是给定 options 之一>"}',
        DecisionKind.CLICK_PROBABILITY: '{"probability": <0-1 小数>}',
        DecisionKind.SENTIMENT: '{"polarity": <-1 到 1 小数>}',
        DecisionKind.WTP: '{"price": <非负数字，单位元>}',
    },
    "en": {
        DecisionKind.RATE: '{"score": <integer 0-10>}',
        DecisionKind.CHOOSE: '{"option": "<must be one of the given options>"}',
        DecisionKind.CLICK_PROBABILITY: '{"probability": <decimal 0-1>}',
        DecisionKind.SENTIMENT: '{"polarity": <decimal -1 to 1>}',
        DecisionKind.WTP: '{"price": <non-negative number>}',
    },
}


_LABELS = {
    "zh": {
        "material": "【材料】",
        "options": "【可选项】",
        "question": "【问题】",
        "instruction": ("请只用一行严格 JSON 回答，格式：{schema}。"
                          "不要添加任何解释、前后缀或代码块标记。"),
    },
    "en": {
        "material": "[Material]",
        "options": "[Options]",
        "question": "[Question]",
        "instruction": ("Reply with exactly one line of strict JSON, "
                          "format: {schema}. Do not add any explanation, "
                          "prefix, suffix, or code fence."),
    },
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
    # P4 i18n: prompt locale. zh 默认（向后兼容）。
    locale: str = "zh"

    def __post_init__(self):
        if self.decision_kind is DecisionKind.CHOOSE and not self.options:
            raise ValueError(
                "CHOOSE decision_kind requires non-empty options tuple")
        if self.feed_k < 0:
            raise ValueError("feed_k must be >= 0")

    def render_user_message(self) -> str:
        loc = self.locale if self.locale in ("zh", "en") else "zh"
        labels = _LABELS[loc]
        parts: list[str] = []
        parts.append(labels["material"])
        parts.append(self.material)
        if self.decision_kind is DecisionKind.CHOOSE and self.options:
            parts.append(labels["options"] + " / ".join(self.options))
        parts.append(labels["question"] + self.question)
        schema = _SCHEMA_HINT[loc][self.decision_kind]
        parts.append(labels["instruction"].format(schema=schema))
        return "\n".join(parts)
