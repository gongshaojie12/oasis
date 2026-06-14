# ============= Copyright 2026 @ WANXIANG. All Rights Reserved. =============
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
# ===========================================================================
"""engine.platform_base — 平台插件抽象基类 + 动作注册协议 (spec §3.1).

平台方言（L3）的运行时合约由 ``wanxiang.actions.dialect.PlatformDialect``
+ ``DialectLoader`` 落地。本模块按 spec §3.1 的位置约定 re-export，并定义
``PlatformPlugin`` 协议作为 spec §3 ④ 业务/产品层接入平台时的稳定签名。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from wanxiang.actions.dialect import PlatformDialect, DialectLoader
from wanxiang.actions.layers import ActionLayer, SimulationMode


@runtime_checkable
class PlatformPlugin(Protocol):
    """spec §3.1 + 5.4：每个平台 = 声明式 yaml + 少量特有逻辑。

    实现该 protocol 即可作为 L3 平台插件被 ``DialectLoader`` 加载，
    或在更高层做 step-level 编排。
    """
    @property
    def platform_id(self) -> str: ...
    def dialect(self) -> PlatformDialect: ...
    def supports_layer(self, layer: ActionLayer) -> bool: ...


__all__ = [
    "PlatformDialect", "DialectLoader", "ActionLayer", "SimulationMode",
    "PlatformPlugin",
]
