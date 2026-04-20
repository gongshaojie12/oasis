# engine/genome/extractor.py
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Awaitable, Optional

from .schema import GenomeData

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """你是一个人格分析专家。根据以下文本/数据，分析其中描述的人物特征，并输出一个 JSON 对象。

输出格式要求（所有数值字段范围 0.0-1.0）：
{
  "traits": {
    "openness": <float>, "conscientiousness": <float>, "extraversion": <float>,
    "agreeableness": <float>, "neuroticism": <float>
  },
  "social_behavior": {
    "activity_level": <float>, "content_creation_ratio": <float>,
    "interaction_preference": "<reply_heavy|post_heavy|balanced|lurker>",
    "influence_weight": <float>, "echo_chamber_tendency": <float>
  },
  "opinion_spectrum": {
    "topic_stances": {"<话题>": <-1.0到1.0的立场值>},
    "persuadability": <float>, "stance_volatility": <float>
  },
  "demographics": {
    "age_range": [<int>, <int>], "profession": "<string>",
    "interests": ["<string>"], "mbti": "<string或null>"
  },
  "behavioral_patterns": {
    "peak_activity_hours": [<int>], "avg_post_length": "<short|medium|long>",
    "emoji_usage": <float>, "hashtag_usage": <float>
  }
}

只输出 JSON，不要输出其他内容。

输入内容：
"""

STRUCTURED_PROMPT = """你是一个人格分析专家。根据以下结构化数据，推断此人的完整人格画像。
对于数据中没有的字段，请根据已有信息合理推断。

输出格式同上（JSON）。只输出 JSON。

结构化数据：
"""


class GenomeExtractor:
    def __init__(self, llm_call: Callable[[str], Awaitable[str]]):
        self._llm_call = llm_call

    async def extract_from_text(self, text: str) -> GenomeData:
        prompt = EXTRACTION_PROMPT + text
        return await self._call_and_parse(prompt)

    async def extract_from_structured(self, data: dict[str, Any]) -> GenomeData:
        prompt = STRUCTURED_PROMPT + json.dumps(data, ensure_ascii=False, indent=2)
        return await self._call_and_parse(prompt)

    async def _call_and_parse(self, prompt: str) -> GenomeData:
        try:
            raw = await self._llm_call(prompt)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            parsed = json.loads(cleaned)
            return GenomeData.model_validate(parsed)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse LLM genome output: %s", e)
            return GenomeData()
