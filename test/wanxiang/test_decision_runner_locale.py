# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: ScenarioConfig.locale + DecisionRunner localizes user message instructions."""
from __future__ import annotations

import asyncio

from wanxiang.personas.persona import Persona
from wanxiang.simulation.decision import DecisionRunner
from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def _persona():
    return Persona(agent_id=0, name="agent",
                   demographic={"城市": "北京"}, personality={}, media={})


def _make_call():
    captured = {"messages": None}

    async def call(messages):
        captured["messages"] = messages
        return '{"score": 5}'

    return call, captured


def test_scenario_locale_defaults_to_zh():
    s = ScenarioConfig(material="m", question="q",
                       decision_kind=DecisionKind.RATE)
    assert s.locale == "zh"


def test_scenario_accepts_en_locale():
    s = ScenarioConfig(material="m", question="q",
                       decision_kind=DecisionKind.RATE, locale="en")
    assert s.locale == "en"


def test_decision_runner_zh_user_message_has_chinese_instruction():
    call, captured = _make_call()
    s = ScenarioConfig(material="m", question="q",
                       decision_kind=DecisionKind.RATE, locale="zh")
    asyncio.run(DecisionRunner().run(_persona(), s, call))
    user_msg = captured["messages"][1]["content"]
    assert "材料" in user_msg or "问题" in user_msg
    # zh instructional verbs / keywords
    assert "评分" in user_msg or "JSON" in user_msg
    # No English verbs leaked into zh prompt instruction
    assert "Please" not in user_msg


def test_decision_runner_en_user_message_has_english_instruction():
    call, captured = _make_call()
    s = ScenarioConfig(material="m", question="q",
                       decision_kind=DecisionKind.RATE, locale="en")
    asyncio.run(DecisionRunner().run(_persona(), s, call))
    user_msg = captured["messages"][1]["content"]
    # English-only labels
    assert "Material" in user_msg or "Question" in user_msg
    assert "JSON" in user_msg
    # Should not contain Chinese instructional brackets
    assert "【材料】" not in user_msg
    assert "【问题】" not in user_msg


def test_decision_runner_en_persona_system_prompt_is_english():
    call, captured = _make_call()
    s = ScenarioConfig(material="m", question="q",
                       decision_kind=DecisionKind.RATE, locale="en")
    asyncio.run(DecisionRunner().run(_persona(), s, call))
    sys_msg = captured["messages"][0]["content"]
    assert "[Demographics]" in sys_msg
    assert "【人口特征】" not in sys_msg


def test_all_decision_kinds_have_en_instruction_no_raw_zh_leak():
    """Each DecisionKind must produce an EN user prompt free of zh chars."""
    import re
    has_cjk = re.compile(r"[一-鿿]")

    cases = [
        (DecisionKind.RATE, None),
        (DecisionKind.CHOOSE, ("apple", "pear")),
        (DecisionKind.CLICK_PROBABILITY, None),
        (DecisionKind.SENTIMENT, None),
        (DecisionKind.WTP, None),
    ]
    for kind, options in cases:
        s = ScenarioConfig(material="Ad", question="Would you buy?",
                           decision_kind=kind, options=options,
                           locale="en")
        msg = s.render_user_message()
        # Material/Question text user supplies is in English here; instruction
        # text appended by ScenarioConfig must contain no Chinese.
        assert not has_cjk.search(msg), \
            f"EN render for {kind} contains zh chars: {msg!r}"
