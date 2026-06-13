# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""engine: 平台无关的模拟内核机制层。

由 OASIS (Apache 2.0, CAMEL-AI.org) 的机制组件抽取重构而来；
平台业务逻辑不在此层。详见 docs/superpowers/specs 的系统设计。
"""
from engine.channel import Channel, AsyncSafeDict
from engine.clock import Clock

__all__ = ["Channel", "AsyncSafeDict", "Clock"]
