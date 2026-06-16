# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P6: POST /v1/workspaces/{slug}/sandboxes/{id}/chat — NL → run sim flow."""
from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".."))
DIST = os.path.join(PROJECT_ROOT, "wanxiang", "datasources", "distributions",
                    "cn_z_generation_v1.yaml")


def _intent_factory(payload: dict):
    """Return a model_factory that returns a fixed JSON string."""
    txt = json.dumps(payload, ensure_ascii=False)

    def factory(cfg):
        async def call(messages):
            # If this is the intent parse system prompt, return the intent JSON;
            # otherwise (decision-time) return a numeric score JSON.
            sys_msg = next((m["content"] for m in messages
                             if m.get("role") == "system"), "")
            if "首席模拟官" in sys_msg or "Simulation Officer" in sys_msg:
                return txt
            # Fall through for decision LLM — return a rating
            return json.dumps({"score": 7})
        return call
    return factory


def _register(client, email, display="U"):
    r = client.post("/v1/auth/register", json={
        "email": email, "password": "Hello123!",
        "display_name": display, "locale": "zh",
    })
    assert r.status_code == 200, r.text
    return r.json()


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


def _setup(intent_payload):
    app = create_app()
    app.dependency_overrides[get_model_factory] = (
        lambda: _intent_factory(intent_payload))
    return TestClient(app)


def _make_sandbox(client, headers):
    ws = client.post("/v1/workspaces", headers=headers,
                      json={"name": "T", "type": "team"}).json()
    sb = client.post(f"/v1/workspaces/{ws['slug']}/sandboxes",
                      headers=headers,
                      json={"name": "Box", "population_size": 60,
                            "distribution_path": DIST}).json()
    return ws, sb


def test_chat_simulate_happy_path_writes_messages():
    intent = {
        "intent": "simulate",
        "fields": {"material": "新品 ¥6", "question": "0-10 评分",
                    "kind": "rate", "options": None, "n": 20,
                    "rounds": 0},
        "missing": [],
        "explanation": "识别为评分意图",
        "confidence": 0.9,
    }
    client = _setup(intent)
    reg = _register(client, "chatsim1@x.com", "C")
    h = _auth(reg["access_token"])
    ws, sb = _make_sandbox(client, h)
    r = client.post(
        f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}/chat",
        headers=h, json={"text": "测购买意愿"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_message"]["content"] == "测购买意愿"
    assert len(body["assistant_messages"]) == 2
    kinds = [m["kind"] for m in body["assistant_messages"]]
    assert kinds == ["intent_parsed", "report_card"]
    assert body["report"]["decision_kind"] == "rate"
    # Messages were persisted
    msgs = client.get(
        f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}/messages",
        headers=h).json()["messages"]
    roles = [m["role"] for m in msgs]
    assert roles == ["user", "assistant", "assistant"]


def test_chat_simulate_unknown_intent_requests_clarification():
    intent = {
        "intent": "unknown",
        "fields": {},
        "missing": ["material", "question"],
        "explanation": "需要补充材料和问题",
        "confidence": 0.2,
    }
    client = _setup(intent)
    reg = _register(client, "chatsim2@x.com", "C")
    h = _auth(reg["access_token"])
    ws, sb = _make_sandbox(client, h)
    r = client.post(
        f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}/chat",
        headers=h, json={"text": "天气如何"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("needs_clarification") is True
    assert "material" in body["missing"]
    assert len(body["assistant_messages"]) == 1
    assert body["assistant_messages"][0]["kind"] == "intent_parsed"


def test_chat_simulate_simulate_intent_with_missing_fields():
    intent = {
        "intent": "simulate",
        "fields": {"material": "", "question": "", "kind": None,
                    "options": None, "n": None, "rounds": 0},
        "missing": [],
        "explanation": "尚需补充字段",
        "confidence": 0.4,
    }
    client = _setup(intent)
    reg = _register(client, "chatsim3@x.com", "C")
    h = _auth(reg["access_token"])
    ws, sb = _make_sandbox(client, h)
    r = client.post(
        f"/v1/workspaces/{ws['slug']}/sandboxes/{sb['sandbox_id']}/chat",
        headers=h, json={"text": "随便"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("needs_clarification") is True
    assert len(body["assistant_messages"]) == 1


def test_chat_simulate_404_when_sandbox_missing():
    client = _setup({"intent": "unknown", "fields": {}, "missing": [],
                      "explanation": "", "confidence": 0})
    reg = _register(client, "chatsim4@x.com", "C")
    h = _auth(reg["access_token"])
    ws = client.post("/v1/workspaces", headers=h,
                      json={"name": "Lone", "type": "team"}).json()
    r = client.post(
        f"/v1/workspaces/{ws['slug']}/sandboxes/no-such-id/chat",
        headers=h, json={"text": "x"})
    assert r.status_code == 404


def test_chat_simulate_unauth_401():
    client = _setup({"intent": "unknown", "fields": {}, "missing": [],
                      "explanation": "", "confidence": 0})
    r = client.post("/v1/workspaces/no/sandboxes/x/chat",
                     json={"text": "y"})
    assert r.status_code == 401
