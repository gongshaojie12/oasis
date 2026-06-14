# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: Persona.render_system_prompt(locale=...) 双语 (zh/en)."""
from __future__ import annotations

from wanxiang.personas.persona import Persona


def _persona():
    return Persona(
        agent_id=0, name="agent#0",
        demographic={"城市": "北京", "性别": "女", "年龄段": "20-24",
                      "月收入区间": "8000-12000"},
        personality={"价格敏感度": 0.4, "尝鲜意愿": 0.7},
        media={"小红书": 0.8, "抖音": 0.6},
    )


def test_default_locale_renders_chinese_prompt():
    p = _persona()
    out = p.render_system_prompt()
    assert "agent#0" in out
    assert "【人口特征】" in out
    assert "城市" in out
    assert "北京" in out
    # No English headings in zh
    assert "[Demographics]" not in out


def test_explicit_zh_locale_renders_chinese_prompt():
    p = _persona()
    out = p.render_system_prompt(locale="zh")
    assert "【人口特征】" in out
    assert "城市" in out


def test_en_locale_renders_english_headings_and_translated_labels():
    p = _persona()
    out = p.render_system_prompt(locale="en")
    assert "agent#0" in out
    assert "[Demographics]" in out
    assert "[Personality]" in out
    assert "[Media Habits]" in out
    # trait label translated
    assert "city" in out
    assert "gender" in out
    # P5 note: this Persona is constructed in zh manually (not via the
    # locale-aware builder), so its stored values stay Chinese — the en
    # prompt walks the stored data as-is.
    assert "北京" in out
    # zh sectional bracket should not appear in en
    assert "【人口特征】" not in out


def test_untranslated_trait_keys_fall_back_to_original_zh():
    """For keys not present in the i18n dict, render the original key verbatim."""
    p = Persona(
        agent_id=1, name="agent#1",
        demographic={"城市": "上海", "某未翻译键": "X"},
        personality={}, media={},
    )
    out = p.render_system_prompt(locale="en")
    assert "city" in out  # known key translated
    assert "某未翻译键" in out  # unknown key kept verbatim
    assert "X" in out


def test_legacy_callers_without_locale_argument_get_zh():
    """Backward compat: existing call sites use no kwarg → zh."""
    p = _persona()
    legacy = p.render_system_prompt()
    explicit_zh = p.render_system_prompt(locale="zh")
    assert legacy == explicit_zh


def test_both_locales_produce_non_empty_strings():
    p = _persona()
    zh = p.render_system_prompt(locale="zh")
    en = p.render_system_prompt(locale="en")
    assert isinstance(zh, str) and len(zh) > 0
    assert isinstance(en, str) and len(en) > 0
    # They should be different
    assert zh != en


def test_render_is_deterministic_across_locale_flips():
    p = _persona()
    a1 = p.render_system_prompt(locale="zh")
    b1 = p.render_system_prompt(locale="en")
    a2 = p.render_system_prompt(locale="zh")
    b2 = p.render_system_prompt(locale="en")
    assert a1 == a2
    assert b1 == b2
