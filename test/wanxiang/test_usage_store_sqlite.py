# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteUsageStore: same semantics as in-memory, plus persistence."""
from datetime import datetime, timezone, timedelta

import pytest

from wanxiang.api.usage import UsageEvent
from wanxiang.api.usage_store_sqlite import SqliteUsageStore


def _evt(tenant="acme", cost=100, when=None):
    return UsageEvent(
        event_id="auto", tenant_id=tenant, task_id=None,
        mode="decision_only", n_agents=50, rounds=0,
        decision_kind="rate", cost_units=cost, status="done",
        recorded_at=when or datetime.now(timezone.utc))


def test_sqlite_record_and_query_roundtrip(tmp_path):
    s = SqliteUsageStore(str(tmp_path / "u.db"))
    s.record(_evt(cost=100))
    s.record(_evt(cost=200))
    now = datetime.now(timezone.utc)
    r = s.query("acme", now - timedelta(hours=1), now + timedelta(hours=1))
    assert r["total_cost_units"] == 300


def test_sqlite_persistence_across_reopen(tmp_path):
    p = str(tmp_path / "u.db")
    s1 = SqliteUsageStore(p)
    s1.record(_evt(cost=500))
    s2 = SqliteUsageStore(p)
    now = datetime.now(timezone.utc)
    r = s2.query("acme", now - timedelta(hours=1), now + timedelta(hours=1))
    assert r["total_cost_units"] == 500


def test_sqlite_tenant_isolation(tmp_path):
    s = SqliteUsageStore(str(tmp_path / "u.db"))
    s.record(_evt(tenant="acme", cost=100))
    s.record(_evt(tenant="beta", cost=999))
    now = datetime.now(timezone.utc)
    assert s.query("acme", now - timedelta(hours=1),
                    now + timedelta(hours=1))["total_cost_units"] == 100


def test_sqlite_monthly(tmp_path):
    s = SqliteUsageStore(str(tmp_path / "u.db"))
    s.record(_evt(cost=100, when=datetime(2026, 5, 31, tzinfo=timezone.utc)))
    s.record(_evt(cost=200, when=datetime(2026, 6, 15, tzinfo=timezone.utc)))
    s.record(_evt(cost=300, when=datetime(2026, 7, 1, tzinfo=timezone.utc)))
    assert s.monthly("acme", 2026, 6)["total_cost_units"] == 200
