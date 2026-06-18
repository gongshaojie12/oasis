# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Test ModelConfig schema validation."""
import pytest
from pydantic import ValidationError
from wanxiang.api.schemas import ModelConfig


def test_stub_ok_without_key():
    assert ModelConfig(provider="stub").api_key is None


def test_deepseek_requires_key():
    with pytest.raises(ValidationError):
        ModelConfig(provider="deepseek")


def test_openai_requires_key():
    with pytest.raises(ValidationError):
        ModelConfig(provider="openai")


def test_custom_requires_base_url():
    with pytest.raises(ValidationError):
        ModelConfig(provider="custom", api_key="sk-x")


def test_custom_ok_with_key_and_base_url():
    c = ModelConfig(provider="custom", api_key="sk-x",
                    base_url="https://gw/v1")
    assert c.base_url == "https://gw/v1"


def test_qwen_ok_with_key():
    assert ModelConfig(provider="qwen", api_key="sk-x").provider == "qwen"
