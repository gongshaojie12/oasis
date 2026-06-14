# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""真计费 (M3-10): UsageEvent + 按 mode 价位档累计.

spec §M7："按模拟次数/规模/能力档位（L1/L2/L3 三档=三价位）计量"。
"""
from __future__ import annotations

import math
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from urllib.parse import urlparse


# ----- cost model -----

_MODES = {"decision_only", "social", "platform"}


def derive_mode_label(*, rounds: int, platform: str | None) -> str:
    """spec §5.2: rounds=0 → decision_only; rounds>0 → social or platform."""
    if rounds <= 0:
        return "decision_only"
    if platform:
        return "platform"
    return "social"


def compute_cost_units(mode: str, n_agents: int, rounds: int) -> int:
    """spec §M7: 按 mode 价位档计 cost。

    decision_only: n
    social:        n * (rounds + 1)
    platform:      ceil(n * (rounds + 1) * 1.5)
    """
    if mode not in _MODES:
        raise ValueError(f"unknown mode: {mode!r}")
    if mode == "decision_only":
        return int(n_agents)
    base = n_agents * (rounds + 1)
    if mode == "social":
        return int(base)
    # platform
    return int(math.ceil(base * 1.5))


@dataclass
class UsageEvent:
    event_id: str        # "auto" → store assigns uuid4 hex
    tenant_id: str
    task_id: str | None
    mode: str
    n_agents: int
    rounds: int
    decision_kind: str
    cost_units: int
    status: str          # "done" | "failed"
    recorded_at: datetime

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "task_id": self.task_id,
            "mode": self.mode,
            "n_agents": self.n_agents,
            "rounds": self.rounds,
            "decision_kind": self.decision_kind,
            "cost_units": self.cost_units,
            "status": self.status,
            "recorded_at": self.recorded_at.isoformat(),
        }


# ----- aggregate helper (shared across backends) -----

def _aggregate(events: list[UsageEvent]) -> dict:
    total = sum(e.cost_units for e in events)
    by_mode: dict[str, int] = Counter()
    by_status: dict[str, int] = Counter()
    for e in events:
        by_mode[e.mode] += e.cost_units
        by_status[e.status] += 1
    # 按时间倒序，只列最近 100 条
    sorted_events = sorted(events, key=lambda e: e.recorded_at, reverse=True)
    return {
        "total_cost_units": total,
        "by_mode": dict(by_mode),
        "by_status": dict(by_status),
        "events": [e.to_dict() for e in sorted_events[:100]],
    }


def _month_window(year: int, month: int) -> tuple[datetime, datetime]:
    if not (1 <= month <= 12):
        raise ValueError(f"invalid month: {month}")
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


# ----- in-memory store -----

class InMemoryUsageStore:
    def __init__(self):
        self._events: list[UsageEvent] = []
        self._lock = Lock()

    def record(self, event: UsageEvent) -> UsageEvent:
        if event.event_id == "auto":
            event.event_id = uuid.uuid4().hex
        with self._lock:
            self._events.append(event)
        return event

    def query(self, tenant_id: str, start: datetime, end: datetime) -> dict:
        with self._lock:
            events = [e for e in self._events
                      if e.tenant_id == tenant_id and start <= e.recorded_at < end]
        result = _aggregate(events)
        result["period"] = {"start": start.isoformat(), "end": end.isoformat()}
        return result

    def monthly(self, tenant_id: str, year: int, month: int) -> dict:
        start, end = _month_window(year, month)
        return self.query(tenant_id, start, end)


# ----- factory (mirrors make_task_store) -----

def make_usage_store(dsn: str | None, *, eager_init: bool = True):
    if not dsn:
        return InMemoryUsageStore()
    parsed = urlparse(dsn)
    scheme = (parsed.scheme or "").lower()
    # Windows 裸路径 C:\foo\bar.db / C:/foo/bar.db 会被 urlparse 解析成
    # scheme='c'；这是路径不是 DSN，按 backwards-compat 走 SQLite。
    if len(scheme) == 1 and scheme.isalpha():
        scheme = ""
    if scheme in ("postgresql", "postgres"):
        from wanxiang.api.usage_store_pg import PgUsageStore
        return PgUsageStore(dsn, eager_init=eager_init)
    if scheme == "sqlite":
        path = parsed.path or dsn[len("sqlite:"):]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
        from wanxiang.api.usage_store_sqlite import SqliteUsageStore
        return SqliteUsageStore(path)
    if not scheme:
        from wanxiang.api.usage_store_sqlite import SqliteUsageStore
        return SqliteUsageStore(dsn)
    raise ValueError(f"unsupported usage store DSN scheme: {scheme!r}")


# ----- helper for routes -----

def build_usage_event(*, tenant_id, request, response_kind, status,
                       task_id=None):
    """Build a UsageEvent from a SimulateRequest + outcome."""
    mode = derive_mode_label(rounds=request.rounds,
                              platform=getattr(request, "platform", None))
    cost = compute_cost_units(mode, request.n, request.rounds)
    return UsageEvent(
        event_id="auto", tenant_id=tenant_id, task_id=task_id,
        mode=mode, n_agents=request.n, rounds=request.rounds,
        decision_kind=response_kind, cost_units=cost, status=status,
        recorded_at=datetime.now(timezone.utc))


__all__ = [
    "compute_cost_units", "derive_mode_label",
    "UsageEvent", "InMemoryUsageStore", "make_usage_store",
    "build_usage_event",
]
