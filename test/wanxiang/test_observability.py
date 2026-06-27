# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""Observability: request-id, structured logs, metrics endpoint."""
import json
import logging
import os
import re

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory
from wanxiang.api.observability import (JsonFormatter, Metrics,
                                          metrics as global_metrics)


def _stub_factory(cfg):
    async def call(messages):
        return '{"score": 7}'
    return call


@pytest.fixture
def client():
    # 每次新 app 实例 → 干净的 metrics
    global_metrics.reset()
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    return c


# ---- Metrics ----

def test_metrics_inc_basic():
    m = Metrics()
    m.inc("foo")
    m.inc("foo")
    snap = m.snapshot()
    assert snap["counters"]["foo"]["_total"] == 2


def test_metrics_inc_with_labels():
    m = Metrics()
    m.inc("auth.success", {"tenant_id": "demo"})
    m.inc("auth.success", {"tenant_id": "demo"})
    m.inc("auth.success", {"tenant_id": "acme"})
    snap = m.snapshot()
    assert snap["counters"]["auth.success"]["tenant_id=demo"] == 2
    assert snap["counters"]["auth.success"]["tenant_id=acme"] == 1


def test_metrics_observe_records_values():
    m = Metrics()
    m.observe("elapsed_ms", 100)
    m.observe("elapsed_ms", 200)
    m.observe("elapsed_ms", 300)
    snap = m.snapshot()
    h = snap["histograms"]["elapsed_ms"]["_all"]
    assert h["count"] == 3
    assert h["sum"] == 600
    assert h["min"] == 100
    assert h["max"] == 300


def test_metrics_reset_clears_everything():
    m = Metrics()
    m.inc("x")
    m.observe("y", 1)
    m.reset()
    snap = m.snapshot()
    assert snap["counters"] == {} and snap["histograms"] == {}


# ---- Request ID ----

def test_request_id_generated_when_missing(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    rid = res.headers.get("x-request-id")
    assert rid is not None
    # 看上去像 hex（uuid4 hex 32 字符）
    assert re.fullmatch(r"[0-9a-f]{32}", rid)


def test_request_id_passthrough_when_supplied(client):
    res = client.get("/healthz", headers={"X-Request-Id": "client-supplied-xyz"})
    assert res.headers.get("x-request-id") == "client-supplied-xyz"


# ---- /metrics endpoint ----

def test_metrics_endpoint_returns_json(client):
    res = client.get("/metrics")
    assert res.status_code == 200
    body = res.json()
    assert "counters" in body and "histograms" in body


def test_metrics_endpoint_unauthenticated(client):
    """/metrics 故意不挂 auth（scrape 友好）；任何调用方都能拿。"""
    res = client.get("/metrics")
    assert res.status_code == 200


def test_metrics_counts_simulate_requests(client):
    # 用 demo key 跑同步 simulate
    import os as _os
    project_root = _os.path.abspath(
        _os.path.join(_os.path.dirname(__file__), "..", ".."))
    distro = _os.path.join(project_root, "test", "wanxiang",
                            "fixtures", "cn_z_generation_v1.yaml")
    body = {"distribution_path": distro, "n": 5, "seed": 1,
            "scenario": {"material": "m", "question": "q", "kind": "rate"},
            "rounds": 0, "model": {"provider": "stub"}}
    r = client.post("/v1/simulate", headers={"X-API-Key": "demo-key"},
                    json=body)
    assert r.status_code == 200
    snap = client.get("/metrics").json()
    # 应能看到 simulate.requested 计数
    sim = snap["counters"].get("simulate.requested", {})
    assert any(v > 0 for v in sim.values()), snap


def test_auth_failure_counted(client):
    """无 key 调用 /v1/* → auth.failure +1。"""
    client.post("/v1/simulate", json={
        "distribution_path": "x", "n": 1, "seed": 1,
        "scenario": {"material": "m", "question": "q", "kind": "rate"},
        "rounds": 0, "model": {"provider": "stub"}})
    snap = client.get("/metrics").json()
    fail = snap["counters"].get("auth.failure", {})
    assert any(v > 0 for v in fail.values())


# ---- JSON log formatter ----

def test_json_formatter_emits_one_line_json():
    fmt = JsonFormatter()
    rec = logging.LogRecord(
        name="wanxiang.access", level=logging.INFO, pathname="x.py",
        lineno=1, msg="msg", args=None, exc_info=None)
    rec.request_id = "abc"
    rec.method = "GET"
    rec.path = "/healthz"
    rec.status = 200
    rec.duration_ms = 5
    line = fmt.format(rec)
    # 单行
    assert "\n" not in line
    data = json.loads(line)
    assert data["request_id"] == "abc"
    assert data["method"] == "GET"
    assert data["status"] == 200
    assert "ts" in data


def test_access_log_filters_healthz_and_metrics(client, caplog):
    """两条噪声路径不进入 access 日志。"""
    caplog.set_level(logging.INFO, logger="wanxiang.access")
    client.get("/healthz")
    client.get("/metrics")
    # 应没有这两个路径的记录
    msgs = [getattr(r, "path", None) for r in caplog.records
            if r.name == "wanxiang.access"]
    assert "/healthz" not in msgs
    assert "/metrics" not in msgs


def test_access_log_records_normal_request(client, caplog):
    caplog.set_level(logging.INFO, logger="wanxiang.access")
    client.post("/v1/simulate",
                headers={"X-API-Key": "demo-key"},
                json={"distribution_path": "/nope.yaml", "n": 1, "seed": 1,
                      "scenario": {"material": "m", "question": "q",
                                    "kind": "rate"},
                      "rounds": 0, "model": {"provider": "stub"}})
    paths = [getattr(r, "path", None) for r in caplog.records
             if r.name == "wanxiang.access"]
    assert "/v1/simulate" in paths
