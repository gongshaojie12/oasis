# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""L1 决策响应动作（平台无关）。

agent 看完场景材料后输出的结构化决策，可直接聚合成群体分布。
对标 Aaru 的"看材料→输出选择/打分"。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from wanxiang.actions.layers import ActionLayer


@dataclass(frozen=True)
class ActionSpec:
    """一个动作的元数据描述（词表项），不含执行逻辑。"""
    name: str
    layer: ActionLayer
    params: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""


L1_ACTIONS: tuple[ActionSpec, ...] = (
    ActionSpec("rate", ActionLayer.L1_DECISION, ("score",),
               "对材料给出 0-10 购买/喜好评分"),
    ActionSpec("choose", ActionLayer.L1_DECISION, ("option",),
               "在多个选项中选择其一"),
    ActionSpec("click_probability", ActionLayer.L1_DECISION, ("probability",),
               "点击/进一步了解的概率 0-1"),
    ActionSpec("sentiment", ActionLayer.L1_DECISION, ("polarity",),
               "对材料的态度极性 -1..1"),
    ActionSpec("willingness_to_pay", ActionLayer.L1_DECISION, ("price",),
               "愿意支付的价格"),
)
