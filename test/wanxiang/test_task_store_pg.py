# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""PgTaskStore tests — skipped unless WANXIANG_TEST_PG_DSN is set.

CI / dev that wants to verify against a real Postgres:
    export WANXIANG_TEST_PG_DSN="postgresql://postgres:postgres@localhost:5432/wanxiang_test"
本沙箱无 PG，这组测试默认 skip；但 make_task_store 的派发逻辑由
test_task_store_factory.py 覆盖（无需真 PG）。
"""
import os
from datetime import datetime, timezone

import pytest

from wanxiang.api.schemas import (ModelConfig, ScenarioPayload,
                                    SimulateRequest, SimulateResponse)
from wanxiang.api.tasks import TaskStatus

_PG_DSN = os.environ.get("WANXIANG_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not _PG_DSN, reason="no WANXIANG_TEST_PG_DSN")


def _req():
    return SimulateRequest(
        distribution_path="x.yaml", n=10, seed=1,
        scenario=ScenarioPayload(material="m", question="q", kind="rate"),
        rounds=0, model=ModelConfig(provider="stub"))


def _resp():
    return SimulateResponse(
        decision_kind="rate", n_total=10, n_valid=10,
        error_count=0, error_rate=0.0,
        report={"foo": "bar"}, markdown="# hi", elapsed_ms=42)


@pytest.fixture
def store():
    from wanxiang.api.task_store_pg import PgTaskStore
    s = PgTaskStore(_PG_DSN)
    # 清表（限定 test 库专用）
    with s._connect() as conn:  # type: ignore[attr-defined]
        conn.execute("TRUNCATE simulation_tasks")
    return s


def test_pg_create_and_get_roundtrip(store):
    t = store.create("acme", _req())
    got = store.get("acme", t.id)
    assert got is not None
    assert got.status is TaskStatus.PENDING
    assert got.request.n == 10


def test_pg_update_status_and_result(store):
    t = store.create("acme", _req())
    store.update(t.id, status=TaskStatus.RUNNING,
                 started_at=datetime.now(timezone.utc))
    store.update(t.id, status=TaskStatus.DONE, result=_resp(),
                 finished_at=datetime.now(timezone.utc))
    got = store.get("acme", t.id)
    assert got.status is TaskStatus.DONE
    assert got.result.n_valid == 10


def test_pg_tenant_isolation(store):
    t = store.create("acme", _req())
    assert store.get("other", t.id) is None


def test_pg_list_for_tenant_newest_first(store):
    import time
    a = store.create("acme", _req())
    time.sleep(0.01)
    b = store.create("acme", _req())
    lst = store.list_for_tenant("acme")
    assert [x.id for x in lst][:2] == [b.id, a.id]
