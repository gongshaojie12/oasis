# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: enforce_balance settings flag + pre-flight 402 + post-deduct flow."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "test", "wanxiang", "fixtures",
                    "cn_z_generation_v1.yaml")


def _smart_stub_factory(cfg):
    async def call(messages):
        user = messages[-1]["content"]
        if "score" in user.lower():
            return '{"score": 7}'
        if "option" in user.lower() or "选项" in user:
            return '{"option": "青提"}'
        if "polarity" in user.lower():
            return '{"polarity": 0.5}'
        if "probability" in user.lower():
            return '{"probability": 0.6}'
        if "price" in user.lower():
            return '{"price": 8}'
        return '{"score": 5}'
    return call


def _client(enforce_balance: bool):
    app = create_app()
    # Toggle settings flag for this app instance
    app.state.settings.enforce_balance = enforce_balance
    app.dependency_overrides[get_model_factory] = lambda: _smart_stub_factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c


def _simulate_body(n=10):
    return {
        "distribution_path": DIST, "n": n, "seed": 1,
        "scenario": {"material": "m", "question": "0-10 评分",
                      "kind": "rate"},
        "rounds": 0, "concurrency": 4,
        "model": {"provider": "stub"},
    }


def test_enforce_false_default_low_balance_still_succeeds():
    client = _client(enforce_balance=False)
    # Drain demo balance manually
    ws_store = client.app.state.workspace_store
    ws = ws_store.get_by_slug("demo")
    ws_store.update_workspace(ws.workspace_id, balance_cost_units=1)
    r = client.post("/v1/simulate", json=_simulate_body(n=10))
    assert r.status_code == 200, r.text
    # Balance went negative; tx still recorded (kind="usage")
    refreshed = ws_store.get_workspace(ws.workspace_id)
    assert refreshed.balance_cost_units < 1
    tx_store = client.app.state.transaction_store
    txs = tx_store.list_for_workspace(ws.workspace_id)
    assert any(t.kind == "usage" for t in txs)


def test_enforce_true_with_sufficient_balance_succeeds_and_deducts():
    client = _client(enforce_balance=True)
    ws_store = client.app.state.workspace_store
    ws = ws_store.get_by_slug("demo")
    ws_store.update_workspace(ws.workspace_id, balance_cost_units=10_000)
    before = ws_store.get_workspace(ws.workspace_id).balance_cost_units
    r = client.post("/v1/simulate", json=_simulate_body(n=10))
    assert r.status_code == 200, r.text
    after = ws_store.get_workspace(ws.workspace_id).balance_cost_units
    # n=10, rounds=0 → mode=decision_only → cost=10
    assert before - after == 10


def test_enforce_true_with_insufficient_returns_402(monkeypatch):
    client = _client(enforce_balance=True)
    ws_store = client.app.state.workspace_store
    ws = ws_store.get_by_slug("demo")
    ws_store.update_workspace(ws.workspace_id, balance_cost_units=1)
    r = client.post("/v1/simulate", json=_simulate_body(n=50))
    assert r.status_code == 402, r.text
    detail = r.json()["detail"]
    # i18n default zh
    assert "余额不足" in detail or "Insufficient balance" in detail


def test_enforce_true_insufficient_en_locale_returns_english_detail():
    client = _client(enforce_balance=True)
    ws_store = client.app.state.workspace_store
    ws = ws_store.get_by_slug("demo")
    ws_store.update_workspace(ws.workspace_id, balance_cost_units=1)
    body = _simulate_body(n=50)
    body["locale"] = "en"
    r = client.post("/v1/simulate", json=body,
                     headers={"Accept-Language": "en"})
    assert r.status_code == 402, r.text
    assert "Insufficient balance" in r.json()["detail"]


def test_sweep_enforce_check_blocks_when_total_exceeds_balance():
    client = _client(enforce_balance=True)
    ws_store = client.app.state.workspace_store
    ws = ws_store.get_by_slug("demo")
    ws_store.update_workspace(ws.workspace_id, balance_cost_units=10)
    body = {
        "distribution_path": DIST, "n": 5, "seed": 1,
        "scenario": {"material": "m {copy}", "question": "0-10 评分",
                      "kind": "rate"},
        "rounds": 0,
        "model": {"provider": "stub"},
        "variable_grid": {"copy": ["a", "b", "c", "d", "e", "f"]},
    }
    r = client.post("/v1/simulations/sweep", json=body)
    # 6 combos × 5 units = 30 > balance 10 → 402
    assert r.status_code == 402, r.text
