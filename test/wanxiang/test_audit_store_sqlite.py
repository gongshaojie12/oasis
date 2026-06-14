# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteAuditStore (M3-13)."""
from datetime import datetime, timezone

from wanxiang.api.audit import AuditEvent
from wanxiang.api.audit_store_sqlite import SqliteAuditStore


def _evt(tenant="acme", action="api_call"):
    return AuditEvent(
        event_id="auto", tenant_id=tenant, action=action,
        resource_type="api", resource_id=None, request_id="rid",
        method="POST", path="/x", status=200,
        ip="127.0.0.1", user_agent="curl", detail={"key": "v"},
        recorded_at=datetime.now(timezone.utc))


def test_sqlite_roundtrip(tmp_path):
    s = SqliteAuditStore(str(tmp_path / "a.db"))
    s.record(_evt())
    s.record(_evt())
    assert s.query("acme")["total"] == 2


def test_sqlite_persistence(tmp_path):
    p = str(tmp_path / "a.db")
    SqliteAuditStore(p).record(_evt())
    s2 = SqliteAuditStore(p)
    assert s2.query("acme")["total"] == 1


def test_sqlite_tenant_isolation(tmp_path):
    s = SqliteAuditStore(str(tmp_path / "a.db"))
    s.record(_evt(tenant="acme"))
    s.record(_evt(tenant="other"))
    assert s.query("acme")["total"] == 1


def test_sqlite_action_filter(tmp_path):
    s = SqliteAuditStore(str(tmp_path / "a.db"))
    s.record(_evt(action="api_call"))
    s.record(_evt(action="sim_failed"))
    assert s.query("acme", action="sim_failed")["total"] == 1


def test_sqlite_detail_json_roundtrip(tmp_path):
    s = SqliteAuditStore(str(tmp_path / "a.db"))
    s.record(_evt())
    r = s.query("acme")
    assert r["events"][0]["detail"] == {"key": "v"}
