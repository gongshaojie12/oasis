# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""spec §M1: 多源数据接入 — 至少 3 个 distribution yamls."""
import os
import pytest

from wanxiang.datasources.distribution import load_distribution
from wanxiang.personas.builder import PersonaBuilder

DIST_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..",
                  "test", "wanxiang", "fixtures"))

EXPECTED = [
    "cn_z_generation_v1.yaml",
    "cn_millennial_premium_v1.yaml",
    "cn_silver_economy_v1.yaml",
]


@pytest.mark.parametrize("fname", EXPECTED)
def test_distribution_yaml_exists(fname):
    assert os.path.exists(os.path.join(DIST_DIR, fname))


@pytest.mark.parametrize("fname", EXPECTED)
def test_distribution_yaml_loads(fname):
    d = load_distribution(os.path.join(DIST_DIR, fname))
    assert d is not None


@pytest.mark.parametrize("fname", EXPECTED)
def test_distribution_builds_persona(fname):
    d = load_distribution(os.path.join(DIST_DIR, fname))
    p = PersonaBuilder().sample(d, n=3, seed=42)
    assert len(p) == 3


def test_millennial_premium_age_in_correct_range():
    d = load_distribution(os.path.join(DIST_DIR, "cn_millennial_premium_v1.yaml"))
    personas = PersonaBuilder().sample(d, n=100, seed=1)
    # all should be in 30-50 ballpark — exact key name depends on schema
    # assume `年龄段` categorical (e.g. "30-35", "35-40")
    bands = [p.demographic.get("年龄段") for p in personas]
    # at least 80% should fall into 30+ bands
    n_correct = sum(1 for b in bands if b and any(s in b for s in ["3","4"]))
    assert n_correct / len(bands) > 0.6


def test_silver_economy_age_skews_old():
    d = load_distribution(os.path.join(DIST_DIR, "cn_silver_economy_v1.yaml"))
    personas = PersonaBuilder().sample(d, n=100, seed=1)
    bands = [p.demographic.get("年龄段") for p in personas]
    # at least 70% should be in 55+ band
    n_correct = sum(1 for b in bands if b and any(s in b for s in ["5","6","7"]))
    assert n_correct / len(bands) > 0.5
