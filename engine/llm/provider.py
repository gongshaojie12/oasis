from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

from engine.config import Settings


@dataclass(frozen=True)
class ProviderSpec:
    """Specification for a single LLM provider."""
    name: str
    base_url: str
    models: list[str]
    api_key_env: str
    platform_type: ModelPlatformType


# All 7 providers with their OpenAI-compatible endpoints.
_BUILTIN_PROVIDERS: list[ProviderSpec] = [
    ProviderSpec(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        models=["deepseek-chat", "deepseek-reasoner"],
        api_key_env="DEEPSEEK_API_KEY",
        platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    ),
    ProviderSpec(
        name="qwen",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        models=["qwen-plus", "qwen-max", "qwen-turbo"],
        api_key_env="QWEN_API_KEY",
        platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    ),
    ProviderSpec(
        name="doubao",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        models=["doubao-1-5-pro-256k", "doubao-1-5-lite-32k"],
        api_key_env="DOUBAO_API_KEY",
        platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    ),
    ProviderSpec(
        name="minimax",
        base_url="https://api.minimax.chat/v1",
        models=["MiniMax-Text-01", "abab6.5s"],
        api_key_env="MINIMAX_API_KEY",
        platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    ),
    ProviderSpec(
        name="zhipu",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        models=["glm-4-plus", "glm-4-flash"],
        api_key_env="ZHIPU_API_KEY",
        platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    ),
    ProviderSpec(
        name="kimi",
        base_url="https://api.moonshot.cn/v1",
        models=["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        api_key_env="KIMI_API_KEY",
        platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    ),
    ProviderSpec(
        name="openai",
        base_url="https://api.openai.com/v1",
        models=["gpt-4o", "gpt-4o-mini"],
        api_key_env="OPENAI_API_KEY",
        platform_type=ModelPlatformType.OPENAI,
    ),
]


class LLMProviderRegistry:
    """Registry of LLM providers and their configurations."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderSpec] = {}
        for spec in _BUILTIN_PROVIDERS:
            self._providers[spec.name] = spec

    def get(self, name: str) -> ProviderSpec:
        if name not in self._providers:
            available = ", ".join(sorted(self._providers.keys()))
            raise KeyError(
                f"Unknown LLM provider '{name}'. Available: {available}"
            )
        return self._providers[name]

    def list_providers(self) -> list[str]:
        return sorted(self._providers.keys())

    def list_models(self, provider_name: str) -> list[str]:
        return list(self.get(provider_name).models)

    def register(self, spec: ProviderSpec) -> None:
        self._providers[spec.name] = spec


def create_model(
    provider_name: str,
    model_id: str,
    settings: Settings,
    registry: Optional[LLMProviderRegistry] = None,
):
    if registry is None:
        registry = LLMProviderRegistry()

    spec = registry.get(provider_name)

    if model_id not in spec.models:
        raise ValueError(
            f"Model '{model_id}' is not registered for provider "
            f"'{provider_name}'. Available: {spec.models}"
        )

    api_key = getattr(settings, spec.api_key_env.lower(), None)
    if not api_key:
        raise ValueError(
            f"API key for provider '{provider_name}' is not configured. "
            f"Set the {spec.api_key_env} environment variable."
        )

    if spec.platform_type == ModelPlatformType.OPENAI:
        model_type = _resolve_openai_model_type(model_id)
        os.environ["OPENAI_API_KEY"] = api_key
        return ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=model_type,
        )

    os.environ["OPENAI_COMPATIBILIY_API_KEY"] = api_key
    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
        model_type=model_id,
        api_key=api_key,
        url=spec.base_url,
        model_config_dict={"max_tokens": 4096},
    )


def _resolve_openai_model_type(model_id: str) -> ModelType:
    _mapping = {
        "gpt-4o": ModelType.GPT_4O,
        "gpt-4o-mini": ModelType.GPT_4O_MINI,
    }
    if model_id not in _mapping:
        raise ValueError(
            f"Unknown OpenAI model '{model_id}'. "
            f"Supported: {list(_mapping.keys())}"
        )
    return _mapping[model_id]
