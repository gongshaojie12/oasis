# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from collections import Counter

import pytest

from wanxiang.personas.builder import PersonaBuilder
from wanxiang.personas.persona import Persona


# ---- 单个 build ----

def test_build_single_persona_from_spec():
    pb = PersonaBuilder()
    p = pb.build(
        agent_id=42,
        name="小K",
        demographic={"年龄": 22, "城市": "北京"},
        personality={"尝鲜意愿": 0.8},
        media={"小红书": 0.6},
    )
    assert isinstance(p, Persona)
    assert p.agent_id == 42
    assert p.name == "小K"
    assert p.demographic["城市"] == "北京"


# ---- 批量 sample ----

SIMPLE_DIST = {
    "demographic": {
        "性别": [("男", 0.5), ("女", 0.5)],
        "城市": [("北京", 0.4), ("上海", 0.6)],
    },
    "personality": {
        "价格敏感度": [(0.2, 0.3), (0.5, 0.4), (0.8, 0.3)],
    },
    "media": {
        "小红书": [(0.0, 0.5), (0.7, 0.5)],
    },
}


def test_sample_returns_n_personas():
    pb = PersonaBuilder()
    ps = pb.sample(SIMPLE_DIST, n=20, seed=123)
    assert len(ps) == 20
    assert all(isinstance(p, Persona) for p in ps)


def test_sample_assigns_unique_sequential_ids_starting_from_zero():
    pb = PersonaBuilder()
    ps = pb.sample(SIMPLE_DIST, n=5, seed=7)
    ids = [p.agent_id for p in ps]
    assert ids == [0, 1, 2, 3, 4]


def test_sample_is_deterministic_with_same_seed():
    pb = PersonaBuilder()
    a = pb.sample(SIMPLE_DIST, n=50, seed=2026)
    b = pb.sample(SIMPLE_DIST, n=50, seed=2026)
    assert [p.demographic for p in a] == [p.demographic for p in b]
    assert [p.personality for p in a] == [p.personality for p in b]
    assert [p.media for p in a] == [p.media for p in b]


def test_sample_different_seeds_produce_different_results():
    pb = PersonaBuilder()
    a = pb.sample(SIMPLE_DIST, n=50, seed=1)
    b = pb.sample(SIMPLE_DIST, n=50, seed=2)
    assert [p.demographic for p in a] != [p.demographic for p in b]


def test_sample_distribution_approximates_weights():
    """20000 次抽样后，城市'上海'的占比应接近 0.6（±0.03）。"""
    pb = PersonaBuilder()
    ps = pb.sample(SIMPLE_DIST, n=20000, seed=999)
    counter = Counter(p.demographic["城市"] for p in ps)
    shanghai_ratio = counter["上海"] / 20000
    assert 0.57 <= shanghai_ratio <= 0.63, (
        f"shanghai_ratio={shanghai_ratio} 不在 0.6±0.03 范围内")


def test_sample_default_name_template():
    pb = PersonaBuilder()
    ps = pb.sample(SIMPLE_DIST, n=3, seed=1)
    assert all(str(p.agent_id) in p.name for p in ps), [p.name for p in ps]


def test_sample_with_name_prefix():
    pb = PersonaBuilder()
    ps = pb.sample(SIMPLE_DIST, n=3, seed=1, name_prefix="测试")
    for p in ps:
        assert p.name.startswith("测试")
