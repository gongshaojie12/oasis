# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P5: ScenarioTemplate locale support."""
from __future__ import annotations

import os

import pytest

from wanxiang.scenarios import (instantiate, list_templates, load_template)


TEMPLATES_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..",
    "wanxiang", "scenarios", "templates"))


def _var_names(template):
    out = []
    for v in template.variables:
        if isinstance(v, dict):
            out.append(v["name"])
        else:
            out.append(getattr(v, "name"))
    return out


def test_consumer_template_has_en_material():
    t = load_template("consumer_concept_test")
    var_names = _var_names(t)
    values = {n: "X" for n in var_names}
    inst = instantiate(t, values, locale="en")
    assert "X" in inst["material"]


def test_consumer_template_zh_default():
    t = load_template("consumer_concept_test")
    var_names = _var_names(t)
    values = {n: "X" for n in var_names}
    inst = instantiate(t, values)
    # zh default — material should contain Chinese characters
    assert any('一' <= c <= '鿿' for c in inst["material"]), (
        f"zh material should contain Chinese characters: {inst['material']}")


def test_all_3_templates_have_en():
    for name in ("consumer_concept_test", "marketing_ad_ab_test",
                  "brand_sentiment_probe"):
        t = load_template(name)
        var_names = _var_names(t)
        values = {n: "x" for n in var_names}
        inst = instantiate(t, values, locale="en")
        assert inst["material"], f"empty en material for {name}"
        assert inst["question"], f"empty en question for {name}"


def test_en_material_contains_english_words():
    """Verify the EN material is actually written in English, not just zh."""
    t = load_template("consumer_concept_test")
    var_names = _var_names(t)
    values = {n: "BRAND_X" for n in var_names}
    inst = instantiate(t, values, locale="en")
    # English material should contain ASCII letters in meaningful quantity
    ascii_letters = sum(1 for c in inst["material"] if c.isascii() and c.isalpha())
    assert ascii_letters > 5, (
        f"en material does not appear to be English: {inst['material']!r}")


def test_template_locale_unknown_falls_back_to_zh():
    t = load_template("consumer_concept_test")
    var_names = _var_names(t)
    values = {n: "X" for n in var_names}
    inst = instantiate(t, values, locale="fr")
    assert inst["material"]  # graceful fallback (zh)
    # Should match zh output
    inst_zh = instantiate(t, values)
    assert inst["material"] == inst_zh["material"]


def test_legacy_template_without_en_field_still_works(tmp_path):
    """A user-authored template with plain string fields still loads."""
    p = tmp_path / "legacy.yaml"
    p.write_text("""
id: legacy
name: 旧模板
description: 旧描述
decision_kind: rate
material_template: |
  {brand} 测试
question_template: 评分？
variables:
  - name: brand
    type: text
    required: true
default_options: null
""", encoding="utf-8")
    # Bypass the built-in template-dir loader by reading directly
    import yaml
    from wanxiang.scenarios.template import _build
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    t = _build(raw)
    inst = instantiate(t, {"brand": "X"})
    assert "X 测试" in inst["material"]
    # legacy → en gracefully falls back to zh
    inst_en = instantiate(t, {"brand": "X"}, locale="en")
    assert "X 测试" in inst_en["material"]


def test_template_endpoint_locale_aware():
    """E2E: GET /v1/templates respects Accept-Language."""
    from fastapi.testclient import TestClient
    from wanxiang.api.app import create_app

    app = create_app()
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    r_zh = c.get("/v1/templates").json()
    r_en = c.get("/v1/templates", headers={"accept-language": "en"}).json()
    # Both should list all 3 templates
    assert isinstance(r_zh, list) and len(r_zh) >= 3
    assert isinstance(r_en, list) and len(r_en) >= 3
    # Names should differ in zh vs en for each template (en is translated)
    zh_names = {t["id"]: t["name"] for t in r_zh}
    en_names = {t["id"]: t["name"] for t in r_en}
    # At least one template has different names
    different = sum(1 for tid in zh_names if zh_names[tid] != en_names[tid])
    assert different >= 1, (
        f"expected some template names to differ across locales, "
        f"got zh={zh_names} en={en_names}")
