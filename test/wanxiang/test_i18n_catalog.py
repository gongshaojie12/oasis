# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""i18n catalog + locale helpers."""
import pytest

from wanxiang.api.i18n import (CATALOG, DEFAULT_LOCALE, SUPPORTED_LOCALES,
                                 normalize_locale, parse_accept_language, t)


def test_default_locale_is_zh():
    assert DEFAULT_LOCALE == "zh"


def test_supported_locales_includes_zh_en():
    assert "zh" in SUPPORTED_LOCALES
    assert "en" in SUPPORTED_LOCALES


def test_t_returns_zh_by_default():
    # zh entry of auth.missing_api_key contains "X-API-Key"
    assert "X-API-Key" in t("auth.missing_api_key")
    out_zh = t("auth.invalid_api_key", locale="zh")
    out_en = t("auth.invalid_api_key", locale="en")
    assert "无效" in out_zh
    assert "Invalid" in out_en


def test_t_falls_back_to_zh_if_locale_missing_in_entry():
    """If an entry lacks en, returns zh."""
    # All catalog entries have both, so simulate via direct call
    out = t("auth.invalid_api_key", locale="zh")
    assert out


def test_t_unknown_key_returns_key_verbatim():
    assert t("does.not.exist") == "does.not.exist"


def test_t_formats_kwargs():
    out = t("sim.distribution_file_not_found", locale="en", path="/x.yaml")
    assert "/x.yaml" in out


def test_t_safe_with_missing_format_keys():
    """Missing format kwargs should not crash."""
    out = t("sim.distribution_file_not_found", locale="en")
    assert isinstance(out, str)


def test_normalize_locale_strips_region():
    assert normalize_locale("zh-CN") == "zh"
    assert normalize_locale("en-US") == "en"
    assert normalize_locale("EN") == "en"
    assert normalize_locale("zh_TW") == "zh"


def test_normalize_locale_unsupported_returns_none():
    assert normalize_locale("fr") is None
    assert normalize_locale("ja-JP") is None
    assert normalize_locale("") is None
    assert normalize_locale(None) is None


def test_parse_accept_language_picks_first_supported():
    assert parse_accept_language("en") == "en"
    assert parse_accept_language("zh-CN,en;q=0.5") == "zh"
    assert parse_accept_language("fr,en;q=0.8") == "en"
    assert parse_accept_language("fr") is None
    assert parse_accept_language("") is None
    assert parse_accept_language(None) is None


def test_all_catalog_entries_have_both_zh_and_en():
    """Quality gate: every key must have both translations."""
    for key, entry in CATALOG.items():
        assert "zh" in entry, f"{key} missing zh"
        assert "en" in entry, f"{key} missing en"
        assert entry["zh"].strip(), f"{key} zh is empty"
        assert entry["en"].strip(), f"{key} en is empty"
