# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import pytest

from wanxiang.simulation.scenario import DecisionKind, ScenarioConfig


def test_scenario_basic_fields():
    s = ScenarioConfig(
        material="新品「轻气泡」无糖气泡水，青提口味，定价 ¥6/瓶。",
        question="你会购买吗？给出 0-10 的购买意愿评分。",
        decision_kind=DecisionKind.RATE,
    )
    assert "轻气泡" in s.material
    assert s.decision_kind is DecisionKind.RATE


def test_scenario_choose_kind_requires_options():
    s = ScenarioConfig(
        material="三种口味：青提 / 白桃 / 海盐荔枝。",
        question="你最想买哪种？",
        decision_kind=DecisionKind.CHOOSE,
        options=("青提", "白桃", "海盐荔枝"),
    )
    assert s.options == ("青提", "白桃", "海盐荔枝")


def test_choose_without_options_raises():
    with pytest.raises(ValueError, match="CHOOSE.*options"):
        ScenarioConfig(
            material="材料", question="选一个", decision_kind=DecisionKind.CHOOSE)


def test_non_choose_kinds_allow_no_options():
    for kind in [DecisionKind.RATE, DecisionKind.SENTIMENT,
                 DecisionKind.CLICK_PROBABILITY, DecisionKind.WTP]:
        s = ScenarioConfig(material="m", question="q", decision_kind=kind)
        assert s.options is None


def test_scenario_render_user_message_includes_material_and_question():
    s = ScenarioConfig(material="材料X", question="问题Y",
                       decision_kind=DecisionKind.RATE)
    msg = s.render_user_message()
    assert "材料X" in msg and "问题Y" in msg
    assert "score" in msg.lower() or "评分" in msg


def test_scenario_choose_render_includes_options_and_option_key():
    s = ScenarioConfig(
        material="m", question="q", decision_kind=DecisionKind.CHOOSE,
        options=("A", "B", "C"))
    msg = s.render_user_message()
    assert "A" in msg and "B" in msg and "C" in msg
    assert "option" in msg.lower() or "选项" in msg
