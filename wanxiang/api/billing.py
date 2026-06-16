# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Workspace balance operations (P4): atomic topup / deduct / refund.

Used by:
- ``routes/admin.py`` for manual top-ups + refunds (super-admin)
- ``routes/simulate.py`` / ``routes/simulations.py`` for usage deductions

Each op acquires a per-workspace ``RLock`` so concurrent admin top-ups +
background simulation deductions stay serialized. The workspace store and
transaction store are passed in as args (rather than module globals) so
tests can use InMemory stores without spinning up a SQLite DB.
"""
from __future__ import annotations

import logging
from threading import RLock

from wanxiang.api.transactions import Transaction

log = logging.getLogger(__name__)

# Per-workspace lock to serialize concurrent topup/deduct against one workspace
_workspace_locks: dict[str, RLock] = {}
_locks_meta = RLock()


def _ws_lock(workspace_id: str) -> RLock:
    with _locks_meta:
        if workspace_id not in _workspace_locks:
            _workspace_locks[workspace_id] = RLock()
        return _workspace_locks[workspace_id]


class InsufficientBalanceError(Exception):
    """Raised by ``deduct_workspace`` when ``enforce=True`` and the
    workspace can't cover the requested deduction."""

    def __init__(self, *, workspace_id: str, required: int, available: int):
        self.workspace_id = workspace_id
        self.required = required
        self.available = available
        super().__init__(
            f"workspace={workspace_id} required={required} "
            f"available={available}")


def topup_workspace(*, workspace_store, transaction_store,
                      workspace_id: str, amount: int,
                      created_by_user_id: str | None = None,
                      note: str = "") -> Transaction:
    """Add ``amount`` cost_units to a workspace and record a ``topup`` tx.

    ``amount`` must be positive; use ``deduct_workspace`` to subtract.
    Raises ``ValueError`` on invalid amount or missing workspace.
    """
    if amount <= 0:
        raise ValueError(f"topup amount must be positive, got {amount}")
    lock = _ws_lock(workspace_id)
    with lock:
        ws = workspace_store.get_workspace(workspace_id)
        if not ws:
            raise ValueError(f"workspace {workspace_id} not found")
        new_balance = ws.balance_cost_units + amount
        workspace_store.update_workspace(
            workspace_id, balance_cost_units=new_balance)
        tx = Transaction(
            tx_id="auto", workspace_id=workspace_id, kind="topup",
            delta_cost_units=amount, balance_after=new_balance, note=note,
            created_by_user_id=created_by_user_id,
        )
        return transaction_store.record(tx)


def deduct_workspace(*, workspace_store, transaction_store,
                       workspace_id: str, amount: int,
                       related_task_id: str | None = None,
                       note: str = "",
                       enforce: bool = True) -> Transaction:
    """Subtract ``amount`` from workspace balance; record a ``usage`` tx.

    - ``enforce=True``: raise ``InsufficientBalanceError`` without deducting
      when balance < amount.
    - ``enforce=False``: allow negative balance (logs a warning). Used by
      MVP "best-effort" hook so legacy clients aren't blocked.
    """
    if amount <= 0:
        raise ValueError(f"deduct amount must be positive, got {amount}")
    lock = _ws_lock(workspace_id)
    with lock:
        ws = workspace_store.get_workspace(workspace_id)
        if not ws:
            raise ValueError(f"workspace {workspace_id} not found")
        if enforce and ws.balance_cost_units < amount:
            raise InsufficientBalanceError(
                workspace_id=workspace_id,
                required=amount,
                available=ws.balance_cost_units)
        new_balance = ws.balance_cost_units - amount
        if new_balance < 0:
            log.warning("workspace=%s went negative balance=%d (enforce=%s)",
                        workspace_id, new_balance, enforce)
        workspace_store.update_workspace(
            workspace_id, balance_cost_units=new_balance)
        tx = Transaction(
            tx_id="auto", workspace_id=workspace_id, kind="usage",
            delta_cost_units=-amount, balance_after=new_balance, note=note,
            related_task_id=related_task_id,
        )
        return transaction_store.record(tx)


def refund_workspace(*, workspace_store, transaction_store,
                       workspace_id: str, amount: int,
                       related_task_id: str | None = None,
                       note: str = "",
                       created_by_user_id: str | None = None) -> Transaction:
    """Credit a refund (positive ``amount``) and record a ``refund`` tx."""
    if amount <= 0:
        raise ValueError(f"refund amount must be positive, got {amount}")
    lock = _ws_lock(workspace_id)
    with lock:
        ws = workspace_store.get_workspace(workspace_id)
        if not ws:
            raise ValueError(f"workspace {workspace_id} not found")
        new_balance = ws.balance_cost_units + amount
        workspace_store.update_workspace(
            workspace_id, balance_cost_units=new_balance)
        return transaction_store.record(Transaction(
            tx_id="auto", workspace_id=workspace_id, kind="refund",
            delta_cost_units=amount, balance_after=new_balance, note=note,
            related_task_id=related_task_id,
            created_by_user_id=created_by_user_id,
        ))


__all__ = [
    "InsufficientBalanceError",
    "topup_workspace", "deduct_workspace", "refund_workspace",
]
