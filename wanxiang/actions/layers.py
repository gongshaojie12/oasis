# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""三层动作空间与三档模拟模式定义。

设计见 spec §5：
- L1 决策响应（平台无关，Aaru 路线）
- L2 通用社交（OASIS 内核，跨平台抽象语义）
- L3 平台方言（国内外差异，声明式映射）

三档递进组合，不可跳层：DECISION_ONLY=L1 / SOCIAL=L1+L2 / PLATFORM=L1+L2+L3。
"""
from __future__ import annotations

from enum import Enum


class ActionLayer(Enum):
    L1_DECISION = 1
    L2_SOCIAL = 2
    L3_PLATFORM = 3


class SimulationMode(Enum):
    DECISION_ONLY = "decision_only"  # L1
    SOCIAL = "social"                # L1 + L2
    PLATFORM = "platform"            # L1 + L2 + L3

    def active_layers(self) -> list[ActionLayer]:
        """返回该档启用的层，逐层叠加，不可跳层。"""
        if self is SimulationMode.DECISION_ONLY:
            return [ActionLayer.L1_DECISION]
        if self is SimulationMode.SOCIAL:
            return [ActionLayer.L1_DECISION, ActionLayer.L2_SOCIAL]
        # PLATFORM
        return [
            ActionLayer.L1_DECISION,
            ActionLayer.L2_SOCIAL,
            ActionLayer.L3_PLATFORM,
        ]

    def requires_platform(self) -> bool:
        """只有 PLATFORM 档需要指定具体平台方言。"""
        return self is SimulationMode.PLATFORM

    @classmethod
    def from_string(cls, name: str) -> "SimulationMode":
        for mode in cls:
            if mode.value == name:
                return mode
        raise ValueError(f"unknown simulation mode: {name!r}")
