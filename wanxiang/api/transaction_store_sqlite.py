# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteTransactionStore (P4): persistent balance-log backend."""
from __future__ import annotations

import os
import sqlite3
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


def _row_to_tx(row: sqlite3.Row) -> Transaction:
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


class SqliteTransactionStore:
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

    def record(self, tx: Transaction) -> Transaction:
        if tx.tx_id == "auto":
            tx.tx_id = uuid.uuid4().hex
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO transactions "
                "(tx_id, workspace_id, kind, delta_cost_units, balance_after, "
                " note, created_by_user_id, related_task_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (tx.tx_id, tx.workspace_id, tx.kind, tx.delta_cost_units,
                 tx.balance_after, tx.note, tx.created_by_user_id,
                 tx.related_task_id, tx.created_at.isoformat()))
        return tx

    def list_for_workspace(self, workspace_id: str, *,
                              limit: int = 100,
                              kind: str | None = None) -> list[Transaction]:
        sql = ("SELECT * FROM transactions WHERE workspace_id = ? "
               "{kind_clause} ORDER BY created_at DESC LIMIT ?")
        params: list = [workspace_id]
        if kind:
            sql = sql.format(kind_clause="AND kind = ?")
            params.append(kind)
        else:
            sql = sql.format(kind_clause="")
        params.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_tx(r) for r in rows]

    def total_balance_change(self, workspace_id: str, *,
                                kind: str | None = None) -> int:
        sql = ("SELECT COALESCE(SUM(delta_cost_units), 0) AS s "
               "FROM transactions WHERE workspace_id = ?")
        params: list = [workspace_id]
        if kind:
            sql += " AND kind = ?"
            params.append(kind)
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row["s"] or 0)

    def list_all(self, *, limit: int = 100,
                   kind: str | None = None) -> list[Transaction]:
        sql = "SELECT * FROM transactions {kind_clause} " \
              "ORDER BY created_at DESC LIMIT ?"
        params: list = []
        if kind:
            sql = sql.format(kind_clause="WHERE kind = ?")
            params.append(kind)
        else:
            sql = sql.format(kind_clause="")
        params.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_tx(r) for r in rows]
