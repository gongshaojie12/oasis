# engine/tests/test_genome_extractor.py
import json
import pytest
from unittest.mock import AsyncMock, patch
from engine.genome.schema import GenomeData, SourceType
from engine.genome.extractor import GenomeExtractor


MOCK_LLM_RESPONSE = json.dumps({
    "traits": {"openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.7, "agreeableness": 0.5, "neuroticism": 0.3},
    "social_behavior": {"activity_level": 0.9, "content_creation_ratio": 0.7, "interaction_preference": "reply_heavy", "influence_weight": 0.8, "echo_chamber_tendency": 0.3},
    "opinion_spectrum": {"topic_stances": {"AI": 0.9}, "persuadability": 0.3, "stance_volatility": 0.2},
    "demographics": {"age_range": [25, 35], "profession": "engineer", "interests": ["tech", "gaming"], "mbti": "INTJ"},
    "behavioral_patterns": {"peak_activity_hours": [9, 20], "avg_post_length": "long", "emoji_usage": 0.2, "hashtag_usage": 0.4},
})


@pytest.mark.asyncio
async def test_extract_from_text():
    mock_llm = AsyncMock(return_value=MOCK_LLM_RESPONSE)
    extractor = GenomeExtractor(llm_call=mock_llm)
    genome = await extractor.extract_from_text("这是一个科技爱好者，喜欢发长文讨论AI技术")
    assert isinstance(genome, GenomeData)
    assert genome.traits.openness == 0.8
    assert genome.demographics.profession == "engineer"


@pytest.mark.asyncio
async def test_extract_from_csv_row():
    extractor = GenomeExtractor(llm_call=AsyncMock(return_value=MOCK_LLM_RESPONSE))
    row = {"name": "张三", "age": 30, "interests": "科技,游戏", "personality": "内向理性"}
    genome = await extractor.extract_from_structured(row)
    assert isinstance(genome, GenomeData)


@pytest.mark.asyncio
async def test_extract_handles_malformed_llm_output():
    mock_llm = AsyncMock(return_value="not valid json")
    extractor = GenomeExtractor(llm_call=mock_llm)
    genome = await extractor.extract_from_text("some text")
    assert isinstance(genome, GenomeData)
    assert genome.traits.openness == 0.5  # default fallback
