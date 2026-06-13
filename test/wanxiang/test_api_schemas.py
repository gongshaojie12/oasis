# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import pytest

from wanxiang.api.schemas import (ScenarioPayload, SimulateRequest,
                                    SimulateResponse, ModelConfig)


def test_simulate_request_choose_validates_options_required():
    with pytest.raises(Exception):
        SimulateRequest(
            distribution_path="x.yaml", n=100, seed=42,
            scenario=ScenarioPayload(
                material="m", question="q", kind="choose",
                options=None),
            rounds=0,
            model=ModelConfig(provider="stub"),
        )


def test_simulate_request_rate_no_options_ok():
    req = SimulateRequest(
        distribution_path="x.yaml", n=100, seed=42,
        scenario=ScenarioPayload(material="m", question="q", kind="rate"),
        rounds=0,
        model=ModelConfig(provider="stub"),
    )
    assert req.scenario.options is None
    assert req.scenario.kind == "rate"


def test_simulate_request_rejects_negative_n():
    with pytest.raises(Exception):
        SimulateRequest(
            distribution_path="x.yaml", n=-1, seed=42,
            scenario=ScenarioPayload(material="m", question="q", kind="rate"),
            rounds=0, model=ModelConfig(provider="stub"))


def test_simulate_request_rejects_negative_rounds():
    with pytest.raises(Exception):
        SimulateRequest(
            distribution_path="x.yaml", n=100, seed=42,
            scenario=ScenarioPayload(material="m", question="q", kind="rate"),
            rounds=-1, model=ModelConfig(provider="stub"))


def test_model_config_deepseek_requires_api_key():
    with pytest.raises(Exception):
        ModelConfig(provider="deepseek")
    cfg = ModelConfig(provider="deepseek", api_key="sk-xxx")
    assert cfg.api_key == "sk-xxx"


def test_simulate_response_basic_shape():
    resp = SimulateResponse(
        decision_kind="rate", n_total=10, n_valid=10,
        error_count=0, error_rate=0.0,
        report={"foo": "bar"},
        markdown="# hi",
        elapsed_ms=123,
    )
    assert resp.decision_kind == "rate"
    assert resp.markdown.startswith("#")
