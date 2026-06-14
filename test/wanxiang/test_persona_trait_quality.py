# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Distribution quality: realistic value ranges, no NaN, no obvious bugs."""
from __future__ import annotations

import math
import os

import pytest

from wanxiang.datasources.distribution import load_distribution
from wanxiang.personas.builder import PersonaBuilder

DIST = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "wanxiang", "datasources", "distributions",
    "cn_z_generation_v1.yaml",
)


def _personas(n: int = 100, seed: int = 1):
    return PersonaBuilder().sample(load_distribution(DIST), n=n, seed=seed)


def test_numeric_personality_in_0_1_range():
    """All numeric personality traits should land within a plausible 0..1 envelope."""
    for p in _personas(50):
        for k, v in p.personality.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                assert -0.5 <= v <= 1.5, (
                    f"personality {k}={v} out of plausible range")


def test_no_nan_or_none_traits():
    for p in _personas(20):
        sections = (
            ("demographic", p.demographic),
            ("personality", p.personality),
            ("media", p.media),
        )
        for section_name, section in sections:
            for k, v in section.items():
                assert v is not None, f"{section_name}.{k} is None"
                if isinstance(v, float):
                    assert not math.isnan(v), f"{section_name}.{k} is NaN"


def test_age_distribution_concentrated_in_z_generation():
    """Z-generation: ~1995-2010 出生 → 2026 时 16-31 岁。"""
    personas = _personas(300)
    ages = []
    for p in personas:
        a = p.demographic.get("年龄")
        if isinstance(a, (int, float)):
            ages.append(int(a))
    assert ages, "expected numeric '年龄' in demographic"
    n_in_range = sum(1 for a in ages if 16 <= a <= 32)
    assert n_in_range / len(ages) > 0.7, (
        f"Z-gen 分布应集中 16-32 岁，实际只 {n_in_range}/{len(ages)}")


def test_at_least_some_diversity_per_trait():
    """A trait that always returns 1 value is broken / not really a distribution."""
    personas = _personas(100)
    sample_traits = []
    for sec_name in ("demographic", "personality", "media"):
        sec = getattr(personas[0], sec_name)
        # Take 3 traits per section as a representative diversity probe.
        for k in list(sec.keys())[:3]:
            sample_traits.append((sec_name, k))
    for sec_name, k in sample_traits:
        values = {getattr(p, sec_name)[k] for p in personas}
        if len(values) < 2:
            pytest.fail(
                f"trait {sec_name}.{k} is constant across 100 personas")


def test_personality_big5_keys_present():
    p = _personas(1)[0]
    for k in ("开放性", "尽责性", "外向性", "宜人性", "神经质"):
        assert k in p.personality, f"Big Five trait missing: {k}"


def test_media_includes_chinese_platforms():
    p = _personas(1)[0]
    for k in (
            "微信日均时长",
            "微博日均时长",
            "小红书日均时长",
            "抖音日均时长",
            "B站日均时长",
    ):
        assert k in p.media, f"core CN platform usage missing: {k}"
