# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Celery integration for WANXIANG distributed mode (Stage 1+2).

Lazy-instantiated so single-process / asyncio mode never imports Celery.
Activated when ``WANXIANG_TASK_QUEUE=celery`` and consumed by both the API
process (which calls ``.delay()``) and the worker process
(``celery -A wanxiang.api.celery_app:get_celery_app worker``).

Env vars:
- ``WANXIANG_CELERY_BROKER`` — default ``redis://localhost:6379/0``
- ``WANXIANG_CELERY_BACKEND`` — default ``redis://localhost:6379/1``
- ``WANXIANG_CELERY_EAGER=1`` — turn on eager mode (tests only)
"""
from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_celery_app():
    """Construct (or return cached) Celery application.

    Importing Celery is deferred to this function so single-process mode
    does not pay the import cost.
    """
    from celery import Celery

    broker = os.environ.get("WANXIANG_CELERY_BROKER",
                            "redis://localhost:6379/0")
    backend = os.environ.get("WANXIANG_CELERY_BACKEND",
                             "redis://localhost:6379/1")
    app = Celery("wanxiang", broker=broker, backend=backend)
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        result_expires=24 * 3600,            # 24h
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        # Avoid pickling FastAPI/Pydantic objects across worker boundary.
        task_default_queue="wanxiang.default",
    )
    if os.environ.get("WANXIANG_CELERY_EAGER") == "1":
        app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
    # Import tasks so they self-register against this Celery app.
    from wanxiang.api import celery_tasks  # noqa: F401
    return app
