# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Celery task definitions for WANXIANG distributed mode (Stage 1+2).

Imported by :mod:`wanxiang.api.celery_app` so tasks register on the Celery
app at construction time.  This module runs in **both** the API process
and the Celery worker process, so it must not depend on FastAPI app state —
all state crosses the wire via task arguments + env-configured stores.
"""
from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime, timezone

from wanxiang.api.celery_app import get_celery_app


_celery = get_celery_app()


def _run_coro_in_fresh_loop(coro):
    """Drive an async coroutine to completion regardless of caller context.

    - In a normal Celery worker process there's no running loop, so
      ``asyncio.run`` works directly.
    - In eager mode the worker call happens inside whatever event loop
      the caller is running (e.g. an in-process FastAPI test using
      TestClient), so we offload to a worker thread that owns its own
      loop to avoid ``RuntimeError: asyncio.run() cannot be called from
      a running event loop``.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # A loop is already running on this thread — run in a fresh one.
    box: dict = {}

    def _worker():
        try:
            box["result"] = asyncio.run(coro)
        except BaseException as e:  # noqa: BLE001
            box["error"] = e

    th = threading.Thread(target=_worker, daemon=True)
    th.start()
    th.join()
    if "error" in box:
        raise box["error"]
    return box.get("result")


@_celery.task(name="wanxiang.run_simulation", bind=True)
def run_simulation_task(self, *, request_dict: dict, locale: str,
                        tenant_id: str, task_id: str) -> dict:
    """Run a single simulation inside a Celery worker.

    Args:
        request_dict: ``SimulateRequest.model_dump()`` payload
        locale: ``"zh"`` | ``"en"`` — controls report rendering language
        tenant_id: caller tenant (for usage accounting)
        task_id: pre-allocated TaskStore id; the worker updates its status
                 and writes the result back into the same store

    Returns:
        dict: serialized SimulateResponse on success, ``{"error": "..."}``
              on failure.  Celery itself stores this in the result backend.
    """
    # Local imports keep the worker boot light and avoid circular pulls.
    from wanxiang.api.deps import get_model_factory_for_worker
    from wanxiang.api.events import get_event_bus
    from wanxiang.api.routes.simulate import run_simulation_pipeline
    from wanxiang.api.schemas import SimulateRequest
    from wanxiang.api.tasks import TaskStatus, make_task_store
    from wanxiang.api.usage import build_usage_event, make_usage_store

    req = SimulateRequest(**request_dict)
    dsn = os.environ.get("WANXIANG_TASKS_DB")
    task_store = make_task_store(dsn)
    usage_store = make_usage_store(dsn)
    event_bus = get_event_bus()
    model_factory = get_model_factory_for_worker()

    started_at = datetime.now(timezone.utc)
    status_str = "failed"
    kind = req.scenario.kind
    try:
        task_store.update(task_id, status=TaskStatus.RUNNING,
                          started_at=started_at)
        try:
            event_bus.publish(task_id, "started", {
                "task_id": task_id, "n": req.n, "rounds": req.rounds,
                "kind": req.scenario.kind,
            })
        except Exception:  # noqa: BLE001
            pass

        result = _run_coro_in_fresh_loop(run_simulation_pipeline(
            req, model_factory, locale=locale))

        finished_at = datetime.now(timezone.utc)
        task_store.update(task_id, status=TaskStatus.DONE, result=result,
                          finished_at=finished_at)
        status_str = "done"
        kind = result.decision_kind
        try:
            event_bus.publish(task_id, "done", {
                "task_id": task_id,
                "n_valid": result.n_valid,
                "n_total": result.n_total,
            })
        except Exception:  # noqa: BLE001
            pass
        out = result.model_dump()
    except Exception as e:  # noqa: BLE001
        task_store.update(task_id, status=TaskStatus.FAILED, error=str(e),
                          finished_at=datetime.now(timezone.utc))
        try:
            event_bus.publish(task_id, "error", {
                "task_id": task_id, "error": str(e),
            })
        except Exception:  # noqa: BLE001
            pass
        out = {"error": str(e)}
    finally:
        try:
            event_bus.close(task_id)
        except Exception:  # noqa: BLE001
            pass

    # Usage accounting — fire-and-forget; never break the task on billing fail.
    try:
        evt = build_usage_event(
            tenant_id=tenant_id, request=req,
            response_kind=kind, status=status_str, task_id=task_id)
        usage_store.record(evt)
    except Exception:  # noqa: BLE001
        pass

    return out
