# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""把 camel.models.BaseModelBackend 包装成 wanxiang 的 ModelCall。

ModelCall: async (messages: list[dict]) -> str
camel:     async arun(messages) -> ChatCompletion
本模块负责类型转换 + 抽取 .choices[0].message.content。
"""
from __future__ import annotations

import hashlib
import json
import random
import re
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


_OPTIONS_RE = re.compile(r"【可选项】\s*(.+?)\s*(?:【问题】|$)", re.DOTALL)


def make_stub_call() -> ModelCall:
    """开发/测试用 stub：根据 user prompt 中的 schema 关键字返回合规 JSON。

    替代 camel 自带 STUB（那个总返回 'Lorem Ipsum'，不符合 wanxiang 的
    结构化决策契约）。本 stub 用 hash(system+user) 作为种子，保证：
    - 同样的输入永远同样的输出（可重现）
    - 不同 persona（不同 system prompt）大概率给不同回答，让 aggregate 有分布
    """

    async def call(messages: list[dict]) -> str:
        system = next((m["content"] for m in messages
                       if m.get("role") == "system"), "")
        user = next((m["content"] for m in messages
                     if m.get("role") == "user"), "")
        # 确定性种子
        h = hashlib.md5((system + "||" + user).encode("utf-8")).hexdigest()
        rng = random.Random(int(h[:8], 16))

        ul = user.lower()
        if "score" in ul:
            return json.dumps({"score": rng.randint(1, 10)})
        if "option" in ul or "选项" in user:
            m = _OPTIONS_RE.search(user)
            if m:
                opts = [s.strip() for s in re.split(r"[/，,]", m.group(1))
                        if s.strip()]
                if opts:
                    return json.dumps({"option": rng.choice(opts)},
                                      ensure_ascii=False)
            return json.dumps({"option": "?"}, ensure_ascii=False)
        if "polarity" in ul:
            return json.dumps({"polarity": round(rng.uniform(-1, 1), 2)})
        if "probability" in ul:
            return json.dumps({"probability": round(rng.uniform(0, 1), 2)})
        if "price" in ul:
            return json.dumps({"price": rng.randint(1, 100)})
        return json.dumps({"score": 5})

    return call


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
