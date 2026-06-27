# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""自然语言 → SimulateRequest 意图解析。

调用方传入一个 ModelCall stub/真实 LLM 调用；本函数：
1) 构造抽取式 system prompt
2) 调用模型获取严格 JSON
3) 校验/组装为 SimulateRequest 或返回 missing 字段列表
4) 任何失败都装入 IntentParseResult 不抛
"""
from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel

from wanxiang.api.schemas import (ModelConfig, ScenarioPayload,
                                    SimulateRequest)
from wanxiang.simulation.decision import ModelCall

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$",
                            re.IGNORECASE | re.MULTILINE)


_SYSTEM_PROMPT_ZH = """你是「万象 WANXIANG」的 AI 首席模拟官。
你的工作是把用户的自然语言研究需求映射为结构化模拟参数。

支持的决策类型 (kind)：
- rate: 0-10 评分（购买意愿、满意度等）
- choose: 多选一（口味/包装/方案对比）
- click_probability: 0-1 点击概率
- sentiment: -1~+1 情感极性
- willingness_to_pay: 愿付价格

请只输出严格 JSON，格式：
{
  "intent": "simulate" | "unknown",
  "fields": {
    "material": <投放材料文本>,
    "question": <提问文本>,
    "kind": <上述五种之一>,
    "options": [<choose 时的候选>] 或 null,
    "n": <虚拟人数量整数，默认 50>,
    "rounds": <社交轮数整数，默认 0>
  },
  "missing": [<尚需用户补充的字段名>],
  "explanation": <一句中文人话说明>,
  "confidence": <0-1 的浮点>
}
若用户意图与"模拟人群预测"无关，intent 设为 "unknown"。
不要在 JSON 之外输出任何文字、不要加 markdown 围栏。
"""

_SYSTEM_PROMPT_EN = """You are the AI Chief Simulation Officer of WANXIANG.
Your job is to map the user's natural-language research request into
structured simulation parameters.

Supported decision kinds:
- rate: 0-10 rating (purchase intent, satisfaction, etc.)
- choose: pick one of N options (flavor/packaging/plan comparison)
- click_probability: 0-1 click probability
- sentiment: -1 to +1 sentiment polarity
- willingness_to_pay: willingness-to-pay price

Reply with strict JSON only, in the schema:
{
  "intent": "simulate" | "unknown",
  "fields": {
    "material": <ad/creative copy text>,
    "question": <the question to ask agents>,
    "kind": <one of the five kinds above>,
    "options": [<candidate options for choose>] or null,
    "n": <number of agents, integer, default 50>,
    "rounds": <number of social rounds, integer, default 0>
  },
  "missing": [<field names the user still needs to provide>],
  "explanation": <one short English sentence>,
  "confidence": <float 0-1>
}
If the user's intent is not about simulating a population prediction,
set intent to "unknown".
Do not output any text outside the JSON. Do not add markdown fences.
"""

# Backward-compat alias for any internal/test code still importing it.
_SYSTEM_PROMPT = _SYSTEM_PROMPT_ZH


# 默认画像:指向 DB 内置画像 slug(resolve_distribution 会解析);
# 不再用文件路径,因为内置画像现在以 DB 为唯一真相源。
_BUNDLED_DIST = "cn_national_joint_2020"


class IntentParseResult(BaseModel):
    intent: Literal["simulate", "unknown"]
    request: SimulateRequest | None = None
    missing: list[str] = []
    explanation: str = ""
    confidence: float = 0.0


def _strip_fence(s: str) -> str:
    return _CODE_FENCE_RE.sub("", s).strip()


async def parse_intent(
    user_text: str,
    model_call: ModelCall,
    default_distribution_path: str | None = None,
    *,
    locale: str = "zh",
) -> IntentParseResult:
    distro = default_distribution_path or _BUNDLED_DIST
    sys_prompt = _SYSTEM_PROMPT_EN if locale == "en" else _SYSTEM_PROMPT_ZH

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_text},
    ]
    try:
        raw = await model_call(messages)
    except Exception as e:  # noqa: BLE001
        return IntentParseResult(intent="unknown", request=None,
                                  missing=[],
                                  explanation=f"模型调用失败：{e}",
                                  confidence=0.0)

    try:
        data = json.loads(_strip_fence(raw))
    except (ValueError, json.JSONDecodeError) as e:
        return IntentParseResult(
            intent="unknown", request=None, missing=[],
            explanation=f"无法解析模型 JSON 输出：{e}",
            confidence=0.0)

    intent = data.get("intent", "unknown")
    explanation = data.get("explanation", "")
    confidence = float(data.get("confidence", 0.0))
    missing: list[str] = list(data.get("missing") or [])
    fields = data.get("fields") or {}

    if intent != "simulate":
        return IntentParseResult(intent="unknown", request=None,
                                  missing=missing,
                                  explanation=explanation,
                                  confidence=confidence)

    # 尝试组装 SimulateRequest；任何缺/非法都进 missing，request=None
    f_missing: list[str] = []
    kind = fields.get("kind")
    material = (fields.get("material") or "").strip()
    question = (fields.get("question") or "").strip()
    options = fields.get("options")
    n = fields.get("n")
    rounds = fields.get("rounds") if fields.get("rounds") is not None else 0

    if not material:
        f_missing.append("material")
    if not question:
        f_missing.append("question")
    if kind not in {"rate", "choose", "click_probability", "sentiment",
                    "willingness_to_pay"}:
        f_missing.append("kind")
    if kind == "choose" and not options:
        f_missing.append("options")
    if n is None or not isinstance(n, (int, float)) or n <= 0:
        f_missing.append("n")
    else:
        n = int(n)

    all_missing = list(dict.fromkeys(missing + f_missing))  # 合并去重

    if all_missing:
        return IntentParseResult(intent="simulate", request=None,
                                  missing=all_missing,
                                  explanation=explanation,
                                  confidence=confidence)

    try:
        req = SimulateRequest(
            distribution_path=distro,
            n=n,
            seed=42,
            scenario=ScenarioPayload(
                material=material, question=question, kind=kind,
                options=list(options) if options else None),
            rounds=int(rounds) if rounds is not None else 0,
            model=ModelConfig(provider="stub"),
        )
    except Exception as e:  # noqa: BLE001
        return IntentParseResult(
            intent="simulate", request=None, missing=all_missing or ["unknown"],
            explanation=f"组装 SimulateRequest 失败：{e}",
            confidence=confidence)

    return IntentParseResult(intent="simulate", request=req, missing=[],
                              explanation=explanation,
                              confidence=confidence)
