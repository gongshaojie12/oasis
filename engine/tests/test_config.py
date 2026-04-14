import os

import pytest

from engine.config import Settings


class TestSettings:
    def test_default_values(self):
        settings = Settings(
            _env_file=None,
        )
        assert settings.nuxt_callback_url == "http://localhost:3000"
        assert settings.internal_api_key == "change-me-to-a-random-secret"
        assert settings.max_concurrent_tasks == 2
        assert settings.default_llm_provider == "deepseek"
        assert settings.default_llm_model == "deepseek-chat"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("NUXT_CALLBACK_URL", "http://nuxt:4000")
        monkeypatch.setenv("MAX_CONCURRENT_TASKS", "5")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
        settings = Settings(_env_file=None)
        assert settings.nuxt_callback_url == "http://nuxt:4000"
        assert settings.max_concurrent_tasks == 5
        assert settings.deepseek_api_key == "sk-test-key"

    def test_optional_api_keys_default_none(self):
        settings = Settings(_env_file=None)
        assert settings.deepseek_api_key is None
        assert settings.qwen_api_key is None
        assert settings.doubao_api_key is None
        assert settings.minimax_api_key is None
        assert settings.zhipu_api_key is None
        assert settings.kimi_api_key is None
        assert settings.openai_api_key is None
