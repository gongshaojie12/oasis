# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""依赖注入：模型工厂可在测试期被替换。"""
from __future__ import annotations

from wanxiang.api.schemas import ModelConfig
from wanxiang.models import (make_deepseek_call, make_openai_compatible_call,
                             make_stub_call)
from wanxiang.simulation.decision import ModelCall


def default_model_factory(cfg: ModelConfig) -> ModelCall:
    """根据 ModelConfig 选择 ModelCall 实现。测试可 monkeypatch 此函数。"""
    if cfg.provider == "stub":
        return make_stub_call()
    from wanxiang.api.model_presets import get_preset
    preset = get_preset(cfg.provider) or {}
    base_url = cfg.base_url or preset.get("base_url")
    model_name = cfg.model_name or preset.get("default_model")
    if not base_url or not model_name:
        raise ValueError(
            f"provider={cfg.provider!r} 缺 base_url/model_name")
    return make_openai_compatible_call(
        api_key=cfg.api_key, base_url=base_url, model_name=model_name)


def get_model_factory():
    """FastAPI dependency: returns the factory CALLABLE itself."""
    return default_model_factory


def get_model_factory_for_worker():
    """Worker-side model factory.

    Celery workers don't have FastAPI's Depends chain, so they call this
    helper directly to obtain the same factory the API process uses.
    Reads provider config from each request's ``model`` field as usual;
    secret material (e.g. DeepSeek API key) must come from env vars that
    the worker container also has access to.
    """
    return default_model_factory
