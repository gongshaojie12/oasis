# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""依赖注入：模型工厂可在测试期被替换。"""
from __future__ import annotations

from wanxiang.api.schemas import ModelConfig
from wanxiang.models import make_deepseek_call, make_stub_call
from wanxiang.simulation.decision import ModelCall


def default_model_factory(cfg: ModelConfig) -> ModelCall:
    """根据 ModelConfig 选择 ModelCall 实现。测试可 monkeypatch 此函数。"""
    if cfg.provider == "stub":
        return make_stub_call()
    if cfg.provider == "deepseek":
        kwargs = {}
        if cfg.model_name:
            kwargs["model_name"] = cfg.model_name
        return make_deepseek_call(api_key=cfg.api_key, **kwargs)
    raise ValueError(f"unknown provider: {cfg.provider}")


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
