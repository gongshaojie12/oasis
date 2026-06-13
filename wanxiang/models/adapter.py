# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""把 camel.models.BaseModelBackend 包装成 wanxiang 的 ModelCall。

ModelCall: async (messages: list[dict]) -> str
camel:     async arun(messages) -> ChatCompletion
本模块负责类型转换 + 抽取 .choices[0].message.content。
"""
from __future__ import annotations

from typing import Any

from camel.models import BaseModelBackend, ModelFactory
from camel.types import ModelPlatformType, ModelType

from wanxiang.simulation.decision import ModelCall


def wrap_camel_model(backend: BaseModelBackend) -> ModelCall:
    """把一个 camel BaseModelBackend 包装为 ModelCall。"""

    async def call(messages: list[dict]) -> str:
        # camel 的 arun 接受 OpenAI 风格 typed dict；普通 dict 在运行期通常也接受
        resp = await backend.arun(messages=messages)
        # ChatCompletion → 第一个 choice 的 message content
        content = resp.choices[0].message.content
        return content if content is not None else ""

    return call


def make_stub_call() -> ModelCall:
    """camel 自带 STUB model 的便捷工厂，用于测试与冒烟（无需 API key）。"""
    backend = ModelFactory.create(model_platform=ModelPlatformType.STUB,
                                  model_type=ModelType.STUB)
    return wrap_camel_model(backend)


def make_deepseek_call(
    api_key: str,
    model_name: str = "deepseek-chat",
    **kwargs: Any,
) -> ModelCall:
    """DeepSeek 模型的便捷工厂。

    生产默认值（spec §D3）。`api_key` 必传；其它参数透传给 ModelFactory。
    不在构造时发起实际请求——只在 await 返回的 call 时。
    """
    backend = ModelFactory.create(
        model_platform=ModelPlatformType.DEEPSEEK,
        model_type=model_name,
        api_key=api_key,
        **kwargs,
    )
    return wrap_camel_model(backend)
