# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""InMemoryAuditStore (M3-13)."""
from datetime import datetime, timezone, timedelta

from wanxiang.api.audit import (AuditEvent, InMemoryAuditStore,
                                  build_api_call_event, build_sim_event)


def _evt(tenant="acme", action="api_call", when=None, status=200):
    return AuditEvent(
        event_id="auto", tenant_id=tenant, action=action,
        resource_type="api", resource_id=None, request_id="rid-1",
        method="POST", path="/v1/simulate", status=status,
        ip="127.0.0.1", user_agent="curl/7", detail=None,
        recorded_at=when or datetime.now(timezone.utc))


def test_record_assigns_id():
    s = InMemoryAuditStore()
    e = s.record(_evt())
    assert e.event_id and e.event_id != "auto"


def test_query_returns_total_count():
    s = InMemoryAuditStore()
    for _ in range(5):
        s.record(_evt())
    r = s.query("acme")
    assert r["total"] == 5


def test_query_tenant_isolation():
    s = InMemoryAuditStore()
    s.record(_evt(tenant="acme"))
    s.record(_evt(tenant="other"))
    assert s.query("acme")["total"] == 1


def test_query_action_filter():
    s = InMemoryAuditStore()
    s.record(_evt(action="api_call"))
    s.record(_evt(action="sim_completed"))
    r = s.query("acme", action="sim_completed")
    assert r["total"] == 1
    assert r["events"][0]["action"] == "sim_completed"


def test_query_time_window():
    s = InMemoryAuditStore()
    old = datetime(2020, 1, 1, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    s.record(_evt(when=old))
    s.record(_evt(when=now))
    r = s.query("acme", start=now - timedelta(minutes=1))
    assert r["total"] == 1


def test_query_by_action_breakdown():
    s = InMemoryAuditStore()
    s.record(_evt(action="api_call"))
    s.record(_evt(action="api_call"))
    s.record(_evt(action="sim_completed"))
    r = s.query("acme")
    assert r["by_action"]["api_call"] == 2
    assert r["by_action"]["sim_completed"] == 1


def test_query_by_status_breakdown():
    s = InMemoryAuditStore()
    s.record(_evt(status=200))
    s.record(_evt(status=200))
    s.record(_evt(status=400))
    r = s.query("acme")
    assert r["by_status"]["200"] == 2
    assert r["by_status"]["400"] == 1


def test_query_limit_caps_events_returned():
    s = InMemoryAuditStore()
    for _ in range(200):
        s.record(_evt())
    r = s.query("acme", limit=50)
    assert r["total"] == 200
    assert len(r["events"]) == 50
