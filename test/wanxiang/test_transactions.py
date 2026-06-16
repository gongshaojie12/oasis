# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: Transaction store unit tests (InMemory + SQLite persistence)."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

import pytest


def _new_inmem():
    from wanxiang.api.transactions import InMemoryTransactionStore
    return InMemoryTransactionStore()


def _new_tx(workspace_id="ws-1", kind="topup", delta=100, balance_after=100,
             note="", tx_id="auto", **kw):
    from wanxiang.api.transactions import Transaction
    return Transaction(
        tx_id=tx_id, workspace_id=workspace_id, kind=kind,
        delta_cost_units=delta, balance_after=balance_after, note=note,
        **kw,
    )


def test_record_and_list_returns_desc_order():
    from datetime import datetime, timedelta, timezone
    store = _new_inmem()
    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    t1 = store.record(_new_tx(delta=100, balance_after=100,
                                 created_at=base))
    t2 = store.record(_new_tx(delta=200, balance_after=300,
                                 created_at=base + timedelta(seconds=1)))
    t3 = store.record(_new_tx(delta=-50, balance_after=250, kind="usage",
                                 created_at=base + timedelta(seconds=2)))
    items = store.list_for_workspace("ws-1")
    assert len(items) == 3
    # DESC by created_at; t3 latest
    assert items[0].tx_id == t3.tx_id
    assert items[-1].tx_id == t1.tx_id


def test_filter_by_kind():
    store = _new_inmem()
    store.record(_new_tx(kind="topup", delta=100, balance_after=100))
    store.record(_new_tx(kind="usage", delta=-30, balance_after=70))
    store.record(_new_tx(kind="topup", delta=50, balance_after=120))
    topups = store.list_for_workspace("ws-1", kind="topup")
    assert len(topups) == 2
    assert all(t.kind == "topup" for t in topups)
    usages = store.list_for_workspace("ws-1", kind="usage")
    assert len(usages) == 1


def test_total_balance_change_sums():
    store = _new_inmem()
    store.record(_new_tx(kind="topup", delta=100, balance_after=100))
    store.record(_new_tx(kind="usage", delta=-30, balance_after=70))
    store.record(_new_tx(kind="topup", delta=50, balance_after=120))
    assert store.total_balance_change("ws-1") == 120
    assert store.total_balance_change("ws-1", kind="topup") == 150
    assert store.total_balance_change("ws-1", kind="usage") == -30


def test_sqlite_persistence_roundtrip(tmp_path):
    from wanxiang.api.transactions import make_transaction_store
    db = str(tmp_path / "tx.db")
    s1 = make_transaction_store(db)
    s1.record(_new_tx(kind="topup", delta=100, balance_after=100,
                       created_by_user_id="admin1"))
    s1.record(_new_tx(kind="usage", delta=-25, balance_after=75,
                       related_task_id="task-x"))
    # Re-open fresh store from same DB
    s2 = make_transaction_store(db)
    items = s2.list_for_workspace("ws-1")
    assert len(items) == 2
    kinds = {t.kind for t in items}
    assert kinds == {"topup", "usage"}
    # Field fidelity
    topup = [t for t in items if t.kind == "topup"][0]
    assert topup.delta_cost_units == 100
    assert topup.created_by_user_id == "admin1"
    usage = [t for t in items if t.kind == "usage"][0]
    assert usage.related_task_id == "task-x"


def test_limit_truncates():
    store = _new_inmem()
    for i in range(10):
        store.record(_new_tx(delta=i, balance_after=i))
    items = store.list_for_workspace("ws-1", limit=3)
    assert len(items) == 3


def test_factory_returns_inmemory_for_none():
    from wanxiang.api.transactions import (InMemoryTransactionStore,
                                              make_transaction_store)
    s = make_transaction_store(None)
    assert isinstance(s, InMemoryTransactionStore)


def test_list_for_workspace_filters_by_workspace():
    store = _new_inmem()
    store.record(_new_tx(workspace_id="ws-1", delta=100, balance_after=100))
    store.record(_new_tx(workspace_id="ws-2", delta=200, balance_after=200))
    a = store.list_for_workspace("ws-1")
    b = store.list_for_workspace("ws-2")
    assert len(a) == 1 and a[0].workspace_id == "ws-1"
    assert len(b) == 1 and b[0].workspace_id == "ws-2"
