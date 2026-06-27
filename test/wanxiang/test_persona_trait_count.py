# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""spec §M2: each Persona has 200+ trait dimensions.

Closes 缺口#1 — `cn_z_generation_v1.yaml` 必须覆盖 spec 承诺的 200+ 维特质，
不能停留在最初的 10 维 MVP。
"""
from __future__ import annotations

import os

import pytest

from wanxiang.datasources.distribution import load_distribution
from wanxiang.personas.builder import PersonaBuilder

DIST = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "test", "wanxiang", "fixtures",
    "cn_z_generation_v1.yaml",
)


def _persona(seed: int = 42):
    dist = load_distribution(DIST)
    return PersonaBuilder().sample(dist, n=1, seed=seed)[0]


def test_total_trait_count_exceeds_200():
    p = _persona()
    total = len(p.demographic) + len(p.personality) + len(p.media)
    assert total >= 200, f"got {total} traits, spec promises 200+"


def test_demographic_has_at_least_40():
    assert len(_persona().demographic) >= 40


def test_personality_has_at_least_70():
    assert len(_persona().personality) >= 70


def test_media_has_at_least_70():
    assert len(_persona().media) >= 70


def test_existing_legacy_traits_still_present():
    """Make sure earlier traits (used in templates / downstream) still exist."""
    p = _persona()
    # 原始 10 维 — 不能消失（templates / 报表里可能直接引用）
    for k in ("城市", "性别", "年龄段", "月收入区间"):
        assert k in p.demographic, f"missing legacy demographic key: {k}"
    for k in ("价格敏感度", "尝鲜意愿", "健康意识"):
        assert k in p.personality, f"missing legacy personality key: {k}"
    for k in ("小红书", "抖音", "微信"):
        assert k in p.media, f"missing legacy media key: {k}"


def test_traits_are_deterministic_with_seed():
    dist = load_distribution(DIST)
    p1 = PersonaBuilder().sample(dist, n=3, seed=7)
    p2 = PersonaBuilder().sample(dist, n=3, seed=7)
    for a, b in zip(p1, p2):
        assert a.demographic == b.demographic
        assert a.personality == b.personality
        assert a.media == b.media
