import pytest

from engine.config import Settings
from engine.llm.provider import (
    LLMProviderRegistry,
    ProviderSpec,
    create_model,
    _resolve_openai_model_type,
)
from camel.types import ModelPlatformType, ModelType


class TestLLMProviderRegistry:
    def setup_method(self):
        self.registry = LLMProviderRegistry()

    def test_builtin_providers_registered(self):
        providers = self.registry.list_providers()
        assert "deepseek" in providers
        assert "qwen" in providers
        assert "doubao" in providers
        assert "minimax" in providers
        assert "zhipu" in providers
        assert "kimi" in providers
        assert "openai" in providers
        assert len(providers) == 7

    def test_get_existing_provider(self):
        spec = self.registry.get("deepseek")
        assert spec.name == "deepseek"
        assert spec.base_url == "https://api.deepseek.com/v1"
        assert "deepseek-chat" in spec.models

    def test_get_unknown_provider_raises(self):
        with pytest.raises(KeyError, match="Unknown LLM provider 'nonexistent'"):
            self.registry.get("nonexistent")

    def test_list_models(self):
        models = self.registry.list_models("qwen")
        assert "qwen-plus" in models
        assert "qwen-max" in models
        assert "qwen-turbo" in models

    def test_register_custom_provider(self):
        custom = ProviderSpec(
            name="custom-llm",
            base_url="https://custom.example.com/v1",
            models=["custom-model-1"],
            api_key_env="CUSTOM_API_KEY",
            platform_type=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
        )
        self.registry.register(custom)
        assert "custom-llm" in self.registry.list_providers()
        assert self.registry.get("custom-llm").base_url == "https://custom.example.com/v1"


class TestResolveOpenAIModelType:
    def test_gpt_4o(self):
        assert _resolve_openai_model_type("gpt-4o") == ModelType.GPT_4O

    def test_gpt_4o_mini(self):
        assert _resolve_openai_model_type("gpt-4o-mini") == ModelType.GPT_4O_MINI

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown OpenAI model"):
            _resolve_openai_model_type("gpt-99")


class TestCreateModel:
    def test_missing_api_key_raises(self):
        settings = Settings(_env_file=None)
        with pytest.raises(ValueError, match="API key for provider 'deepseek' is not configured"):
            create_model("deepseek", "deepseek-chat", settings)

    def test_invalid_model_for_provider_raises(self):
        settings = Settings(_env_file=None, deepseek_api_key="sk-test")
        with pytest.raises(ValueError, match="not registered for provider"):
            create_model("deepseek", "nonexistent-model", settings)

    def test_unknown_provider_raises(self):
        settings = Settings(_env_file=None)
        with pytest.raises(KeyError, match="Unknown LLM provider"):
            create_model("nonexistent", "some-model", settings)


from engine.llm.tiered import AgentTier, TierConfig, TieredModelAssigner


class TestTieredModelAssigner:
    def test_assign_tiers_covers_all_agents(self):
        settings = Settings(_env_file=None)
        assigner = TieredModelAssigner(settings=settings)
        assignments = assigner.assign_tiers(100)
        assert len(assignments) == 100
        assert set(assignments.keys()) == set(range(100))

    def test_assign_tiers_distribution(self):
        settings = Settings(_env_file=None)
        assigner = TieredModelAssigner(settings=settings, seed=123)
        assignments = assigner.assign_tiers(100)
        core_count = sum(1 for t in assignments.values() if t == AgentTier.CORE)
        normal_count = sum(1 for t in assignments.values() if t == AgentTier.NORMAL)
        bg_count = sum(1 for t in assignments.values() if t == AgentTier.BACKGROUND)
        assert core_count == 10
        assert normal_count == 25
        assert bg_count == 65
        assert core_count + normal_count + bg_count == 100

    def test_assign_tiers_small_count(self):
        settings = Settings(_env_file=None)
        assigner = TieredModelAssigner(settings=settings)
        assignments = assigner.assign_tiers(3)
        assert len(assignments) == 3
        all_tiers = set(assignments.values())
        assert len(all_tiers) >= 1  # at least one tier assigned

    def test_assign_tiers_single_agent(self):
        settings = Settings(_env_file=None)
        assigner = TieredModelAssigner(settings=settings)
        assignments = assigner.assign_tiers(1)
        assert len(assignments) == 1
        assert 0 in assignments

    def test_assign_tiers_deterministic_with_same_seed(self):
        settings = Settings(_env_file=None)
        a1 = TieredModelAssigner(settings=settings, seed=99).assign_tiers(50)
        a2 = TieredModelAssigner(settings=settings, seed=99).assign_tiers(50)
        assert a1 == a2

    def test_tier_summary(self):
        settings = Settings(_env_file=None)
        assigner = TieredModelAssigner(settings=settings)
        summary = assigner.get_tier_summary(100)
        assert "core" in summary
        assert "normal" in summary
        assert "background" in summary
        assert summary["core"] + summary["normal"] + summary["background"] == 100

    def test_get_model_for_unknown_tier_raises(self):
        settings = Settings(_env_file=None)
        assigner = TieredModelAssigner(
            settings=settings,
            tier_configs=[],
        )
        with pytest.raises(ValueError, match="No configuration found"):
            assigner.get_model_for_tier(AgentTier.CORE)
