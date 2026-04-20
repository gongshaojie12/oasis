# engine/tests/test_genome_breeder.py
import pytest
from engine.genome.schema import GenomeData, BigFiveTraits, BreedStrategy
from engine.genome.breeder import GenomeBreeder


def _make_seed(openness: float = 0.8) -> GenomeData:
    return GenomeData(traits=BigFiveTraits(openness=openness, extraversion=0.6))


def test_clone_mutate_preserves_count():
    seeds = [_make_seed()]
    breeder = GenomeBreeder(seeds=seeds, target_count=10, mutation_rate=0.1, strategy=BreedStrategy.CLONE_MUTATE)
    result = breeder.breed()
    assert len(result) == 10


def test_clone_mutate_introduces_variation():
    seeds = [_make_seed()]
    breeder = GenomeBreeder(seeds=seeds, target_count=50, mutation_rate=0.3, strategy=BreedStrategy.CLONE_MUTATE)
    result = breeder.breed()
    openness_values = [g.traits.openness for g in result]
    assert len(set(round(v, 4) for v in openness_values)) > 1


def test_crossover_requires_two_seeds():
    seeds = [_make_seed(0.8), _make_seed(0.2)]
    breeder = GenomeBreeder(seeds=seeds, target_count=20, mutation_rate=0.1, strategy=BreedStrategy.CROSSOVER)
    result = breeder.breed()
    assert len(result) == 20


def test_distribution_sampling():
    seeds = [_make_seed(0.3), _make_seed(0.7), _make_seed(0.5)]
    breeder = GenomeBreeder(seeds=seeds, target_count=100, mutation_rate=0.0, strategy=BreedStrategy.DISTRIBUTION)
    result = breeder.breed()
    assert len(result) == 100
    avg_openness = sum(g.traits.openness for g in result) / len(result)
    assert 0.3 <= avg_openness <= 0.7


def test_values_stay_in_bounds():
    seeds = [GenomeData(traits=BigFiveTraits(openness=0.99, neuroticism=0.01))]
    breeder = GenomeBreeder(seeds=seeds, target_count=200, mutation_rate=0.5, strategy=BreedStrategy.CLONE_MUTATE)
    result = breeder.breed()
    for g in result:
        assert 0.0 <= g.traits.openness <= 1.0
        assert 0.0 <= g.traits.neuroticism <= 1.0


def test_diversity_check():
    seeds = [_make_seed()]
    breeder = GenomeBreeder(seeds=seeds, target_count=50, mutation_rate=0.2, strategy=BreedStrategy.CLONE_MUTATE)
    diversity = breeder.compute_diversity(breeder.breed())
    assert diversity > 0.0
