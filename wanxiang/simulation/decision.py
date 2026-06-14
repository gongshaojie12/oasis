# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""DecisionRunner: persona + scenario → 调模型 → 解析 → DecisionResult。

输入侧：不依赖具体 LLM SDK，只要求一个 `async (messages) -> str` 的可
调用。真实用 camel 时由调用方做一层薄适配。
输出侧：DecisionResult 永远返回，错误装入 error 字段——不抛异常打断
M1-3 的批量并发。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from wanxiang.media.environment import render_feed_prompt, select_feed
from wanxiang.personas.persona import Persona
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig

ModelCall = Callable[[list[dict]], Awaitable[str]]

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class DecisionResult:
    agent_id: int
    kind: DecisionKind
    value: Any
    raw: str
    error: str | None = None


_FIELD_FOR_KIND = {
    DecisionKind.RATE: "score",
    DecisionKind.CHOOSE: "option",
    DecisionKind.CLICK_PROBABILITY: "probability",
    DecisionKind.SENTIMENT: "polarity",
    DecisionKind.WTP: "price",
}


class DecisionRunner:

    async def run(
        self,
        persona: Persona,
        scenario: ScenarioConfig,
        model_call: ModelCall,
    ) -> DecisionResult:
        # M4: 动态信息流前置注入（feed → persona → scenario）
        system_text = persona.render_system_prompt()
        if scenario.media_pool and scenario.feed_k > 0:
            feed = select_feed(persona, scenario.media_pool, scenario.feed_k)
            feed_prefix = render_feed_prompt(feed)
            if feed_prefix:
                system_text = feed_prefix + "\n" + system_text
        messages = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": scenario.render_user_message()},
        ]
        try:
            raw = await model_call(messages)
        except Exception as e:  # noqa: BLE001
            return DecisionResult(
                agent_id=persona.agent_id, kind=scenario.decision_kind,
                value=None, raw="", error=f"model call failed: {e}")

        stripped = _CODE_FENCE_RE.sub("", raw).strip()
        try:
            data = json.loads(stripped)
        except (json.JSONDecodeError, ValueError) as e:
            return DecisionResult(
                agent_id=persona.agent_id, kind=scenario.decision_kind,
                value=None, raw=raw, error=f"invalid json: {e}")

        field = _FIELD_FOR_KIND[scenario.decision_kind]
        if not isinstance(data, dict) or field not in data:
            return DecisionResult(
                agent_id=persona.agent_id, kind=scenario.decision_kind,
                value=None, raw=raw,
                error=f"missing required field {field!r} in model output")

        value = data[field]
        if scenario.decision_kind is DecisionKind.CHOOSE:
            if value not in (scenario.options or ()):
                return DecisionResult(
                    agent_id=persona.agent_id, kind=scenario.decision_kind,
                    value=None, raw=raw,
                    error=(f"choice {value!r} not in declared options "
                           f"{scenario.options}"))

        return DecisionResult(
            agent_id=persona.agent_id, kind=scenario.decision_kind,
            value=value, raw=raw, error=None)
