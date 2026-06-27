# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import os
from collections import Counter

import pytest

from wanxiang.datasources.distribution import load_distribution
from wanxiang.personas import PersonaBuilder

SAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "test", "wanxiang", "fixtures",
)


def _write(tmp_path, content):
    p = tmp_path / "dist.yaml"
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_loader_returns_persona_builder_compatible_dict(tmp_path):
    path = _write(tmp_path, """
name: tiny
demographic:
  城市:
    北京: 0.4
    上海: 0.6
personality:
  价格敏感度:
    "0.2": 0.5
    "0.8": 0.5
media: {}
""")
    dist = load_distribution(path)
    assert "demographic" in dist and "personality" in dist and "media" in dist
    cities = dist["demographic"]["城市"]
    assert isinstance(cities, list)
    assert ("北京", 0.4) in cities
    assert ("上海", 0.6) in cities


def test_loader_coerces_numeric_keys_in_personality_and_media(tmp_path):
    path = _write(tmp_path, """
demographic: {}
personality:
  尝鲜意愿:
    "0.3": 0.5
    "0.7": 0.5
media:
  抖音:
    "0.0": 0.5
    "0.9": 0.5
""")
    dist = load_distribution(path)
    pairs = dist["personality"]["尝鲜意愿"]
    values = [v for v, _ in pairs]
    assert all(isinstance(v, float) for v in values), pairs
    assert 0.3 in values and 0.7 in values
    m_pairs = dist["media"]["抖音"]
    assert all(isinstance(v, float) for v, _ in m_pairs)


def test_loader_leaves_demographic_string_values_as_strings(tmp_path):
    path = _write(tmp_path, """
demographic:
  性别:
    男: 0.5
    女: 0.5
personality: {}
media: {}
""")
    dist = load_distribution(path)
    vals = [v for v, _ in dist["demographic"]["性别"]]
    assert vals == ["男", "女"] or vals == ["女", "男"]
    assert all(isinstance(v, str) for v in vals)


def test_loader_handles_missing_group(tmp_path):
    """缺失的 group 应作为空 dict 出现。"""
    path = _write(tmp_path, """
demographic:
  city:
    A: 0.5
    B: 0.5
""")
    dist = load_distribution(path)
    assert dist["demographic"]["city"]
    assert dist["personality"] == {}
    assert dist["media"] == {}


def test_loader_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_distribution(str(tmp_path / "nope.yaml"))


def test_sample_distribution_file_loads_and_feeds_personabuilder():
    """打包内置的示例分布能被加载，并能驱动 PersonaBuilder 抽样。"""
    path = os.path.join(SAMPLES_DIR, "cn_z_generation_v1.yaml")
    dist = load_distribution(path)
    pb = PersonaBuilder()
    ps = pb.sample(dist, n=2000, seed=42)
    assert len(ps) == 2000
    # 城市应至少包含 yaml 里列出的一线城市之一
    cities = Counter(p.demographic.get("城市") for p in ps)
    assert any(c in cities for c in ["北京", "上海", "广州", "深圳"])
    # 抽样比例应大致符合 yaml 权重（取一个明显占比的项目验证）
    total = sum(cities.values())
    top_share = max(cities.values()) / total
    assert top_share < 0.5  # 没有一个城市能压倒性 50%+（yaml 是 25/30/20/25）
