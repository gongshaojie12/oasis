# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""可观测性：结构化访问日志 / 内存指标 / 请求 ID 中间件（spec §M7 运维基础）。"""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# ----------------- Metrics -----------------

_QUIET_PATHS = {"/healthz", "/metrics"}


class Metrics:
    """In-memory counters + histograms（MVP；Prometheus 集成是后续工作）。

    counters[name][label_key] = int
    histograms[name][label_key] = {count, sum, min, max}
    label_key: 'k1=v1|k2=v2'（按 key 排序）或 '_total'（无 labels）/ '_all'（histogram）
    """

    def __init__(self):
        self._lock = Lock()
        self._counters: dict[str, dict[str, int]] = {}
        self._hist: dict[str, dict[str, dict[str, float]]] = {}

    @staticmethod
    def _label_key(labels: dict[str, Any] | None) -> str:
        if not labels:
            return "_total"
        return "|".join(f"{k}={labels[k]}" for k in sorted(labels.keys()))

    def inc(self, name: str, labels: dict[str, Any] | None = None,
            n: int = 1) -> None:
        key = self._label_key(labels)
        with self._lock:
            bucket = self._counters.setdefault(name, {})
            bucket[key] = bucket.get(key, 0) + n

    def observe(self, name: str, value: float,
                labels: dict[str, Any] | None = None) -> None:
        key = self._label_key(labels) if labels else "_all"
        with self._lock:
            bucket = self._hist.setdefault(name, {})
            entry = bucket.setdefault(
                key, {"count": 0, "sum": 0.0, "min": value, "max": value})
            entry["count"] += 1
            entry["sum"] += value
            entry["min"] = min(entry["min"], value)
            entry["max"] = max(entry["max"], value)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            # 深拷贝避免外部修改
            return {
                "counters": {n: dict(b) for n, b in self._counters.items()},
                "histograms": {n: {k: dict(v) for k, v in b.items()}
                               for n, b in self._hist.items()},
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._hist.clear()


metrics = Metrics()


# ----------------- JsonFormatter -----------------

class JsonFormatter(logging.Formatter):
    """把 LogRecord（含 extra 字段）格式化为一行 JSON。"""

    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # 透传所有非标准字段
        std_fields = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "asctime", "taskName",
        }
        for k, v in record.__dict__.items():
            if k in std_fields:
                continue
            data[k] = v
        return json.dumps(data, ensure_ascii=False)


# ----------------- Middleware -----------------

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["x-request-id"] = rid
        return response


_access_log = logging.getLogger("wanxiang.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        start = time.monotonic()
        response = await call_next(request)
        # 噪声路径不进 access log
        if path in _QUIET_PATHS:
            return response
        duration_ms = int((time.monotonic() - start) * 1000)
        tenant_id = getattr(request.state, "tenant_id", None)
        rid = getattr(request.state, "request_id", None)
        client_ip = request.client.host if request.client else None
        _access_log.info(
            "request",
            extra={
                "request_id": rid,
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "tenant_id": tenant_id,
                "client_ip": client_ip,
            },
        )
        return response


def configure_logging() -> None:
    """根据 WANXIANG_LOG_JSON 切换 access log 输出格式。

    默认（未设或非 '1'）：人类可读 text；'1' 时切换为 JSON 一行式。
    text 模式下不动 handler，让 pytest caplog 通过 root 传播能正常捕获。
    """
    import os as _os
    if _os.environ.get("WANXIANG_LOG_JSON") != "1":
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    _access_log.handlers = [handler]
    _access_log.setLevel(logging.INFO)
    _access_log.propagate = False
