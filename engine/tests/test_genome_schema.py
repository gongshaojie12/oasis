# engine/tests/test_genome_schema.py
from engine.genome.schema import GenomeData, BigFiveTraits, BreedStrategy, SourceType


def test_genome_data_defaults():
    g = GenomeData()
    assert g.traits.openness == 0.5
    assert g.social_behavior.activity_level == 0.5
    assert g.demographics.profession == "general"


def test_genome_data_custom():
    g = GenomeData(
        traits=BigFiveTraits(openness=0.9, extraversion=0.2),
        demographics={"age_range": [18, 25], "profession": "student", "interests": ["gaming"]},
    )
    assert g.traits.openness == 0.9
    assert g.demographics.profession == "student"


def test_genome_data_serialization():
    g = GenomeData()
    d = g.model_dump()
    assert "traits" in d
    assert "social_behavior" in d
    restored = GenomeData.model_validate(d)
    assert restored.traits.openness == g.traits.openness


def test_source_type_values():
    assert SourceType.DOCUMENT.value == "document"
    assert SourceType.NATURAL_LANGUAGE.value == "natural_language"


def test_breed_strategy_values():
    assert BreedStrategy.CROSSOVER.value == "crossover"
