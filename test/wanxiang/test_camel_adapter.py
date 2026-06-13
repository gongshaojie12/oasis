# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""camel BaseModelBackend → ModelCall 适配器测试。

用 camel 自带 STUB model（不需要 API key）。
"""
import asyncio

import pytest

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

from wanxiang.models import make_stub_call, wrap_camel_model
from wanxiang.simulation.decision import DecisionRunner
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig
from wanxiang.personas.persona import Persona


def test_wrap_camel_model_returns_async_callable_yielding_str():
    backend = ModelFactory.create(model_platform=ModelPlatformType.STUB,
                                  model_type=ModelType.STUB)
    call = wrap_camel_model(backend)
    out = asyncio.run(call([{"role": "user", "content": "hello"}]))
    assert isinstance(out, str)
    assert len(out) > 0  # stub 至少返回非空


def test_make_stub_call_helper_works():
    call = make_stub_call()
    out = asyncio.run(call([{"role": "user", "content": "anything"}]))
    assert isinstance(out, str)


def test_decision_runner_works_with_wrapped_stub():
    """端到端：把 wrapped stub 喂给 DecisionRunner，确认 pipeline 通。
    注意：stub 不会真返回 JSON，所以 DecisionResult 会带 error，但 runner
    本身不应抛——这正是我们想验证的契约。"""
    call = make_stub_call()
    runner = DecisionRunner()
    persona = Persona(agent_id=0, name="测试用户",
                      demographic={}, personality={}, media={})
    scenario = ScenarioConfig(material="m", question="q",
                              decision_kind=DecisionKind.RATE)
    res = asyncio.run(runner.run(persona, scenario, call))
    # 不抛；要么 value 有效，要么 error 有内容
    assert res.agent_id == 0
    assert res.error is not None or res.value is not None


def test_wrap_passes_messages_in_camel_compatible_form():
    """wrap 出来的 call 应能把 OpenAI 风格 messages 直接传给 arun。"""
    backend = ModelFactory.create(model_platform=ModelPlatformType.STUB,
                                  model_type=ModelType.STUB)
    call = wrap_camel_model(backend)
    # 多角色 messages（system + user）
    messages = [
        {"role": "system", "content": "你是测试用户"},
        {"role": "user", "content": "请回答"},
    ]
    out = asyncio.run(call(messages))
    assert isinstance(out, str)


def test_make_deepseek_call_returns_callable_without_real_request():
    """make_deepseek_call 不应在构造时发请求；只要能拿到 callable 即可
    （此处不实际调用——避免依赖 DEEPSEEK_API_KEY 与网络）。"""
    from wanxiang.models import make_deepseek_call
    call = make_deepseek_call(api_key="sk-fake-not-used-in-this-test")
    assert callable(call)
    # 不实际 await call — 那需要真 key
