from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import Any, Optional

from engine.callback import CallbackClient
from engine.config import Settings
from engine.llm.provider import LLMProviderRegistry, create_model
from engine.llm.tiered import AgentTier, TieredModelAssigner
from engine.queue import TaskInfo
from engine.reporter import ProgressReporter

logger = logging.getLogger("engine.runner")


class SimulationRunner:
    """Wraps OASIS core to run a full simulation lifecycle.

    Responsibilities:
        1. Build an AgentGraph with tiered LLM models.
        2. Create an OasisEnv and reset it.
        3. Execute N simulation steps, reporting progress per step.
        4. Close the environment and return results.
    """

    def __init__(
        self,
        settings: Settings,
        reporter: ProgressReporter,
        registry: Optional[LLMProviderRegistry] = None,
    ) -> None:
        self._settings = settings
        self._reporter = reporter
        self._registry = registry or LLMProviderRegistry()

    async def run(self, task_info: TaskInfo, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a simulation task end-to-end.

        Expected params:
            platform_type: str  - "twitter" or "reddit" (default "reddit")
            num_steps: int      - number of simulation steps (default 5)
            num_agents: int     - number of agents (default 10)
            agent_profiles: list[dict] | None - custom agent profiles
            profile_path: str | None - path to agent profile JSON/CSV file
            seed_content: str | None - initial post content for step 0
            available_actions: list[str] | None - action types to enable
            tier_config: dict | None - override tier percentages/models
            llm_provider: str | None - override default LLM provider
            llm_model: str | None - override default LLM model

        Returns:
            dict with db_path, num_steps_completed, and agent summary.
        """
        # Lazy import to avoid importing oasis at module level (so tests
        # that mock oasis can control the import).
        import oasis
        from oasis import (
            ActionType,
            AgentGraph,
            DefaultPlatformType,
            LLMAction,
            ManualAction,
            SocialAgent,
            UserInfo,
            generate_reddit_agent_graph,
        )

        platform_type_str = params.get("platform_type", "reddit")
        num_steps = params.get("num_steps", 5)
        num_agents = params.get("num_agents", 10)
        profile_path = params.get("profile_path")
        agent_profiles = params.get("agent_profiles")
        seed_content = params.get("seed_content")
        llm_provider = params.get("llm_provider", self._settings.default_llm_provider)
        llm_model = params.get("llm_model", self._settings.default_llm_model)

        # Resolve platform type
        if platform_type_str == "twitter":
            platform_enum = DefaultPlatformType.TWITTER
            recsys_type = "twitter"
            default_actions = ActionType.get_default_twitter_actions()
        else:
            platform_enum = DefaultPlatformType.REDDIT
            recsys_type = "reddit"
            default_actions = ActionType.get_default_reddit_actions()

        # Resolve available actions
        action_names = params.get("available_actions")
        if action_names:
            available_actions = [ActionType(name) for name in action_names]
        else:
            available_actions = default_actions

        # Total steps = 1 (setup) + num_steps (simulation) + 1 (cleanup)
        total_progress_steps = num_steps + 2

        # --- Step 0: Setup ---
        await self._reporter.report_progress(
            task_info, current_step=0, total_steps=total_progress_steps,
            data={"phase": "setup"},
        )

        # Create a temporary database file
        db_dir = os.path.join(tempfile.gettempdir(), "oasis_simulations")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, f"{task_info.task_id}.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        os.environ["OASIS_DB_PATH"] = os.path.abspath(db_path)

        # Build models via tiered assignment
        tiered_assigner = self._build_tiered_assigner(params)

        # Build agent graph
        if profile_path:
            # Use existing profile file
            if profile_path.endswith(".json"):
                default_model = create_model(
                    llm_provider, llm_model, self._settings, self._registry,
                )
                agent_graph = await generate_reddit_agent_graph(
                    profile_path=profile_path,
                    model=default_model,
                    available_actions=available_actions,
                )
            else:
                # CSV path handled by generate_twitter_agent_graph
                from oasis import generate_twitter_agent_graph
                default_model = create_model(
                    llm_provider, llm_model, self._settings, self._registry,
                )
                agent_graph = await generate_twitter_agent_graph(
                    profile_path=profile_path,
                    model=default_model,
                    available_actions=available_actions,
                )
        elif agent_profiles:
            # Build agents from inline profile data
            agent_graph = self._build_agent_graph_from_profiles(
                agent_profiles=agent_profiles,
                tiered_assigner=tiered_assigner,
                available_actions=available_actions,
                recsys_type=recsys_type,
                AgentGraph=AgentGraph,
                SocialAgent=SocialAgent,
                UserInfo=UserInfo,
            )
        else:
            # Generate simple numbered agents
            agent_graph = self._build_simple_agent_graph(
                num_agents=num_agents,
                tiered_assigner=tiered_assigner,
                available_actions=available_actions,
                recsys_type=recsys_type,
                AgentGraph=AgentGraph,
                SocialAgent=SocialAgent,
                UserInfo=UserInfo,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )

        # Create OasisEnv
        env = oasis.make(
            agent_graph=agent_graph,
            platform=platform_enum,
            database_path=db_path,
        )

        try:
            await env.reset()

            # --- Step 1..N: Simulation ---
            for step in range(1, num_steps + 1):
                # Check for cancellation
                if task_info.status.value == "cancelled":
                    logger.info("Task %s cancelled at step %d", task_info.task_id, step)
                    break

                if step == 1 and seed_content:
                    # First step: seed content via manual action, then LLM for rest
                    actions = {}
                    first_agent = env.agent_graph.get_agent(0)
                    actions[first_agent] = [
                        ManualAction(
                            action_type=ActionType.CREATE_POST,
                            action_args={"content": seed_content},
                        ),
                    ]
                    # Other agents do LLM actions
                    for agent_id, agent in env.agent_graph.get_agents():
                        if agent_id != 0:
                            actions[agent] = LLMAction()
                    await env.step(actions)
                else:
                    # All agents perform LLM-driven actions
                    actions = {
                        agent: LLMAction()
                        for _, agent in env.agent_graph.get_agents()
                    }
                    await env.step(actions)

                await self._reporter.report_progress(
                    task_info,
                    current_step=step,
                    total_steps=total_progress_steps,
                    data={"phase": "simulation", "step": step},
                )

        finally:
            # --- Cleanup ---
            await env.close()

        await self._reporter.report_progress(
            task_info,
            current_step=total_progress_steps,
            total_steps=total_progress_steps,
            data={"phase": "cleanup"},
        )

        result = {
            "db_path": db_path,
            "num_steps_completed": num_steps,
            "num_agents": agent_graph.get_num_nodes(),
            "platform_type": platform_type_str,
        }

        await self._reporter.report_complete(task_info, result)
        return result

    def _build_tiered_assigner(
        self, params: dict[str, Any]
    ) -> Optional[TieredModelAssigner]:
        """Build a TieredModelAssigner if API keys are available."""
        try:
            return TieredModelAssigner(
                settings=self._settings,
                registry=self._registry,
            )
        except Exception:
            logger.debug("Tiered assignment not available, using single model")
            return None

    def _build_simple_agent_graph(
        self,
        num_agents: int,
        tiered_assigner: Optional[TieredModelAssigner],
        available_actions,
        recsys_type: str,
        AgentGraph,
        SocialAgent,
        UserInfo,
        llm_provider: str,
        llm_model: str,
    ):
        """Create a simple agent graph with numbered agents."""
        agent_graph = AgentGraph()

        # Try tiered assignment first, fall back to single model
        if tiered_assigner:
            try:
                tier_assignments = tiered_assigner.assign_models(num_agents)
            except Exception:
                logger.info("Tiered model creation failed, falling back to single model")
                tier_assignments = None
        else:
            tier_assignments = None

        if tier_assignments is None:
            # Single model for all agents
            single_model = create_model(
                llm_provider, llm_model, self._settings, self._registry,
            )
            for i in range(num_agents):
                agent = SocialAgent(
                    agent_id=i,
                    user_info=UserInfo(
                        user_name=f"agent_{i}",
                        name=f"Agent {i}",
                        description=f"Simulated user {i}",
                        profile=None,
                        recsys_type=recsys_type,
                    ),
                    agent_graph=agent_graph,
                    model=single_model,
                    available_actions=available_actions,
                )
                agent_graph.add_agent(agent)
        else:
            for i in range(num_agents):
                tier, model = tier_assignments[i]
                agent = SocialAgent(
                    agent_id=i,
                    user_info=UserInfo(
                        user_name=f"agent_{i}",
                        name=f"Agent {i}",
                        description=f"Simulated user {i} (tier={tier.value})",
                        profile=None,
                        recsys_type=recsys_type,
                    ),
                    agent_graph=agent_graph,
                    model=model,
                    available_actions=available_actions,
                )
                agent_graph.add_agent(agent)

        return agent_graph

    def _build_agent_graph_from_profiles(
        self,
        agent_profiles: list[dict[str, Any]],
        tiered_assigner: Optional[TieredModelAssigner],
        available_actions,
        recsys_type: str,
        AgentGraph,
        SocialAgent,
        UserInfo,
    ):
        """Create an agent graph from user-provided profile dictionaries.

        Each profile dict should have:
            user_name: str
            name: str
            description: str
            profile: dict | None (optional, for persona/mbti/etc.)
        """
        agent_graph = AgentGraph()
        num_agents = len(agent_profiles)

        if tiered_assigner:
            try:
                tier_assignments = tiered_assigner.assign_models(num_agents)
            except Exception:
                tier_assignments = None
        else:
            tier_assignments = None

        for i, prof in enumerate(agent_profiles):
            if tier_assignments and i in tier_assignments:
                _, model = tier_assignments[i]
            else:
                model = create_model(
                    self._settings.default_llm_provider,
                    self._settings.default_llm_model,
                    self._settings,
                    self._registry,
                )

            profile_data = prof.get("profile")

            agent = SocialAgent(
                agent_id=i,
                user_info=UserInfo(
                    user_name=prof.get("user_name", f"agent_{i}"),
                    name=prof.get("name", f"Agent {i}"),
                    description=prof.get("description", ""),
                    profile=profile_data,
                    recsys_type=recsys_type,
                ),
                agent_graph=agent_graph,
                model=model,
                available_actions=available_actions,
            )
            agent_graph.add_agent(agent)

        return agent_graph
