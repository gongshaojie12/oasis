# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""SqliteTaskStore round-trip + persistence + tenant isolation."""
import os
from datetime import datetime, timezone

import pytest

from wanxiang.api.schemas import (ScenarioPayload, ModelConfig,
                                    SimulateRequest, SimulateResponse)
from wanxiang.api.task_store_sqlite import SqliteTaskStore
from wanxiang.api.tasks import TaskStatus


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


def test_create_and_get_roundtrip(tmp_path):
    s = SqliteTaskStore(str(tmp_path / "t.db"))
    t = s.create("acme", _req())
    fetched = s.get("acme", t.id)
    assert fetched is not None
    assert fetched.id == t.id
    assert fetched.tenant_id == "acme"
    assert fetched.status is TaskStatus.PENDING
    assert fetched.request.n == 10
    assert fetched.result is None


def test_update_persists_status_and_result(tmp_path):
    s = SqliteTaskStore(str(tmp_path / "t.db"))
    t = s.create("acme", _req())
    s.update(t.id, status=TaskStatus.RUNNING,
             started_at=datetime.now(timezone.utc))
    s.update(t.id, status=TaskStatus.DONE,
             result=_resp(),
             finished_at=datetime.now(timezone.utc))
    got = s.get("acme", t.id)
    assert got.status is TaskStatus.DONE
    assert got.started_at is not None
    assert got.finished_at is not None
    assert got.result.n_valid == 10
    assert got.error is None


def test_persistence_across_reopen(tmp_path):
    path = str(tmp_path / "t.db")
    s1 = SqliteTaskStore(path)
    t = s1.create("acme", _req())
    s1.update(t.id, status=TaskStatus.DONE, result=_resp())
    # 重新打开
    s2 = SqliteTaskStore(path)
    got = s2.get("acme", t.id)
    assert got is not None
    assert got.status is TaskStatus.DONE
    assert got.result.n_valid == 10


def test_tenant_isolation_get(tmp_path):
    s = SqliteTaskStore(str(tmp_path / "t.db"))
    t = s.create("acme", _req())
    # 其他 tenant 不应能拿到
    assert s.get("other", t.id) is None
    assert s.get("acme", t.id) is not None


def test_get_unknown_id_returns_none(tmp_path):
    s = SqliteTaskStore(str(tmp_path / "t.db"))
    assert s.get("acme", "nonexistent") is None


def test_list_for_tenant_returns_only_own_tasks(tmp_path):
    s = SqliteTaskStore(str(tmp_path / "t.db"))
    a1 = s.create("acme", _req())
    a2 = s.create("acme", _req())
    b1 = s.create("beta", _req())
    a_list = s.list_for_tenant("acme")
    b_list = s.list_for_tenant("beta")
    a_ids = {t.id for t in a_list}
    b_ids = {t.id for t in b_list}
    assert a_ids == {a1.id, a2.id}
    assert b_ids == {b1.id}


def test_list_for_tenant_newest_first(tmp_path):
    import time
    s = SqliteTaskStore(str(tmp_path / "t.db"))
    t1 = s.create("acme", _req())
    time.sleep(0.01)
    t2 = s.create("acme", _req())
    time.sleep(0.01)
    t3 = s.create("acme", _req())
    lst = s.list_for_tenant("acme")
    assert [t.id for t in lst] == [t3.id, t2.id, t1.id]


def test_list_for_tenant_pagination(tmp_path):
    s = SqliteTaskStore(str(tmp_path / "t.db"))
    ids = [s.create("acme", _req()).id for _ in range(5)]
    page1 = s.list_for_tenant("acme", limit=2, offset=0)
    page2 = s.list_for_tenant("acme", limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    # 无重复
    assert set(t.id for t in page1).isdisjoint(t.id for t in page2)


def test_in_memory_store_also_has_list_for_tenant():
    """parity: in-memory TaskStore 也应提供 list_for_tenant。"""
    from wanxiang.api.tasks import TaskStore
    s = TaskStore()
    t1 = s.create("acme", _req())
    t2 = s.create("acme", _req())
    s.create("beta", _req())
    lst = s.list_for_tenant("acme")
    assert {t.id for t in lst} == {t1.id, t2.id}
