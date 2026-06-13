# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""models: camel BaseModelBackend → ModelCall 适配器（spec §M7 模型可配置）。"""
from wanxiang.models.adapter import (make_deepseek_call, make_stub_call,
                                      wrap_camel_model)

__all__ = ["wrap_camel_model", "make_stub_call", "make_deepseek_call"]
