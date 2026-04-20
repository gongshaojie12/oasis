from __future__ import annotations

import json
import logging
from typing import Callable, Awaitable, Optional

from engine.composer.schema import ScenarioDNA, ScenarioConfig

logger = logging.getLogger("engine.composer.mixer")

MIX_PROMPT = """You are a social media simulation scenario designer. Two scenario DNAs have been mixed by weighted average. Based on the blended DNA values, generate a complete simulation configuration.

DNA A (weight {weight_a}):
{dna_a}

DNA B (weight {weight_b}):
{dna_b}

Blended DNA:
{blended}

Generate a JSON simulation config that matches this blended DNA profile:
{{
  "platform": "<best platform>",
  "num_agents": <integer>,
  "num_steps": <integer>,
  "seed_content": "<content matching the scenario>",
  "agent_groups": [{{ "name": "<name>", "ratio": <0-1>, "stance_range": [<min>, <max>] }}],
  "event_injections": [{{ "round": <int>, "content": "<event>" }}],
  "available_actions": ["CREATE_POST", "COMMENT", "LIKE", "REPOST", "FOLLOW"],
  "description": "<scenario description>"
}}

Return ONLY valid JSON."""


class DNAMixer:
    def __init__(self, llm_call: Optional[Callable[[str], Awaitable[str]]] = None):
        self._llm_call = llm_call

    def blend(self, dna_a: ScenarioDNA, dna_b: ScenarioDNA, weight_a: float = 0.5) -> ScenarioDNA:
        weight_b = 1.0 - weight_a
        platforms = list(set(dna_a.platform_fit + dna_b.platform_fit))

        dynamics_options = [dna_a.temporal_dynamics, dna_b.temporal_dynamics]
        temporal = dynamics_options[0] if weight_a >= 0.5 else dynamics_options[1]

        return ScenarioDNA(
            conflict_level=round(dna_a.conflict_level * weight_a + dna_b.conflict_level * weight_b, 3),
            information_density=round(dna_a.information_density * weight_a + dna_b.information_density * weight_b, 3),
            viral_potential=round(dna_a.viral_potential * weight_a + dna_b.viral_potential * weight_b, 3),
            sentiment_polarity=round(dna_a.sentiment_polarity * weight_a + dna_b.sentiment_polarity * weight_b, 3),
            temporal_dynamics=temporal,
            agent_diversity=round(dna_a.agent_diversity * weight_a + dna_b.agent_diversity * weight_b, 3),
            platform_fit=platforms,
        )

    async def mix_to_config(self, dna_a: ScenarioDNA, dna_b: ScenarioDNA, weight_a: float = 0.5) -> ScenarioConfig:
        if not self._llm_call:
            raise RuntimeError("LLM call required for mix_to_config")

        blended = self.blend(dna_a, dna_b, weight_a)
        weight_b = 1.0 - weight_a

        prompt = MIX_PROMPT.format(
            weight_a=weight_a, weight_b=weight_b,
            dna_a=dna_a.model_dump_json(indent=2),
            dna_b=dna_b.model_dump_json(indent=2),
            blended=blended.model_dump_json(indent=2),
        )

        raw = await self._llm_call(prompt)
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        data = json.loads(text)
        from engine.composer.schema import AgentGroup, EventInjection

        config = ScenarioConfig(
            platform=data.get("platform", blended.platform_fit[0] if blended.platform_fit else "twitter"),
            num_agents=data.get("num_agents", 50),
            num_steps=data.get("num_steps", 10),
            seed_content=data.get("seed_content", ""),
            agent_groups=[AgentGroup(**g) for g in data.get("agent_groups", [])],
            event_injections=[EventInjection(**e) for e in data.get("event_injections", [])],
            available_actions=data.get("available_actions", ["CREATE_POST", "COMMENT", "LIKE", "REPOST", "FOLLOW"]),
            dna=blended,
            description=data.get("description", ""),
        )
        return config
