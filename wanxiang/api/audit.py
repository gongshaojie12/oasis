# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""审计日志 (M3-13).

记录每次"重要操作"的结构化事件，便于租户后续审计与合规审查。

写入时机：
- 每次成功的写操作（POST/PUT/DELETE）由中间件记录一条 api_call 事件
- 每次模拟成功/失败 由 _run_task / simulate 显式补一条 sim_completed/sim_failed

读取：
- GET /v1/audit/events  — 当前租户的审计记录（带时间窗 + action 过滤 + 分页）
"""
from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from urllib.parse import urlparse


@dataclass
class AuditEvent:
    event_id: str
    tenant_id: str
    action: str             # e.g. "api_call", "sim_completed", "sim_failed"
    resource_type: str      # e.g. "simulation", "report", "auth"
    resource_id: str | None  # e.g. task_id
    request_id: str | None  # for cross-correlation with access log
    method: str | None      # POST/GET/...
    path: str | None        # /v1/simulate
    status: int | None      # HTTP status
    ip: str | None
    user_agent: str | None
    detail: dict | None     # arbitrary structured fields
    recorded_at: datetime

    def to_dict(self) -> dict:
        d = asdict(self)
        d["recorded_at"] = self.recorded_at.isoformat()
        return d


# ----- aggregate helper (shared across backends) -----

def _aggregate(events: list[AuditEvent], *, limit: int) -> dict:
    by_action: dict[str, int] = Counter()
    by_status: dict[str, int] = Counter()
    for e in events:
        by_action[e.action] += 1
        if e.status is not None:
            by_status[str(e.status)] += 1
    sorted_events = sorted(events, key=lambda e: e.recorded_at, reverse=True)
    return {
        "total": len(events),
        "by_action": dict(by_action),
        "by_status": dict(by_status),
        "events": [e.to_dict() for e in sorted_events[:limit]],
    }


# ----- in-memory store -----

class InMemoryAuditStore:
    def __init__(self):
        self._events: list[AuditEvent] = []
        self._lock = Lock()

    def record(self, event: AuditEvent) -> AuditEvent:
        if event.event_id == "auto":
            event.event_id = uuid.uuid4().hex
        with self._lock:
            self._events.append(event)
        return event

    def query(self, tenant_id: str, *,
              start: datetime | None = None,
              end: datetime | None = None,
              action: str | None = None,
              limit: int = 100) -> dict:
        with self._lock:
            events = [e for e in self._events
                      if e.tenant_id == tenant_id]
        if start is not None:
            events = [e for e in events if e.recorded_at >= start]
        if end is not None:
            events = [e for e in events if e.recorded_at < end]
        if action is not None:
            events = [e for e in events if e.action == action]
        return _aggregate(events, limit=limit)


# ----- factory (mirrors make_usage_store) -----

def make_audit_store(dsn: str | None, *, eager_init: bool = True):
    if not dsn:
        return InMemoryAuditStore()
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()
    # Windows 裸路径 C:\foo\bar.db / C:/foo/bar.db 会被 urlparse 解析成
    # scheme='c'；这是路径不是 DSN，按 backwards-compat 走 SQLite。
    if len(scheme) == 1 and scheme.isalpha():
        scheme = ""
    if scheme in ("postgresql", "postgres"):
        from wanxiang.api.audit_store_pg import PgAuditStore
        return PgAuditStore(dsn, eager_init=eager_init)
    if scheme == "sqlite":
        path = parsed.path or dsn[len("sqlite:"):]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        from wanxiang.api.audit_store_sqlite import SqliteAuditStore
        return SqliteAuditStore(path)
    if not scheme:
        from wanxiang.api.audit_store_sqlite import SqliteAuditStore
        return SqliteAuditStore(dsn)
    raise ValueError(f"unsupported audit store DSN scheme: {scheme!r}")


# ----- helpers -----

def build_api_call_event(*, tenant_id, request, response_status,
                          request_id=None, resource_type="api",
                          resource_id=None, detail=None):
    return AuditEvent(
        event_id="auto", tenant_id=tenant_id,
        action="api_call", resource_type=resource_type,
        resource_id=resource_id, request_id=request_id,
        method=request.method, path=str(request.url.path),
        status=response_status,
        ip=(request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        detail=detail,
        recorded_at=datetime.now(timezone.utc))


def build_sim_event(*, tenant_id, action, task_id=None,
                     request_id=None, detail=None, status_code=None):
    """action: 'sim_started' | 'sim_completed' | 'sim_failed'."""
    return AuditEvent(
        event_id="auto", tenant_id=tenant_id, action=action,
        resource_type="simulation", resource_id=task_id,
        request_id=request_id, method=None, path=None,
        status=status_code, ip=None, user_agent=None,
        detail=detail,
        recorded_at=datetime.now(timezone.utc))


__all__ = [
    "AuditEvent", "InMemoryAuditStore", "make_audit_store",
    "build_api_call_event", "build_sim_event",
]
