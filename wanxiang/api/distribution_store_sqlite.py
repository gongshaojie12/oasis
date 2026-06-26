# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteDistributionStore —— 人群画像库 SQLite 后端。"""
from __future__ import annotations

import json
import os
import sqlite3
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
    enabled INTEGER NOT NULL DEFAULT 1,
    builtin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by_user_id TEXT
);
"""


def _row_to_rec(row: sqlite3.Row) -> DistributionRecord:
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


class SqliteDistributionStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._lock = Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False,
                               isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def get(self, distribution_id: str) -> DistributionRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM distributions WHERE distribution_id = ?",
                (distribution_id,)).fetchone()
        return _row_to_rec(row) if row else None

    def get_by_slug(self, slug: str) -> DistributionRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM distributions WHERE slug = ?",
                (slug,)).fetchone()
        return _row_to_rec(row) if row else None

    def list_all(self, *, enabled_only: bool = False
                 ) -> list[DistributionRecord]:
        q = "SELECT * FROM distributions"
        if enabled_only:
            q += " WHERE enabled = 1"
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
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(distribution_id) DO UPDATE SET "
                " slug=excluded.slug, name_zh=excluded.name_zh, "
                " name_en=excluded.name_en, description=excluded.description, "
                " source_type=excluded.source_type, content=excluded.content, "
                " trait_counts=excluded.trait_counts, "
                " enabled=excluded.enabled, builtin=excluded.builtin, "
                " updated_at=excluded.updated_at, "
                " created_by_user_id=excluded.created_by_user_id",
                (rec.distribution_id, rec.slug, rec.name_zh, rec.name_en,
                 rec.description, rec.source_type,
                 json.dumps(rec.content, ensure_ascii=False),
                 json.dumps(rec.trait_counts, ensure_ascii=False),
                 1 if rec.enabled else 0, 1 if rec.builtin else 0,
                 rec.created_at.isoformat(), rec.updated_at.isoformat(),
                 rec.created_by_user_id))
        return rec

    def set_enabled(self, distribution_id: str, enabled: bool) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE distributions SET enabled = ?, updated_at = ? "
                "WHERE distribution_id = ?",
                (1 if enabled else 0, datetime.now().isoformat(),
                 distribution_id))

    def delete(self, distribution_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM distributions WHERE distribution_id = ?",
                         (distribution_id,))
