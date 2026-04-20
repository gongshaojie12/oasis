# engine/genome/breeder.py
from __future__ import annotations

import random
from typing import Optional

import numpy as np

from .schema import GenomeData, BreedStrategy


_FLOAT_FIELDS = [
    ("traits", ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]),
    ("social_behavior", ["activity_level", "content_creation_ratio", "influence_weight", "echo_chamber_tendency"]),
    ("opinion_spectrum", ["persuadability", "stance_volatility"]),
    ("behavioral_patterns", ["emoji_usage", "hashtag_usage"]),
]


def _get_float_vector(genome: GenomeData) -> list[float]:
    values: list[float] = []
    for section, fields in _FLOAT_FIELDS:
        obj = getattr(genome, section)
        for f in fields:
            values.append(getattr(obj, f))
    return values


def _set_float_vector(genome: GenomeData, values: list[float]) -> None:
    idx = 0
    for section, fields in _FLOAT_FIELDS:
        obj = getattr(genome, section)
        for f in fields:
            clamped = max(0.0, min(1.0, values[idx]))
            setattr(obj, f, round(clamped, 4))
            idx += 1


class GenomeBreeder:
    def __init__(
        self,
        seeds: list[GenomeData],
        target_count: int,
        mutation_rate: float = 0.15,
        strategy: BreedStrategy = BreedStrategy.CROSSOVER,
        rng_seed: Optional[int] = 42,
    ):
        self._seeds = seeds
        self._target_count = target_count
        self._mutation_rate = mutation_rate
        self._strategy = strategy
        self._rng = random.Random(rng_seed)
        self._np_rng = np.random.default_rng(rng_seed)

    def breed(self) -> list[GenomeData]:
        if self._strategy == BreedStrategy.CLONE_MUTATE:
            return self._clone_mutate()
        elif self._strategy == BreedStrategy.CROSSOVER:
            return self._crossover()
        else:
            return self._distribution()

    def _clone_mutate(self) -> list[GenomeData]:
        result: list[GenomeData] = []
        for i in range(self._target_count):
            parent = self._seeds[i % len(self._seeds)]
            child = parent.model_copy(deep=True)
            vec = _get_float_vector(child)
            mutated = [
                v + self._np_rng.normal(0, self._mutation_rate) if self._rng.random() < 0.7 else v
                for v in vec
            ]
            _set_float_vector(child, mutated)
            self._mutate_non_float(child, parent)
            result.append(child)
        return result

    def _crossover(self) -> list[GenomeData]:
        result: list[GenomeData] = []
        for _ in range(self._target_count):
            p1, p2 = self._rng.choices(self._seeds, k=2)
            child = p1.model_copy(deep=True)
            v1 = _get_float_vector(p1)
            v2 = _get_float_vector(p2)
            alpha = self._np_rng.uniform(0.3, 0.7, size=len(v1))
            merged = [a * x + (1 - a) * y for a, x, y in zip(alpha, v1, v2)]
            noise = [self._np_rng.normal(0, self._mutation_rate * 0.5) for _ in merged]
            final = [m + n for m, n in zip(merged, noise)]
            _set_float_vector(child, final)
            self._crossover_non_float(child, p1, p2)
            result.append(child)
        return result

    def _distribution(self) -> list[GenomeData]:
        vectors = np.array([_get_float_vector(s) for s in self._seeds])
        mean = vectors.mean(axis=0)
        std = vectors.std(axis=0) + 1e-6
        result: list[GenomeData] = []
        for _ in range(self._target_count):
            template = self._rng.choice(self._seeds)
            child = template.model_copy(deep=True)
            sampled = self._np_rng.normal(mean, std)
            _set_float_vector(child, sampled.tolist())
            self._mutate_non_float(child, template)
            result.append(child)
        return result

    def _mutate_non_float(self, child: GenomeData, parent: GenomeData) -> None:
        if parent.demographics.interests and self._rng.random() < self._mutation_rate:
            pool = list(parent.demographics.interests)
            keep = max(1, len(pool) - 1)
            child.demographics.interests = self._rng.sample(pool, min(keep, len(pool)))

        if parent.demographics.age_range and self._rng.random() < self._mutation_rate:
            lo, hi = parent.demographics.age_range
            shift = self._rng.randint(-5, 5)
            child.demographics.age_range = [max(13, lo + shift), max(14, hi + shift)]

    def _crossover_non_float(self, child: GenomeData, p1: GenomeData, p2: GenomeData) -> None:
        all_interests = list(set(p1.demographics.interests + p2.demographics.interests))
        if all_interests:
            k = max(1, len(all_interests) // 2)
            child.demographics.interests = self._rng.sample(all_interests, min(k, len(all_interests)))
        child.demographics.mbti = self._rng.choice([p1.demographics.mbti, p2.demographics.mbti])
        child.demographics.profession = self._rng.choice([p1.demographics.profession, p2.demographics.profession])

    def compute_diversity(self, genomes: list[GenomeData]) -> float:
        if len(genomes) < 2:
            return 0.0
        vectors = np.array([_get_float_vector(g) for g in genomes])
        return float(vectors.std(axis=0).mean())
