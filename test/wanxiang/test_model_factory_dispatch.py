# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Test model factory dispatch logic for different providers."""
import wanxiang.models.adapter as adapter
from wanxiang.api.deps import default_model_factory
from wanxiang.api.schemas import ModelConfig


def test_stub_provider_returns_callable():
    call = default_model_factory(ModelConfig(provider="stub"))
    assert callable(call)


def test_openai_compatible_used_for_deepseek(monkeypatch):
    captured = {}

    def fake(api_key, base_url, model_name, **kw):
        captured.update(api_key=api_key, base_url=base_url,
                        model_name=model_name)
        return lambda messages: "x"

    monkeypatch.setattr(adapter, "make_openai_compatible_call", fake)
    monkeypatch.setattr("wanxiang.api.deps.make_openai_compatible_call", fake)
    default_model_factory(ModelConfig(provider="deepseek", api_key="sk-1"))
    assert captured["base_url"] == "https://api.deepseek.com/v1"
    assert captured["model_name"] == "deepseek-chat"
    assert captured["api_key"] == "sk-1"


def test_custom_passes_through_base_url(monkeypatch):
    captured = {}

    def fake(api_key, base_url, model_name, **kw):
        captured.update(base_url=base_url, model_name=model_name)
        return lambda messages: "x"

    monkeypatch.setattr("wanxiang.api.deps.make_openai_compatible_call", fake)
    default_model_factory(ModelConfig(
        provider="custom", api_key="sk-1",
        base_url="https://gw/v1", model_name="my-model"))
    assert captured["base_url"] == "https://gw/v1"
    assert captured["model_name"] == "my-model"
