# engine/genome/schema.py
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    DOCUMENT = "document"
    URL = "url"
    CSV = "csv"
    MANUAL = "manual"
    NATURAL_LANGUAGE = "natural_language"
    BREED = "breed"


class BigFiveTraits(BaseModel):
    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)


class SocialBehavior(BaseModel):
    activity_level: float = Field(default=0.5, ge=0.0, le=1.0)
    content_creation_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    interaction_preference: str = Field(default="balanced")
    influence_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    echo_chamber_tendency: float = Field(default=0.5, ge=0.0, le=1.0)


class OpinionSpectrum(BaseModel):
    topic_stances: dict[str, float] = Field(default_factory=dict)
    persuadability: float = Field(default=0.5, ge=0.0, le=1.0)
    stance_volatility: float = Field(default=0.5, ge=0.0, le=1.0)


class Demographics(BaseModel):
    age_range: list[int] = Field(default=[20, 40])
    profession: str = Field(default="general")
    interests: list[str] = Field(default_factory=list)
    mbti: Optional[str] = None


class BehavioralPatterns(BaseModel):
    peak_activity_hours: list[int] = Field(default=[9, 12, 20, 22])
    avg_post_length: str = Field(default="medium")
    emoji_usage: float = Field(default=0.3, ge=0.0, le=1.0)
    hashtag_usage: float = Field(default=0.3, ge=0.0, le=1.0)


class GenomeData(BaseModel):
    traits: BigFiveTraits = Field(default_factory=BigFiveTraits)
    social_behavior: SocialBehavior = Field(default_factory=SocialBehavior)
    opinion_spectrum: OpinionSpectrum = Field(default_factory=OpinionSpectrum)
    demographics: Demographics = Field(default_factory=Demographics)
    behavioral_patterns: BehavioralPatterns = Field(
        default_factory=BehavioralPatterns
    )


class BreedStrategy(str, Enum):
    CLONE_MUTATE = "clone_mutate"
    CROSSOVER = "crossover"
    DISTRIBUTION = "distribution"
