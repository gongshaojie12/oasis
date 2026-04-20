from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class AgentGroup(BaseModel):
    name: str
    ratio: float = Field(ge=0.0, le=1.0)
    stance_range: list[float] = Field(default_factory=lambda: [0.0, 0.0])


class EventInjection(BaseModel):
    round: int = Field(ge=1)
    content: str


class ScenarioDNA(BaseModel):
    conflict_level: float = Field(default=0.5, ge=0.0, le=1.0)
    information_density: float = Field(default=0.5, ge=0.0, le=1.0)
    viral_potential: float = Field(default=0.5, ge=0.0, le=1.0)
    sentiment_polarity: float = Field(default=0.5, ge=0.0, le=1.0)
    temporal_dynamics: str = Field(default="stable")
    agent_diversity: float = Field(default=0.5, ge=0.0, le=1.0)
    platform_fit: list[str] = Field(default_factory=lambda: ["twitter"])


class ScenarioConfig(BaseModel):
    platform: str = "twitter"
    num_agents: int = Field(default=50, ge=1, le=100000)
    num_steps: int = Field(default=10, ge=1, le=1000)
    seed_content: str = ""
    agent_groups: list[AgentGroup] = Field(default_factory=list)
    event_injections: list[EventInjection] = Field(default_factory=list)
    available_actions: list[str] = Field(default_factory=lambda: ["CREATE_POST", "COMMENT", "LIKE", "REPOST", "FOLLOW"])
    dna: Optional[ScenarioDNA] = None
    description: str = ""


class ResourceEstimate(BaseModel):
    llm_calls: int = 0
    estimated_tokens: int = 0
    estimated_minutes: float = 0.0
    estimated_cost_usd: float = 0.0
