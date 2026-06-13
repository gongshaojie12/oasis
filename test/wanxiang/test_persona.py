# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import pytest

from wanxiang.personas.persona import Persona


def make_basic(**overrides):
    base = dict(
        agent_id=0,
        name="小张",
        demographic={"年龄": 25, "性别": "男", "城市": "上海", "月收入": 12000},
        personality={"价格敏感度": 0.4, "尝鲜意愿": 0.7, "健康意识": 0.6},
        media={"小红书": 0.5, "抖音": 0.8, "微信": 0.9},
    )
    base.update(overrides)
    return Persona(**base)


def test_persona_is_frozen():
    p = make_basic()
    with pytest.raises(Exception):  # FrozenInstanceError
        p.name = "改了"  # type: ignore


def test_persona_trait_count_exposes_total_dimensions():
    p = make_basic()
    # 4 人口 + 3 个性 + 3 媒体 = 10
    assert p.trait_count() == 10


def test_render_system_prompt_includes_name_and_key_traits():
    p = make_basic()
    prompt = p.render_system_prompt()
    assert "小张" in prompt
    assert "25" in prompt
    assert "上海" in prompt
    assert "价格敏感度" in prompt
    assert "小红书" in prompt


def test_render_system_prompt_returns_str():
    p = make_basic()
    assert isinstance(p.render_system_prompt(), str)


def test_empty_trait_groups_render_safely():
    p = Persona(agent_id=1, name="阿哲",
                demographic={}, personality={}, media={})
    out = p.render_system_prompt()
    assert "阿哲" in out
    assert isinstance(out, str) and len(out) > 0


def test_persona_equality_by_value():
    a = make_basic()
    b = make_basic()
    assert a == b
    c = make_basic(name="不同")
    assert a != c
