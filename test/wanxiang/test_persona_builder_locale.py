# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P5: PersonaBuilder.sample(..., locale=...) localizes trait keys + values."""
from __future__ import annotations

import os

import pytest

from wanxiang.datasources.distribution import load_distribution
from wanxiang.personas.builder import PersonaBuilder

DIST = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..",
    "test", "wanxiang", "fixtures",
    "cn_z_generation_v1.yaml"))


def test_sample_zh_default():
    d = load_distribution(DIST)
    p = PersonaBuilder().sample(d, n=1, seed=42)[0]
    # zh keys + zh values
    assert "城市" in p.demographic
    val = p.demographic["城市"]
    assert isinstance(val, str)


def test_sample_en_keys_and_values():
    d = load_distribution(DIST)
    p_en = PersonaBuilder().sample(d, n=1, seed=42, locale="en")[0]
    assert "city" in p_en.demographic
    val = p_en.demographic["city"]
    # value should be the EN label (Beijing/Shanghai/...) not Chinese
    assert val
    # And ZH should not appear in the en key set
    assert "城市" not in p_en.demographic


def test_sample_deterministic_per_locale_per_seed():
    d = load_distribution(DIST)
    p1 = PersonaBuilder().sample(d, n=3, seed=42, locale="en")
    p2 = PersonaBuilder().sample(d, n=3, seed=42, locale="en")
    for a, b in zip(p1, p2):
        assert a.demographic == b.demographic
        assert a.personality == b.personality
        assert a.media == b.media


def test_sample_total_traits_count_same_across_locales():
    d = load_distribution(DIST)
    p_zh = PersonaBuilder().sample(d, n=1, seed=1)[0]
    p_en = PersonaBuilder().sample(d, n=1, seed=1, locale="en")[0]
    assert len(p_zh.demographic) == len(p_en.demographic)
    assert len(p_zh.personality) == len(p_en.personality)
    assert len(p_zh.media) == len(p_en.media)


def test_persona_locale_field_recorded():
    d = load_distribution(DIST)
    p = PersonaBuilder().sample(d, n=1, seed=1, locale="en")[0]
    # Persona has a locale attribute set
    assert getattr(p, "locale", None) == "en"


def test_persona_render_system_prompt_uses_data_directly():
    """P5 fix: no more Chinese keys leaking into en prompt."""
    d = load_distribution(DIST)
    p = PersonaBuilder().sample(d, n=1, seed=42, locale="en")[0]
    prompt = p.render_system_prompt(locale="en")
    # Should NOT contain Chinese trait labels
    for forbidden in ("城市", "性别", "年龄段"):
        assert forbidden not in prompt, (
            f"untranslated zh label {forbidden} in en prompt")
