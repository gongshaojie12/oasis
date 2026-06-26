# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PgDistributionStore —— 人群画像库 PostgreSQL 后端,接口同 SQLite 版。"""
from __future__ import annotations

import json
from datetime import datetime
from threading import Lock

from wanxiang.api.distributions import DistributionRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS distributions (
    distribution_id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name_zh TEXT NOT NULL,
    name_en TEXT,
    description TEXT,
    source_type TEXT NOT NULL,
    content TEXT NOT NULL,
    trait_counts TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    builtin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by_user_id TEXT
);
"""


def _row_to_rec(row: dict) -> DistributionRecord:
    return DistributionRecord(
        distribution_id=row["distribution_id"],
        slug=row["slug"],
        name_zh=row["name_zh"],
        name_en=row["name_en"] or "",
        description=row["description"] or "",
        source_type=row["source_type"],
        content=json.loads(row["content"]) if row["content"] else {},
        trait_counts=json.loads(row["trait_counts"])
        if row["trait_counts"] else {},
        enabled=bool(row["enabled"]),
        builtin=bool(row["builtin"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        created_by_user_id=row["created_by_user_id"],
    )


class PgDistributionStore:
    def __init__(self, dsn: str, *, eager_init: bool = True):
        self.dsn = dsn
        self._lock = Lock()
        if eager_init:
            with self._connect() as conn:
                conn.execute(_SCHEMA)

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)

    def get(self, distribution_id: str) -> DistributionRecord | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM distributions WHERE distribution_id = %s",
                (distribution_id,))
            row = cur.fetchone()
        return _row_to_rec(row) if row else None

    def get_by_slug(self, slug: str) -> DistributionRecord | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM distributions WHERE slug = %s", (slug,))
            row = cur.fetchone()
        return _row_to_rec(row) if row else None

    def list_all(self, *, enabled_only: bool = False
                 ) -> list[DistributionRecord]:
        q = "SELECT * FROM distributions"
        if enabled_only:
            q += " WHERE enabled = TRUE"
        with self._connect() as conn:
            rows = conn.execute(q).fetchall()
        recs = [_row_to_rec(r) for r in rows]
        return sorted(recs, key=lambda r: (not r.builtin, r.name_zh))

    def upsert(self, rec: DistributionRecord) -> DistributionRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO distributions "
                "(distribution_id, slug, name_zh, name_en, description, "
                " source_type, content, trait_counts, enabled, builtin, "
                " created_at, updated_at, created_by_user_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (distribution_id) DO UPDATE SET "
                " slug=EXCLUDED.slug, name_zh=EXCLUDED.name_zh, "
                " name_en=EXCLUDED.name_en, description=EXCLUDED.description, "
                " source_type=EXCLUDED.source_type, content=EXCLUDED.content, "
                " trait_counts=EXCLUDED.trait_counts, "
                " enabled=EXCLUDED.enabled, builtin=EXCLUDED.builtin, "
                " updated_at=EXCLUDED.updated_at, "
                " created_by_user_id=EXCLUDED.created_by_user_id",
                (rec.distribution_id, rec.slug, rec.name_zh, rec.name_en,
                 rec.description, rec.source_type,
                 json.dumps(rec.content, ensure_ascii=False),
                 json.dumps(rec.trait_counts, ensure_ascii=False),
                 rec.enabled, rec.builtin,
                 rec.created_at.isoformat(), rec.updated_at.isoformat(),
                 rec.created_by_user_id))
        return rec

    def set_enabled(self, distribution_id: str, enabled: bool) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE distributions SET enabled = %s, updated_at = %s "
                "WHERE distribution_id = %s",
                (enabled, datetime.now().isoformat(), distribution_id))

    def delete(self, distribution_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "DELETE FROM distributions WHERE distribution_id = %s",
                (distribution_id,))
