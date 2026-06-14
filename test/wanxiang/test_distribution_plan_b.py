# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P5: Plan B yaml format support + backward compat."""
from __future__ import annotations

import os
import textwrap

import pytest

from wanxiang.datasources.distribution import load_distribution

DIST_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..",
                  "wanxiang", "datasources", "distributions"))


def _write(tmp_path, content):
    p = tmp_path / "d.yaml"
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_loads_plan_a_legacy_format(tmp_path):
    """Old format still works."""
    p = _write(tmp_path, textwrap.dedent("""
        demographic:
          城市:
            北京: 0.6
            上海: 0.4
    """).strip())
    d = load_distribution(p)
    # Internal canonical form: name should expose both zh + en
    # (en falls back to zh for legacy yaml)
    names = list(d["demographic"])
    assert names, "expected at least one demographic trait"
    name = names[0]["name"]
    assert isinstance(name, dict)
    assert name["zh"] == "城市"
    assert name["en"] == "城市"


def test_loads_plan_b_format(tmp_path):
    p = _write(tmp_path, textwrap.dedent("""
        demographic:
          - name: { zh: 城市, en: city }
            distribution:
              values:
                - label: { zh: 北京, en: Beijing }
                  weight: 0.6
                - label: { zh: 上海, en: Shanghai }
                  weight: 0.4
    """).strip())
    d = load_distribution(p)
    name = list(d["demographic"])[0]["name"]
    assert name["zh"] == "城市"
    assert name["en"] == "city"


def test_plan_b_weights_preserved(tmp_path):
    p = _write(tmp_path, textwrap.dedent("""
        demographic:
          - name: { zh: 城市, en: city }
            distribution:
              values:
                - label: { zh: 北京, en: Beijing }
                  weight: 0.6
                - label: { zh: 上海, en: Shanghai }
                  weight: 0.4
    """).strip())
    d = load_distribution(p)
    trait = list(d["demographic"])[0]
    values = trait["distribution"]["values"]
    # internal form: list of {label: {zh, en}, weight}
    weights = [v["weight"] for v in values]
    assert sum(weights) == pytest.approx(1.0)
    # Each entry has a bilingual label
    for v in values:
        assert isinstance(v["label"], dict)
        assert v["label"].get("zh")
        assert v["label"].get("en")


def test_plan_b_en_falls_back_to_zh_when_missing(tmp_path):
    p = _write(tmp_path, textwrap.dedent("""
        demographic:
          - name: { zh: 城市 }
            distribution:
              values:
                - label: { zh: 北京 }
                  weight: 1.0
    """).strip())
    d = load_distribution(p)
    name = list(d["demographic"])[0]["name"]
    assert name["en"] == "城市"
    val_label = list(d["demographic"])[0]["distribution"]["values"][0]["label"]
    assert val_label["en"] == "北京"


def test_legacy_dict_access_still_works(tmp_path):
    """PersonaBuilder + existing tests access dist['demographic']['城市']
    as dict-of-trait-name. This must continue to work as a backward-compat view."""
    p = _write(tmp_path, textwrap.dedent("""
        demographic:
          城市:
            北京: 0.6
            上海: 0.4
        personality:
          价格敏感度:
            "0.2": 0.5
            "0.8": 0.5
        media: {}
    """).strip())
    d = load_distribution(p)
    # Legacy access via zh key
    cities = d["demographic"]["城市"]
    assert isinstance(cities, list)
    pairs = sorted(cities, key=lambda x: x[0])
    assert pairs == [("北京", 0.6), ("上海", 0.4)] or sorted(
        [(v, w) for v, w in cities]) == sorted([("北京", 0.6), ("上海", 0.4)])


@pytest.mark.parametrize("fname", [
    "cn_z_generation_v1.yaml",
    "cn_millennial_premium_v1.yaml",
    "cn_silver_economy_v1.yaml",
])
def test_real_distributions_load_after_refactor(fname):
    """The committed distribution yamls work in en too."""
    d = load_distribution(os.path.join(DIST_DIR, fname))
    # All names should expose en (not None)
    for sec in ("demographic", "personality", "media"):
        traits = list(d.get(sec, []))
        for trait in traits:
            name = trait["name"]
            assert isinstance(name, dict), f"{sec} trait name not bilingual: {trait}"
            assert name["zh"], f"empty zh name in {sec}: {trait}"
            assert name["en"], f"empty en name in {sec}: {trait}"


@pytest.mark.parametrize("fname", [
    "cn_z_generation_v1.yaml",
    "cn_millennial_premium_v1.yaml",
    "cn_silver_economy_v1.yaml",
])
def test_real_distributions_values_have_bilingual_labels(fname):
    d = load_distribution(os.path.join(DIST_DIR, fname))
    for sec in ("demographic", "personality", "media"):
        for trait in list(d.get(sec, [])):
            values = trait["distribution"]["values"]
            for v in values:
                assert isinstance(v["label"], dict)
                assert v["label"].get("zh") is not None
                assert v["label"].get("en") is not None
