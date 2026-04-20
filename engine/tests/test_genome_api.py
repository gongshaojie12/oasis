# engine/tests/test_genome_api.py
import pytest
from httpx import ASGITransport, AsyncClient

from engine.main import app


@pytest.fixture
def internal_key_header():
    return {"X-Internal-Key": "test-key"}


@pytest.mark.asyncio
async def test_extract_genome_endpoint(internal_key_header):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/engine/genomes/extract",
            json={"source_type": "natural_language", "content": "一个热爱科技的年轻人"},
            headers=internal_key_header,
        )
        assert resp.status_code in (200, 202)


@pytest.mark.asyncio
async def test_breed_genome_endpoint(internal_key_header):
    seed = {
        "traits": {"openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.5,
                    "agreeableness": 0.5, "neuroticism": 0.3},
        "social_behavior": {"activity_level": 0.7, "content_creation_ratio": 0.5,
                            "interaction_preference": "balanced", "influence_weight": 0.5,
                            "echo_chamber_tendency": 0.3},
        "opinion_spectrum": {"topic_stances": {}, "persuadability": 0.5, "stance_volatility": 0.3},
        "demographics": {"age_range": [20, 30], "profession": "student", "interests": ["tech"], "mbti": "INTP"},
        "behavioral_patterns": {"peak_activity_hours": [9, 21], "avg_post_length": "medium",
                                "emoji_usage": 0.3, "hashtag_usage": 0.3},
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/engine/genomes/breed",
            json={"seeds": [seed], "target_count": 5, "mutation_rate": 0.15, "strategy": "clone_mutate"},
            headers=internal_key_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["genomes"]) == 5
        assert "diversity" in data
