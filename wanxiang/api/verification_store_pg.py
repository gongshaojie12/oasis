# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PgVerificationStore (P2) — PG mirror of SqliteVerificationStore.

Lazy psycopg import.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from threading import Lock

from wanxiang.api.verification import VerificationCode

_SCHEMA = """
CREATE TABLE IF NOT EXISTS verification_codes (
    code_id TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    identifier TEXT NOT NULL,
    purpose TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    consumed_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vcodes_lookup
    ON verification_codes(channel, identifier, purpose, consumed_at);
CREATE INDEX IF NOT EXISTS idx_vcodes_rate_limit
    ON verification_codes(channel, identifier, created_at);
"""


def _row_to_vc(row: dict) -> VerificationCode:
    return VerificationCode(
        code_id=row["code_id"],
        channel=row["channel"],
        identifier=row["identifier"],
        purpose=row["purpose"],
        code_hash=row["code_hash"],
        expires_at=datetime.fromisoformat(row["expires_at"]),
        attempts=int(row["attempts"]),
        consumed_at=(datetime.fromisoformat(row["consumed_at"])
                     if row["consumed_at"] else None),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class PgVerificationStore:
    def __init__(self, dsn: str, *, eager_init: bool = True):
        self.dsn = dsn
        self._lock = Lock()
        if eager_init:
            with self._connect() as conn:
                conn.execute(_SCHEMA)

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(self.dsn, autocommit=True,
                                row_factory=dict_row)

    def create(self, vc: VerificationCode) -> VerificationCode:
        if vc.code_id == "auto":
            vc.code_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO verification_codes "
                "(code_id, channel, identifier, purpose, code_hash, "
                " expires_at, attempts, consumed_at, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (vc.code_id, vc.channel, vc.identifier, vc.purpose,
                 vc.code_hash, vc.expires_at.isoformat(),
                 int(vc.attempts),
                 vc.consumed_at.isoformat() if vc.consumed_at else None,
                 vc.created_at.isoformat()))
        return vc

    def count_recent_sends(self, channel: str, identifier: str,
                             *, since: datetime) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) AS n FROM verification_codes "
                "WHERE channel = %s AND identifier = %s "
                "  AND created_at >= %s",
                (channel, identifier, since.isoformat()))
            row = cur.fetchone()
        return int(row["n"]) if row else 0

    def latest_active(self, channel: str, identifier: str,
                        purpose: str) -> VerificationCode | None:
        from wanxiang.api.verification import MAX_ATTEMPTS_PER_CODE
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM verification_codes "
                "WHERE channel = %s AND identifier = %s AND purpose = %s "
                "  AND consumed_at IS NULL "
                "  AND expires_at > %s "
                "  AND attempts < %s "
                "ORDER BY created_at DESC LIMIT 1",
                (channel, identifier, purpose, now_iso,
                 MAX_ATTEMPTS_PER_CODE))
            row = cur.fetchone()
        return _row_to_vc(row) if row else None

    def increment_attempts(self, code_id: str) -> int:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE verification_codes "
                "SET attempts = attempts + 1 WHERE code_id = %s",
                (code_id,))
            cur = conn.execute(
                "SELECT attempts FROM verification_codes "
                "WHERE code_id = %s", (code_id,))
            row = cur.fetchone()
        return int(row["attempts"]) if row else 0

    def consume(self, code_id: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "UPDATE verification_codes SET consumed_at = %s "
                "WHERE code_id = %s AND consumed_at IS NULL",
                (now, code_id))
            return (cur.rowcount or 0) > 0
