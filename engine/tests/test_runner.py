import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.config import Settings
from engine.queue import TaskInfo, TaskStatus
from engine.reporter import ProgressReporter
from engine.runner import SimulationRunner


def _make_settings(**overrides):
    defaults = {
        "_env_file": None,
        "deepseek_api_key": "sk-test",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _make_reporter():
    client = MagicMock()
    client.send_progress = AsyncMock(return_value=True)
    client.send_complete = AsyncMock(return_value=True)
    client.send_error = AsyncMock(return_value=True)
    return ProgressReporter(callback_client=client)


class TestSimulationRunner:
    @pytest.mark.asyncio
    async def test_run_with_mocked_oasis(self):
        """Full run with mocked oasis module to verify the runner flow."""
        settings = _make_settings()
        reporter = _make_reporter()

        # Mock the entire oasis module
        mock_env = AsyncMock()
        mock_env.reset = AsyncMock()
        mock_env.step = AsyncMock()
        mock_env.close = AsyncMock()

        mock_agent = MagicMock()
        mock_agent.social_agent_id = 0
        mock_agent_graph = MagicMock()
        mock_agent_graph.get_agents.return_value = [(0, mock_agent)]
        mock_agent_graph.get_agent.return_value = mock_agent
        mock_agent_graph.get_num_nodes.return_value = 1
        mock_env.agent_graph = mock_agent_graph

        mock_make = MagicMock(return_value=mock_env)
        mock_create_model = MagicMock(return_value=MagicMock())

        task_info = TaskInfo(task_id="test123", params={})

        with patch("engine.runner.create_model", mock_create_model), \
             patch.dict("sys.modules", {
                 "oasis": MagicMock(
                     make=mock_make,
                     ActionType=MagicMock(
                         get_default_reddit_actions=MagicMock(return_value=[]),
                         CREATE_POST=MagicMock(),
                     ),
                     AgentGraph=MagicMock,
                     DefaultPlatformType=MagicMock(REDDIT="reddit", TWITTER="twitter"),
                     LLMAction=MagicMock,
                     ManualAction=MagicMock,
                     SocialAgent=MagicMock,
                     UserInfo=MagicMock,
                     generate_reddit_agent_graph=AsyncMock(),
                 ),
             }):
            runner = SimulationRunner(settings=settings, reporter=reporter)
            result = await runner.run(task_info, {
                "num_agents": 1,
                "num_steps": 2,
                "platform_type": "reddit",
            })

        assert result["num_steps_completed"] == 2
        assert result["platform_type"] == "reddit"
        assert "db_path" in result
        assert mock_env.reset.called
        assert mock_env.close.called
        # step called once per simulation step
        assert mock_env.step.call_count == 2
        # Reporter progress calls: setup + 2 steps + cleanup = 4
        assert reporter._client.send_progress.call_count == 4
        assert reporter._client.send_complete.call_count == 1

    @pytest.mark.asyncio
    async def test_run_with_seed_content(self):
        """Verify seed content creates a manual action on step 1."""
        settings = _make_settings()
        reporter = _make_reporter()

        mock_env = AsyncMock()
        mock_env.reset = AsyncMock()
        mock_env.step = AsyncMock()
        mock_env.close = AsyncMock()

        mock_agent_0 = MagicMock()
        mock_agent_0.social_agent_id = 0
        mock_agent_1 = MagicMock()
        mock_agent_1.social_agent_id = 1
        mock_agent_graph = MagicMock()
        mock_agent_graph.get_agents.return_value = [
            (0, mock_agent_0),
            (1, mock_agent_1),
        ]
        mock_agent_graph.get_agent.return_value = mock_agent_0
        mock_agent_graph.get_num_nodes.return_value = 2
        mock_env.agent_graph = mock_agent_graph

        mock_make = MagicMock(return_value=mock_env)
        mock_create_model = MagicMock(return_value=MagicMock())

        task_info = TaskInfo(task_id="seed-test", params={})

        mock_manual_action_cls = MagicMock()
        mock_llm_action_cls = MagicMock()

        with patch("engine.runner.create_model", mock_create_model), \
             patch.dict("sys.modules", {
                 "oasis": MagicMock(
                     make=mock_make,
                     ActionType=MagicMock(
                         get_default_reddit_actions=MagicMock(return_value=[]),
                         CREATE_POST=MagicMock(),
                     ),
                     AgentGraph=MagicMock,
                     DefaultPlatformType=MagicMock(REDDIT="reddit", TWITTER="twitter"),
                     LLMAction=mock_llm_action_cls,
                     ManualAction=mock_manual_action_cls,
                     SocialAgent=MagicMock,
                     UserInfo=MagicMock,
                     generate_reddit_agent_graph=AsyncMock(),
                 ),
             }):
            runner = SimulationRunner(settings=settings, reporter=reporter)
            result = await runner.run(task_info, {
                "num_agents": 2,
                "num_steps": 2,
                "seed_content": "Hello OASIS!",
            })

        # ManualAction should have been instantiated for the seed post
        mock_manual_action_cls.assert_called()
        assert result["num_steps_completed"] == 2
