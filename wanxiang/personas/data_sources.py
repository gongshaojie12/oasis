# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""M1 多源数据接入抽象(spec §M1)。

把"画像分布从哪来"抽象成统一接口 ``DataSource.load() -> DistributionProfile``。
三个实现:
- ``StaticFileSource``:读内置 yaml 文件(系统预置画像)。
- ``UploadSource``:接收管理员上传的画像内容(yaml/json 已解析的 dict)。
- ``SyntheticSource``:稀疏维度的概率合成补缺(给定目标维度的边际比例)。

所有源统一产出 ``DistributionProfile``(规范化的 demographic/personality/media
dict 的轻包装),再经 ingest_compliance 处理后入库。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class DistributionProfile:
    """规范化画像 + 元信息。content 形如 {demographic, personality, media}。"""
    content: dict
    name: str = ""
    source_type: str = "upload"
    notes: list[str] = field(default_factory=list)


class DataSource(Protocol):
    """spec §M1 接口:``load(segment_spec) -> DistributionProfile``。"""

    def load(self, segment_spec: Any = None) -> DistributionProfile: ...


class StaticFileSource:
    """从内置 yaml 文件加载(系统预置画像)。"""

    def __init__(self, path: str):
        self.path = path

    def load(self, segment_spec: Any = None) -> DistributionProfile:
        import os
        import yaml
        from wanxiang.datasources.distribution import load_distribution_from_dict
        with open(self.path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        # 规范化成 list 形态
        view = load_distribution_from_dict(raw)
        content: dict = {}
        if isinstance(raw.get("name"), str):
            content["name"] = raw["name"]
        for g in ("demographic", "personality", "media"):
            content[g] = [
                {"name": t["name"],
                 "distribution": {"values": t["distribution"]["values"]}}
                for t in list(view.get(g, []))
            ]
        name = content.get("name") or os.path.basename(self.path)
        return DistributionProfile(content=content, name=name,
                                   source_type="builtin")


class UploadSource:
    """从管理员上传的内容(已解析为 dict)加载。"""

    def __init__(self, raw: dict, name: str = ""):
        self.raw = raw or {}
        self.name = name

    def load(self, segment_spec: Any = None) -> DistributionProfile:
        from wanxiang.datasources.distribution import load_distribution_from_dict
        view = load_distribution_from_dict(self.raw)
        content: dict = {}
        if isinstance(self.raw.get("name"), str):
            content["name"] = self.raw["name"]
        for g in ("demographic", "personality", "media"):
            content[g] = [
                {"name": t["name"],
                 "distribution": {"values": t["distribution"]["values"]}}
                for t in list(view.get(g, []))
            ]
        name = self.name or content.get("name") or "uploaded"
        return DistributionProfile(content=content, name=name,
                                   source_type="upload")


class SyntheticSource:
    """稀疏维度概率补缺。

    给定 ``marginals``:``{group: {trait_name: {value: weight, ...}}}``,
    生成规范化的 trait 列表。用于:上传画像缺 personality/media 时补默认
    估计值;或填补稀疏细分群体(spec §M1 "合成补缺,不碰真实个人")。
    """

    # 缺省的 personality/media 估计(均匀偏中性),仅作占位,标注为合成。
    DEFAULT_PERSONALITY = {
        "价格敏感度": {"0.3": 0.3, "0.5": 0.4, "0.7": 0.3},
        "尝鲜意愿": {"0.3": 0.3, "0.5": 0.4, "0.7": 0.3},
        "健康意识": {"0.3": 0.3, "0.5": 0.4, "0.7": 0.3},
        "从众倾向": {"0.3": 0.35, "0.5": 0.4, "0.7": 0.25},
    }
    DEFAULT_MEDIA = {
        "小红书": {"0.0": 0.3, "0.5": 0.4, "0.9": 0.3},
        "抖音": {"0.0": 0.2, "0.5": 0.4, "0.9": 0.4},
        "微信": {"0.0": 0.1, "0.5": 0.4, "0.9": 0.5},
    }

    def __init__(self, marginals: dict | None = None):
        self.marginals = marginals

    def load(self, segment_spec: Any = None) -> DistributionProfile:
        marg = self.marginals or {
            "personality": self.DEFAULT_PERSONALITY,
            "media": self.DEFAULT_MEDIA,
        }
        content: dict = {}
        for group, traits in marg.items():
            lst = []
            for tname, choices in traits.items():
                values = [{"label": {"zh": str(v), "en": str(v)},
                           "weight": float(w)} for v, w in choices.items()]
                lst.append({"name": {"zh": tname, "en": tname},
                            "distribution": {"values": values}})
            content[group] = lst
        return DistributionProfile(
            content=content, name="synthetic",
            source_type="synthetic",
            notes=["合成补缺数据(非真实采集),仅作占位估计"])


def merge_profiles(*profiles: DistributionProfile) -> DistributionProfile:
    """合并多个 profile(后者补前者缺的 group)。content group 取第一个非空。"""
    merged: dict = {}
    notes: list[str] = []
    name = ""
    for p in profiles:
        if not name and p.name:
            name = p.name
        notes.extend(p.notes)
        for g in ("demographic", "personality", "media"):
            if not merged.get(g) and p.content.get(g):
                merged[g] = p.content[g]
        if "name" not in merged and p.content.get("name"):
            merged["name"] = p.content["name"]
    return DistributionProfile(content=merged, name=name,
                               source_type="merged", notes=notes)


__all__ = ["DistributionProfile", "DataSource", "StaticFileSource",
           "UploadSource", "SyntheticSource", "merge_profiles"]
