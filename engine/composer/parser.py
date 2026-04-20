from __future__ import annotations

import json
import logging
from typing import Callable, Awaitable

from engine.composer.schema import ScenarioConfig, ScenarioDNA, AgentGroup, EventInjection

logger = logging.getLogger("engine.composer.parser")

PARSE_PROMPT = """You are a social media simulation scenario designer. Parse the user's natural language description into a structured simulation configuration.

User description:
{description}

Return a valid JSON object with these fields:
{{
  "platform": "twitter" | "reddit" | "weibo" | "xiaohongshu" | "douyin" | "kuaishou" | "bilibili" | "wechat_video",
  "num_agents": <integer 1-100000>,
  "num_steps": <integer 1-1000>,
  "seed_content": "<initial post content>",
  "agent_groups": [
    {{ "name": "<group name>", "ratio": <0-1>, "stance_range": [<min>, <max>] }}
  ],
  "event_injections": [
    {{ "round": <integer>, "content": "<event description>" }}
  ],
  "available_actions": ["CREATE_POST", "COMMENT", "LIKE", "REPOST", "FOLLOW"],
  "dna": {{
    "conflict_level": <0-1>,
    "information_density": <0-1>,
    "viral_potential": <0-1>,
    "sentiment_polarity": <0-1>,
    "temporal_dynamics": "stable" | "escalation" | "decay" | "wave",
    "agent_diversity": <0-1>,
    "platform_fit": ["<platform>"]
  }},
  "description": "<brief summary of the scenario>"
}}

Rules:
- Infer reasonable defaults if the user doesn't specify everything
- Agent group ratios must sum to 1.0
- Event injection rounds must be within num_steps range
- Return ONLY valid JSON, no markdown or explanation"""


class ScenarioParser:
    def __init__(self, llm_call: Callable[[str], Awaitable[str]]):
        self._llm_call = llm_call

    async def parse(self, description: str) -> ScenarioConfig:
        prompt = PARSE_PROMPT.format(description=description)
        raw = await self._llm_call(prompt)

        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        data = json.loads(text)

        groups = [AgentGroup(**g) for g in data.get("agent_groups", [])]
        events = [EventInjection(**e) for e in data.get("event_injections", [])]
        dna = ScenarioDNA(**data["dna"]) if "dna" in data else None

        return ScenarioConfig(
            platform=data.get("platform", "twitter"),
            num_agents=data.get("num_agents", 50),
            num_steps=data.get("num_steps", 10),
            seed_content=data.get("seed_content", ""),
            agent_groups=groups,
            event_injections=events,
            available_actions=data.get("available_actions", ["CREATE_POST", "COMMENT", "LIKE", "REPOST", "FOLLOW"]),
            dna=dna,
            description=data.get("description", description),
        )
