# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""按模拟档位解析可用动作空间（spec §5.2 组合规则的封顶 API）。"""
from __future__ import annotations

from wanxiang.actions.dialect import PlatformDialect
from wanxiang.actions.l1_decision import L1_ACTIONS
from wanxiang.actions.l2_social import L2_ACTIONS
from wanxiang.actions.layers import ActionLayer, SimulationMode


def resolve_action_space(
    mode: SimulationMode,
    dialect: PlatformDialect | None = None,
) -> set[str]:
    """返回该档位下可用的动作名集合。

    - DECISION_ONLY: 仅 L1
    - SOCIAL: L1 + 全部 L2 抽象动作
    - PLATFORM: L1 + 被 dialect 支持的 L2 动作（按平台过滤）

    规则（spec §5.2）：PLATFORM 必须给 dialect；其它档不接受 dialect。
    """
    if mode.requires_platform() and dialect is None:
        raise ValueError("PLATFORM mode requires a platform dialect")
    if not mode.requires_platform() and dialect is not None:
        raise ValueError("only PLATFORM mode accepts a dialect")

    layers = mode.active_layers()
    space: set[str] = set()

    if ActionLayer.L1_DECISION in layers:
        space.update(a.name for a in L1_ACTIONS)

    if ActionLayer.L2_SOCIAL in layers:
        if ActionLayer.L3_PLATFORM in layers:
            # PLATFORM：L2 动作按方言过滤
            space.update(dialect.supported_action_names())
        else:
            # SOCIAL：全部 L2 抽象动作
            space.update(a.name for a in L2_ACTIONS)

    return space
