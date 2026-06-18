# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Provider 预设表(静态,不入库)+ key 脱敏辅助。

新增主流 provider = 往 MODEL_PRESETS 加一行,不碰核心代码。
"""
from __future__ import annotations

MODEL_PRESETS: list[dict] = [
    {"id": "deepseek", "label": "DeepSeek",
     "base_url": "https://api.deepseek.com/v1",
     "default_model": "deepseek-chat",
     "needs_key": True, "allow_custom_base_url": False},
    {"id": "openai", "label": "OpenAI",
     "base_url": "https://api.openai.com/v1",
     "default_model": "gpt-4o-mini",
     "needs_key": True, "allow_custom_base_url": False},
    {"id": "qwen", "label": "通义千问",
     "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
     "default_model": "qwen-plus",
     "needs_key": True, "allow_custom_base_url": False},
    {"id": "custom", "label": "自定义 (OpenAI 兼容)",
     "base_url": None, "default_model": None,
     "needs_key": True, "allow_custom_base_url": True},
    {"id": "stub", "label": "测试桩 (无需 key)",
     "base_url": None, "default_model": None,
     "needs_key": False, "allow_custom_base_url": False},
]


def get_preset(provider_id: str) -> dict | None:
    return next((p for p in MODEL_PRESETS if p["id"] == provider_id), None)


def mask_key(key: str | None) -> str | None:
    """脱敏:保留尾 4 位,其余以 … 代替。空/None → None。"""
    if not key:
        return None
    tail = key[-4:]
    return f"…{tail}" if len(key) <= 4 else f"{key[:3]}…{tail}"
