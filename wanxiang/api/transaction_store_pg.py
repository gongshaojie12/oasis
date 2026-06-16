# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PgTransactionStore (P4): Postgres mirror of SqliteTransactionStore."""
from __future__ import annotations

import uuid
from datetime import datetime
from threading import Lock

from wanxiang.api.transactions import Transaction

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    tx_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('topup','usage','refund','adjust')),
    delta_cost_units INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_by_user_id TEXT,
    related_task_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tx_workspace_time
    ON transactions(workspace_id, created_at DESC);
"""


def _row_to_tx(row: dict) -> Transaction:
    return Transaction(
        tx_id=row["tx_id"],
        workspace_id=row["workspace_id"],
        kind=row["kind"],
        delta_cost_units=row["delta_cost_units"],
        balance_after=row["balance_after"],
        note=row["note"] or "",
        created_by_user_id=row["created_by_user_id"],
        related_task_id=row["related_task_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class PgTransactionStore:
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

    def record(self, tx: Transaction) -> Transaction:
        if tx.tx_id == "auto":
            tx.tx_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO transactions "
                "(tx_id, workspace_id, kind, delta_cost_units, balance_after, "
                " note, created_by_user_id, related_task_id, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (tx.tx_id, tx.workspace_id, tx.kind, tx.delta_cost_units,
                 tx.balance_after, tx.note, tx.created_by_user_id,
                 tx.related_task_id, tx.created_at.isoformat()))
        return tx

    def list_for_workspace(self, workspace_id: str, *,
                              limit: int = 100,
                              kind: str | None = None) -> list[Transaction]:
        sql = ("SELECT * FROM transactions WHERE workspace_id = %s "
               "{kind_clause} ORDER BY created_at DESC LIMIT %s")
        params: list = [workspace_id]
        if kind:
            sql = sql.format(kind_clause="AND kind = %s")
            params.append(kind)
        else:
            sql = sql.format(kind_clause="")
        params.append(int(limit))
        with self._connect() as conn:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
        return [_row_to_tx(r) for r in rows]

    def total_balance_change(self, workspace_id: str, *,
                                kind: str | None = None) -> int:
        sql = ("SELECT COALESCE(SUM(delta_cost_units), 0) AS s "
               "FROM transactions WHERE workspace_id = %s")
        params: list = [workspace_id]
        if kind:
            sql += " AND kind = %s"
            params.append(kind)
        with self._connect() as conn:
            cur = conn.execute(sql, params)
            row = cur.fetchone()
        return int(row["s"] or 0)

    def list_all(self, *, limit: int = 100,
                   kind: str | None = None) -> list[Transaction]:
        sql = "SELECT * FROM transactions {kind_clause} " \
              "ORDER BY created_at DESC LIMIT %s"
        params: list = []
        if kind:
            sql = sql.format(kind_clause="WHERE kind = %s")
            params.append(kind)
        else:
            sql = sql.format(kind_clause="")
        params.append(int(limit))
        with self._connect() as conn:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
        return [_row_to_tx(r) for r in rows]
