# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""InMemoryUsageStore + record/query/monthly."""
from datetime import datetime, timezone, timedelta

import pytest

from wanxiang.api.usage import InMemoryUsageStore, UsageEvent


def _evt(tenant="acme", mode="decision_only", cost=100, status="done",
         when=None, task_id=None):
    return UsageEvent(
        event_id="auto",  # store will fill if "auto"
        tenant_id=tenant, task_id=task_id, mode=mode, n_agents=100,
        rounds=0, decision_kind="rate", cost_units=cost, status=status,
        recorded_at=when or datetime.now(timezone.utc))


def test_record_assigns_event_id_if_auto():
    s = InMemoryUsageStore()
    e = s.record(_evt())
    assert e.event_id and e.event_id != "auto"


def test_query_aggregates_total():
    s = InMemoryUsageStore()
    s.record(_evt(cost=100))
    s.record(_evt(cost=200))
    now = datetime.now(timezone.utc)
    r = s.query("acme", now - timedelta(hours=1), now + timedelta(hours=1))
    assert r["total_cost_units"] == 300


def test_query_isolates_tenants():
    s = InMemoryUsageStore()
    s.record(_evt(tenant="acme", cost=100))
    s.record(_evt(tenant="beta", cost=999))
    now = datetime.now(timezone.utc)
    r = s.query("acme", now - timedelta(hours=1), now + timedelta(hours=1))
    assert r["total_cost_units"] == 100


def test_query_excludes_out_of_range():
    s = InMemoryUsageStore()
    long_ago = datetime(2020, 1, 1, tzinfo=timezone.utc)
    s.record(_evt(cost=100, when=long_ago))
    s.record(_evt(cost=200))  # now
    now = datetime.now(timezone.utc)
    r = s.query("acme", now - timedelta(hours=1), now + timedelta(hours=1))
    assert r["total_cost_units"] == 200


def test_query_by_mode_breakdown():
    s = InMemoryUsageStore()
    s.record(_evt(mode="decision_only", cost=100))
    s.record(_evt(mode="social", cost=300))
    s.record(_evt(mode="social", cost=150))
    now = datetime.now(timezone.utc)
    r = s.query("acme", now - timedelta(hours=1), now + timedelta(hours=1))
    assert r["by_mode"]["decision_only"] == 100
    assert r["by_mode"]["social"] == 450


def test_query_by_status_count():
    s = InMemoryUsageStore()
    s.record(_evt(status="done"))
    s.record(_evt(status="done"))
    s.record(_evt(status="failed"))
    now = datetime.now(timezone.utc)
    r = s.query("acme", now - timedelta(hours=1), now + timedelta(hours=1))
    assert r["by_status"]["done"] == 2
    assert r["by_status"]["failed"] == 1


def test_monthly_filters_by_year_month():
    s = InMemoryUsageStore()
    s.record(_evt(cost=100, when=datetime(2026, 5, 15, tzinfo=timezone.utc)))
    s.record(_evt(cost=200, when=datetime(2026, 6, 1, tzinfo=timezone.utc)))
    s.record(_evt(cost=300, when=datetime(2026, 6, 30, 23, 59, tzinfo=timezone.utc)))
    s.record(_evt(cost=999, when=datetime(2026, 7, 1, tzinfo=timezone.utc)))
    r = s.monthly("acme", year=2026, month=6)
    assert r["total_cost_units"] == 500  # 200 + 300


def test_monthly_invalid_month_raises():
    s = InMemoryUsageStore()
    with pytest.raises(ValueError):
        s.monthly("acme", year=2026, month=13)


def test_events_list_limited_to_100():
    s = InMemoryUsageStore()
    for _ in range(150):
        s.record(_evt(cost=1))
    now = datetime.now(timezone.utc)
    r = s.query("acme", now - timedelta(hours=1), now + timedelta(hours=1))
    assert len(r["events"]) == 100
    assert r["total_cost_units"] == 150  # all counted even though only 100 listed
