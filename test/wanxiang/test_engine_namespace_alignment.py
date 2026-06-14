# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""spec §3.1: engine/ 应包含 7 个模块（channel, agent_runtime, graph,
trace, orchestrator, model_provider, platform_base）。"""
import importlib

import pytest


@pytest.mark.parametrize("modname", [
    "channel", "agent_runtime", "graph", "trace",
    "orchestrator", "model_provider", "platform_base",
])
def test_engine_module_importable(modname):
    m = importlib.import_module(f"engine.{modname}")
    assert m is not None


def test_engine_model_provider_re_exports():
    from engine.model_provider import (
        ModelCall, wrap_camel_model, make_stub_call, make_deepseek_call)
    # 同源
    from wanxiang.models.adapter import make_stub_call as src
    assert make_stub_call is src


def test_engine_graph_re_exports():
    from engine.graph import FriendGraph, AgentGraph, generate_small_world
    from wanxiang.social_graph.graph import FriendGraph as src
    assert FriendGraph is src
    assert AgentGraph is FriendGraph  # spec uses AgentGraph name


def test_engine_agent_runtime_re_exports_three_runners():
    from engine.agent_runtime import (DecisionRunner, BatchRunner,
                                        SocialRoundsRunner)
    assert DecisionRunner and BatchRunner and SocialRoundsRunner


def test_engine_platform_base_has_plugin_protocol():
    from engine.platform_base import PlatformPlugin, PlatformDialect
    assert PlatformPlugin and PlatformDialect
