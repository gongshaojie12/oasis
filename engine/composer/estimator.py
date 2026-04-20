from __future__ import annotations

from engine.composer.schema import ScenarioConfig, ResourceEstimate


class ResourceEstimator:
    AVG_TOKENS_PER_CALL = 800
    AVG_SECONDS_PER_CALL = 2.0
    COST_PER_1K_TOKENS = 0.003

    def estimate(self, config: ScenarioConfig) -> ResourceEstimate:
        calls_per_step = config.num_agents
        total_calls = calls_per_step * config.num_steps
        total_tokens = total_calls * self.AVG_TOKENS_PER_CALL
        total_seconds = total_calls * self.AVG_SECONDS_PER_CALL
        total_cost = (total_tokens / 1000) * self.COST_PER_1K_TOKENS

        return ResourceEstimate(
            llm_calls=total_calls,
            estimated_tokens=total_tokens,
            estimated_minutes=round(total_seconds / 60, 1),
            estimated_cost_usd=round(total_cost, 2),
        )
