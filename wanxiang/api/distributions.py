# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""人群画像库(M1):全局共享的分布数据,超管维护,所有工作区建沙盒可选。

DSN 分发同 model_config.py:None→InMemory;sqlite/路径→SQLite;postgresql→PG。
content 存「规范化后的画像 dict」的 JSON(demographic/personality/media)。
Docker 里 distributions 目录只读 → 上传数据只进 DB,内置 yaml 仅作启动 seed 源。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from urllib.parse import urlparse


@dataclass
class DistributionRecord:
    distribution_id: str
    slug: str
    name_zh: str
    name_en: str
    description: str
    source_type: str            # builtin | upload | synthetic | form
    content: dict               # 规范化画像 {demographic, personality, media}
    trait_counts: dict          # {demographic:int, personality:int, media:int}
    enabled: bool = True
    builtin: bool = False
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))
    created_by_user_id: str | None = None

    def to_summary(self) -> dict:
        """列表用(不含 content,体积小)。"""
        return {
            "distribution_id": self.distribution_id,
            "slug": self.slug,
            "name_zh": self.name_zh,
            "name_en": self.name_en,
            "description": self.description,
            "source_type": self.source_type,
            "trait_counts": self.trait_counts,
            "enabled": self.enabled,
            "builtin": self.builtin,
            "updated_at": self.updated_at.isoformat() if self.updated_at
            else None,
        }

    def to_detail(self) -> dict:
        d = self.to_summary()
        d["content"] = self.content
        return d


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", (name or "").strip().lower())
    s = s.strip("-")
    return s or "dist"


def count_traits(content: dict) -> dict:
    out = {}
    for g in ("demographic", "personality", "media"):
        v = (content or {}).get(g)
        out[g] = len(v) if isinstance(v, (list, dict)) else 0
    return out


class InMemoryDistributionStore:
    def __init__(self):
        self._by_id: dict[str, DistributionRecord] = {}
        self._lock = Lock()

    def get(self, distribution_id: str) -> DistributionRecord | None:
        return self._by_id.get(distribution_id)

    def get_by_slug(self, slug: str) -> DistributionRecord | None:
        return next((r for r in self._by_id.values() if r.slug == slug), None)

    def list_all(self, *, enabled_only: bool = False
                 ) -> list[DistributionRecord]:
        recs = list(self._by_id.values())
        if enabled_only:
            recs = [r for r in recs if r.enabled]
        return sorted(recs, key=lambda r: (not r.builtin, r.name_zh))

    def upsert(self, rec: DistributionRecord) -> DistributionRecord:
        with self._lock:
            self._by_id[rec.distribution_id] = rec
        return rec

    def set_enabled(self, distribution_id: str, enabled: bool) -> None:
        with self._lock:
            r = self._by_id.get(distribution_id)
            if r:
                r.enabled = enabled
                r.updated_at = datetime.now(timezone.utc)

    def delete(self, distribution_id: str) -> None:
        with self._lock:
            self._by_id.pop(distribution_id, None)


def make_distribution_store(dsn: str | None, *, eager_init: bool = True):
    if not dsn:
        return InMemoryDistributionStore()
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()
    if len(scheme) == 1 and scheme.isalpha():
        scheme = ""
    if scheme in ("postgresql", "postgres"):
        from wanxiang.api.distribution_store_pg import PgDistributionStore
        return PgDistributionStore(dsn, eager_init=eager_init)
    if scheme == "sqlite":
        path = parsed.path or dsn[len("sqlite:"):]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        from wanxiang.api.distribution_store_sqlite import (
            SqliteDistributionStore)
        return SqliteDistributionStore(path)
    if not scheme:
        from wanxiang.api.distribution_store_sqlite import (
            SqliteDistributionStore)
        return SqliteDistributionStore(dsn)
    raise ValueError(f"unsupported distribution store DSN scheme: {scheme!r}")


# 序列化辅助(pg/sqlite 共用)
def serialize_content(content: dict) -> str:
    return json.dumps(content, ensure_ascii=False)


def serialize_counts(counts: dict) -> str:
    return json.dumps(counts, ensure_ascii=False)


__all__ = ["DistributionRecord", "InMemoryDistributionStore",
           "make_distribution_store", "slugify", "count_traits",
           "serialize_content", "serialize_counts"]
