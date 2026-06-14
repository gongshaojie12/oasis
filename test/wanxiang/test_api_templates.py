# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""GET/POST /v1/templates endpoints."""
import pytest
from fastapi.testclient import TestClient

from wanxiang.api.app import create_app
from wanxiang.api.deps import get_model_factory


def _stub_factory(cfg):
    async def call(messages):
        return '{"score": 7}'
    return call


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_model_factory] = lambda: _stub_factory
    c = TestClient(app)
    c.headers.update({"X-API-Key": "demo-key"})
    return c


def test_list_templates_returns_array(client):
    res = client.get("/v1/templates")
    assert res.status_code == 200
    arr = res.json()
    assert isinstance(arr, list)
    ids = {t["id"] for t in arr}
    assert ids >= {"consumer_concept_test", "marketing_ad_ab_test",
                    "brand_sentiment_probe"}
    # 列表项应有 id / name / decision_kind / variables，不应有完整的 material_template
    for t in arr:
        assert "id" in t and "name" in t and "decision_kind" in t
        assert "variables" in t


def test_get_single_template_returns_full(client):
    res = client.get("/v1/templates/marketing_ad_ab_test")
    assert res.status_code == 200
    t = res.json()
    assert t["id"] == "marketing_ad_ab_test"
    assert "material_template" in t  # 完整版要有模板原文
    assert "question_template" in t


def test_get_unknown_template_returns_404(client):
    res = client.get("/v1/templates/totally_nope")
    assert res.status_code == 404


def test_instantiate_endpoint_returns_scenario_payload(client):
    # 先拿模板看需要哪些变量
    t = client.get("/v1/templates/marketing_ad_ab_test").json()
    values = {v["name"]: "demo" for v in t["variables"]}
    res = client.post(f"/v1/templates/{t['id']}/instantiate",
                      json={"values": values, "options": None})
    assert res.status_code == 200
    sc = res.json()
    assert sc["kind"] == "rate"
    assert "material" in sc and "question" in sc
    # 这个 payload 应能直接喂给 /v1/simulate（schema 兼容）
    from wanxiang.api.schemas import ScenarioPayload
    ScenarioPayload(**sc)  # 不抛 = 兼容


def test_instantiate_missing_required_returns_422(client):
    res = client.post("/v1/templates/marketing_ad_ab_test/instantiate",
                      json={"values": {}, "options": None})
    # 业务校验失败应返 4xx（422 或 400 都可接受）
    assert res.status_code in (400, 422)


def test_templates_endpoints_require_auth():
    app = create_app()
    c = TestClient(app)
    assert c.get("/v1/templates").status_code == 401
    assert c.get("/v1/templates/anything").status_code == 401
    assert c.post("/v1/templates/anything/instantiate",
                  json={"values": {}}).status_code == 401
