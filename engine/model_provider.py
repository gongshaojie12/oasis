# ============= Copyright 2026 @ WANXIANG. All Rights Reserved. =============
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
# ===========================================================================
"""engine.model_provider — 模型 provider 抽象 (spec §3.1).

实现实际落点为 ``wanxiang.models.adapter`` — 这里做 re-export 以让 spec §3.1
列举的 7 个引擎模块在 ``engine/`` 名空间下都能 import 到。

历史背景：M0 引擎重构时模型 provider 与业务侧 ModelConfig schema 强绑定
（DeepSeek/Stub provider 切换），故把实现放到了 ``wanxiang/models/`` 而非
``engine/``。本模块保留 spec 中的位置约定，避免后续阅读者按 spec 找不到入口。
"""
from wanxiang.models.adapter import (
    ModelCall, wrap_camel_model, make_stub_call, make_deepseek_call,
)

__all__ = [
    "ModelCall", "wrap_camel_model", "make_stub_call", "make_deepseek_call",
]
