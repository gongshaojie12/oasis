# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: Billing ops (topup / deduct / refund) unit tests."""
from __future__ import annotations

import threading

import pytest


def _make_env():
    """Fresh in-memory workspace store + transaction store + a seeded ws."""
    from wanxiang.api.workspaces import (InMemoryWorkspaceStore, Workspace)
    from wanxiang.api.transactions import InMemoryTransactionStore
    ws_store = InMemoryWorkspaceStore()
    tx_store = InMemoryTransactionStore()
    ws = Workspace(
        workspace_id="auto", slug="acme", name="Acme",
        type="team", owner_user_id="u1", balance_cost_units=500,
    )
    ws = ws_store.create_workspace(ws)
    return ws_store, tx_store, ws


def test_topup_workspace_adds_balance_and_records_tx():
    from wanxiang.api.billing import topup_workspace
    ws_store, tx_store, ws = _make_env()
    tx = topup_workspace(
        workspace_store=ws_store, transaction_store=tx_store,
        workspace_id=ws.workspace_id, amount=100,
        created_by_user_id="admin1", note="initial",
    )
    refreshed = ws_store.get_workspace(ws.workspace_id)
    assert refreshed.balance_cost_units == 600
    assert tx.kind == "topup"
    assert tx.delta_cost_units == 100
    assert tx.balance_after == 600
    assert tx.created_by_user_id == "admin1"
    assert tx.note == "initial"


def test_topup_amount_zero_raises():
    from wanxiang.api.billing import topup_workspace
    ws_store, tx_store, ws = _make_env()
    with pytest.raises(ValueError):
        topup_workspace(workspace_store=ws_store, transaction_store=tx_store,
                          workspace_id=ws.workspace_id, amount=0,
                          created_by_user_id="admin1")


def test_topup_negative_amount_raises():
    from wanxiang.api.billing import topup_workspace
    ws_store, tx_store, ws = _make_env()
    with pytest.raises(ValueError):
        topup_workspace(workspace_store=ws_store, transaction_store=tx_store,
                          workspace_id=ws.workspace_id, amount=-5,
                          created_by_user_id="admin1")


def test_topup_unknown_workspace_raises():
    from wanxiang.api.billing import topup_workspace
    ws_store, tx_store, _ = _make_env()
    with pytest.raises(ValueError):
        topup_workspace(workspace_store=ws_store, transaction_store=tx_store,
                          workspace_id="missing", amount=100,
                          created_by_user_id="admin1")


def test_deduct_workspace_subtracts_and_records_usage_tx():
    from wanxiang.api.billing import deduct_workspace
    ws_store, tx_store, ws = _make_env()
    tx = deduct_workspace(
        workspace_store=ws_store, transaction_store=tx_store,
        workspace_id=ws.workspace_id, amount=50,
        related_task_id="task-1", note="sim run",
    )
    refreshed = ws_store.get_workspace(ws.workspace_id)
    assert refreshed.balance_cost_units == 450
    assert tx.kind == "usage"
    assert tx.delta_cost_units == -50
    assert tx.balance_after == 450
    assert tx.related_task_id == "task-1"


def test_deduct_insufficient_with_enforce_raises():
    from wanxiang.api.billing import (InsufficientBalanceError,
                                        deduct_workspace)
    ws_store, tx_store, ws = _make_env()
    with pytest.raises(InsufficientBalanceError) as ei:
        deduct_workspace(workspace_store=ws_store, transaction_store=tx_store,
                           workspace_id=ws.workspace_id, amount=1000,
                           enforce=True)
    assert ei.value.required == 1000
    assert ei.value.available == 500
    # Balance unchanged
    assert ws_store.get_workspace(ws.workspace_id).balance_cost_units == 500
    # No tx recorded
    assert tx_store.list_for_workspace(ws.workspace_id) == []


def test_deduct_insufficient_with_no_enforce_goes_negative():
    from wanxiang.api.billing import deduct_workspace
    ws_store, tx_store, ws = _make_env()
    tx = deduct_workspace(
        workspace_store=ws_store, transaction_store=tx_store,
        workspace_id=ws.workspace_id, amount=600, enforce=False,
    )
    refreshed = ws_store.get_workspace(ws.workspace_id)
    assert refreshed.balance_cost_units == -100
    assert tx.balance_after == -100


def test_refund_workspace_adds_back():
    from wanxiang.api.billing import refund_workspace
    ws_store, tx_store, ws = _make_env()
    tx = refund_workspace(
        workspace_store=ws_store, transaction_store=tx_store,
        workspace_id=ws.workspace_id, amount=25, related_task_id="task-2",
        note="apology",
    )
    refreshed = ws_store.get_workspace(ws.workspace_id)
    assert refreshed.balance_cost_units == 525
    assert tx.kind == "refund"
    assert tx.delta_cost_units == 25
    assert tx.balance_after == 525


def test_refund_negative_raises():
    from wanxiang.api.billing import refund_workspace
    ws_store, tx_store, ws = _make_env()
    with pytest.raises(ValueError):
        refund_workspace(workspace_store=ws_store, transaction_store=tx_store,
                          workspace_id=ws.workspace_id, amount=-1)


def test_concurrent_topup_deduct_serialized_correctly():
    """Race test: many threads topup +1 then deduct -1; final balance must match."""
    from wanxiang.api.billing import deduct_workspace, topup_workspace
    ws_store, tx_store, ws = _make_env()
    initial = ws_store.get_workspace(ws.workspace_id).balance_cost_units

    n_iter = 25

    def topper():
        for _ in range(n_iter):
            topup_workspace(workspace_store=ws_store,
                              transaction_store=tx_store,
                              workspace_id=ws.workspace_id,
                              amount=1, created_by_user_id="t")

    def ducker():
        for _ in range(n_iter):
            deduct_workspace(workspace_store=ws_store,
                                transaction_store=tx_store,
                                workspace_id=ws.workspace_id,
                                amount=1, enforce=False)

    threads = [threading.Thread(target=topper) for _ in range(4)] + \
              [threading.Thread(target=ducker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final = ws_store.get_workspace(ws.workspace_id).balance_cost_units
    # 4*n_iter +1's and 4*n_iter -1's → delta == 0
    assert final == initial
    # All transactions recorded
    all_tx = tx_store.list_for_workspace(ws.workspace_id, limit=10**6)
    assert len(all_tx) == 8 * n_iter


def test_balance_after_field_correct_in_sequence():
    from wanxiang.api.billing import (deduct_workspace, refund_workspace,
                                        topup_workspace)
    ws_store, tx_store, ws = _make_env()
    # ws starts at 500
    t1 = topup_workspace(workspace_store=ws_store, transaction_store=tx_store,
                           workspace_id=ws.workspace_id, amount=200,
                           created_by_user_id="a")
    assert t1.balance_after == 700
    t2 = deduct_workspace(workspace_store=ws_store,
                            transaction_store=tx_store,
                            workspace_id=ws.workspace_id, amount=100)
    assert t2.balance_after == 600
    t3 = refund_workspace(workspace_store=ws_store,
                            transaction_store=tx_store,
                            workspace_id=ws.workspace_id, amount=25)
    assert t3.balance_after == 625
