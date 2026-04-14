from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from camel.models import BaseModelBackend

from engine.config import Settings
from engine.llm.provider import LLMProviderRegistry, create_model


class AgentTier(str, Enum):
    """Cost tier for agent LLM assignment."""

    CORE = "core"
    NORMAL = "normal"
    BACKGROUND = "background"


@dataclass
class TierConfig:
    """Configuration for a single agent tier."""

    tier: AgentTier
    percentage: float  # 0.0 to 1.0
    provider: str
    model: str


DEFAULT_TIER_CONFIGS: list[TierConfig] = [
    TierConfig(
        tier=AgentTier.CORE,
        percentage=0.10,
        provider="qwen",
        model="qwen-max",
    ),
    TierConfig(
        tier=AgentTier.NORMAL,
        percentage=0.25,
        provider="deepseek",
        model="deepseek-chat",
    ),
    TierConfig(
        tier=AgentTier.BACKGROUND,
        percentage=0.65,
        provider="zhipu",
        model="glm-4-flash",
    ),
]


class TieredModelAssigner:
    """Assigns LLM models to agents based on cost tiers.

    Given a total number of agents, splits them into core (KOL),
    normal (active), and background (silent) tiers, then creates
    appropriate model backends for each tier.
    """

    def __init__(
        self,
        settings: Settings,
        tier_configs: Optional[list[TierConfig]] = None,
        registry: Optional[LLMProviderRegistry] = None,
        seed: int = 42,
    ) -> None:
        self._settings = settings
        self._tier_configs = tier_configs if tier_configs is not None else DEFAULT_TIER_CONFIGS
        self._registry = registry or LLMProviderRegistry()
        self._rng = random.Random(seed)
        self._model_cache: dict[tuple[str, str], BaseModelBackend] = {}

    def _get_or_create_model(
        self, provider: str, model_id: str
    ) -> BaseModelBackend:
        """Return a cached model or create a new one."""
        cache_key = (provider, model_id)
        if cache_key not in self._model_cache:
            self._model_cache[cache_key] = create_model(
                provider_name=provider,
                model_id=model_id,
                settings=self._settings,
                registry=self._registry,
            )
        return self._model_cache[cache_key]

    def assign_tiers(self, num_agents: int) -> dict[int, AgentTier]:
        """Assign a tier to each agent index.

        Agents are shuffled and then partitioned sequentially according
        to configured percentages.  Returns a mapping from agent_id to tier.
        """
        agent_ids = list(range(num_agents))
        self._rng.shuffle(agent_ids)

        assignments: dict[int, AgentTier] = {}
        offset = 0
        for i, tc in enumerate(self._tier_configs):
            if i == len(self._tier_configs) - 1:
                # Last tier gets all remaining agents
                count = num_agents - offset
            else:
                count = round(tc.percentage * num_agents)
            for agent_id in agent_ids[offset : offset + count]:
                assignments[agent_id] = tc.tier
            offset += count

        return assignments

    def get_model_for_tier(self, tier: AgentTier) -> BaseModelBackend:
        """Return the LLM model backend for the given tier."""
        for tc in self._tier_configs:
            if tc.tier == tier:
                return self._get_or_create_model(tc.provider, tc.model)
        raise ValueError(f"No configuration found for tier '{tier.value}'")

    def assign_models(
        self, num_agents: int
    ) -> dict[int, tuple[AgentTier, BaseModelBackend]]:
        """Assign both a tier and a model to each agent.

        Returns a mapping from agent_id to (tier, model).
        """
        tier_map = self.assign_tiers(num_agents)
        result: dict[int, tuple[AgentTier, BaseModelBackend]] = {}
        for agent_id, tier in tier_map.items():
            model = self.get_model_for_tier(tier)
            result[agent_id] = (tier, model)
        return result

    def get_tier_summary(self, num_agents: int) -> dict[str, int]:
        """Return a count of agents in each tier for diagnostics."""
        tier_map = self.assign_tiers(num_agents)
        summary: dict[str, int] = {}
        for tier in AgentTier:
            summary[tier.value] = sum(
                1 for t in tier_map.values() if t == tier
            )
        return summary
