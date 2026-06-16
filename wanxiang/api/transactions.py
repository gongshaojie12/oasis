# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Workspace balance transaction log (P4).

Every balance change (admin top-up, usage deduction, refund) writes one row.
Provides an audit trail + accountability for /v1/admin/transactions and the
workspace-scoped /v1/workspaces/{slug}/transactions endpoints.

Backends mirror ``usage_store``: InMemory (tests/dev), Sqlite (default),
Postgres (production). DSN dispatch in ``make_transaction_store``.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Literal
from urllib.parse import urlparse


TxKind = Literal["topup", "usage", "refund", "adjust"]


@dataclass
class Transaction:
    tx_id: str
    workspace_id: str
    kind: str                    # "topup" | "usage" | "refund" | "adjust"
    delta_cost_units: int        # signed: +topup, -usage
    balance_after: int           # snapshot after applying delta
    note: str = ""
    # admin who initiated (for topup/refund); None for system usage
    created_by_user_id: str | None = None
    # for usage deductions / refunds tied to a sim task
    related_task_id: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "tx_id": self.tx_id,
            "workspace_id": self.workspace_id,
            "kind": self.kind,
            "delta_cost_units": self.delta_cost_units,
            "balance_after": self.balance_after,
            "note": self.note,
            "created_by_user_id": self.created_by_user_id,
            "related_task_id": self.related_task_id,
            "created_at": self.created_at.isoformat(),
        }


class InMemoryTransactionStore:
    def __init__(self):
        self._tx: list[Transaction] = []
        self._lock = Lock()

    def record(self, tx: Transaction) -> Transaction:
        if tx.tx_id == "auto":
            tx.tx_id = uuid.uuid4().hex
        with self._lock:
            self._tx.append(tx)
        return tx

    def list_for_workspace(self, workspace_id: str, *,
                              limit: int = 100,
                              kind: str | None = None) -> list[Transaction]:
        with self._lock:
            items = [t for t in self._tx if t.workspace_id == workspace_id]
        if kind:
            items = [t for t in items if t.kind == kind]
        items.sort(key=lambda t: t.created_at, reverse=True)
        return items[:limit]

    def total_balance_change(self, workspace_id: str, *,
                                kind: str | None = None) -> int:
        items = self.list_for_workspace(
            workspace_id, limit=10**9, kind=kind)
        return sum(t.delta_cost_units for t in items)

    def list_all(self, *, limit: int = 100,
                   kind: str | None = None) -> list[Transaction]:
        with self._lock:
            items = list(self._tx)
        if kind:
            items = [t for t in items if t.kind == kind]
        items.sort(key=lambda t: t.created_at, reverse=True)
        return items[:limit]


def make_transaction_store(dsn: str | None, *, eager_init: bool = True):
    """DSN dispatch mirroring ``make_usage_store``."""
    if not dsn:
        return InMemoryTransactionStore()
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()
    # Windows raw path C:\foo\bar.db parses with scheme='c'; treat as path.
    if len(scheme) == 1 and scheme.isalpha():
        scheme = ""
    if scheme in ("postgresql", "postgres"):
        from wanxiang.api.transaction_store_pg import PgTransactionStore
        return PgTransactionStore(dsn, eager_init=eager_init)
    if scheme == "sqlite":
        path = parsed.path or dsn[len("sqlite:"):]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        from wanxiang.api.transaction_store_sqlite import (
            SqliteTransactionStore)
        return SqliteTransactionStore(path)
    if not scheme:
        from wanxiang.api.transaction_store_sqlite import (
            SqliteTransactionStore)
        return SqliteTransactionStore(dsn)
    raise ValueError(f"unsupported transaction store DSN scheme: {scheme!r}")


__all__ = [
    "Transaction", "TxKind",
    "InMemoryTransactionStore", "make_transaction_store",
]
