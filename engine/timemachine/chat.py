# engine/timemachine/chat.py
from __future__ import annotations

import sqlite3
from typing import Any, Callable, Awaitable, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None


class ChatResponse(BaseModel):
    agent_id: int
    agent_name: str
    response: str
    context_round: int


class AgentChatEngine:
    def __init__(
        self,
        db_path: str,
        llm_call: Callable[[str], Awaitable[str]],
    ) -> None:
        self._db_path = db_path
        self._llm_call = llm_call

    async def chat(
        self,
        agent_id: int,
        round_context: int,
        user_message: str,
        history: list[ChatMessage] | None = None,
    ) -> ChatResponse:
        agent_profile = self._get_agent_profile(agent_id)
        agent_state = self._get_agent_state_at_round(agent_id, round_context)

        prompt = self._build_chat_prompt(
            agent_profile=agent_profile,
            agent_state=agent_state,
            round_context=round_context,
            user_message=user_message,
            history=history or [],
        )

        response_text = await self._llm_call(prompt)

        return ChatResponse(
            agent_id=agent_id,
            agent_name=agent_profile.get("user_name", f"agent_{agent_id}"),
            response=response_text,
            context_round=round_context,
        )

    async def roundtable(
        self,
        agent_ids: list[int],
        round_context: int,
        topic: str,
        num_rounds: int = 3,
    ) -> list[ChatMessage]:
        profiles = {aid: self._get_agent_profile(aid) for aid in agent_ids}
        states = {aid: self._get_agent_state_at_round(aid, round_context) for aid in agent_ids}

        messages: list[ChatMessage] = []
        for round_num in range(num_rounds):
            for aid in agent_ids:
                prompt = self._build_roundtable_prompt(
                    speaker_profile=profiles[aid],
                    speaker_state=states[aid],
                    all_profiles=profiles,
                    round_context=round_context,
                    topic=topic,
                    prior_messages=messages,
                    round_num=round_num,
                )
                response = await self._llm_call(prompt)
                messages.append(ChatMessage(
                    role="agent",
                    content=response,
                    agent_id=aid,
                    agent_name=profiles[aid].get("user_name", f"agent_{aid}"),
                ))

        return messages

    def _get_agent_profile(self, agent_id: int) -> dict[str, Any]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM user WHERE user_id = ?", (agent_id,)
            ).fetchone()
            return dict(row) if row else {"user_id": agent_id, "user_name": f"agent_{agent_id}"}
        finally:
            conn.close()

    def _get_agent_state_at_round(self, agent_id: int, round_number: int) -> dict[str, Any]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            all_traces = [
                dict(r) for r in conn.execute(
                    "SELECT * FROM trace WHERE user_id = ? ORDER BY created_at",
                    (agent_id,),
                ).fetchall()
            ]

            all_agent_ids = set(
                r["user_id"] for r in conn.execute("SELECT DISTINCT user_id FROM trace").fetchall()
            )
            num_agents = max(len(all_agent_ids), 1)
            cutoff = round_number * num_agents

            agent_traces_up_to_round = [t for i, t in enumerate(all_traces) if i < cutoff]

            post_count = sum(
                1 for t in agent_traces_up_to_round
                if t.get("action") in ("CREATE_POST", "REPOST", "create_post", "repost")
            )

            action_counts: dict[str, int] = {}
            for t in agent_traces_up_to_round:
                a = t.get("action", "unknown")
                action_counts[a] = action_counts.get(a, 0) + 1

            recent = agent_traces_up_to_round[-5:] if agent_traces_up_to_round else []

            return {
                "post_count": post_count,
                "total_actions": len(agent_traces_up_to_round),
                "action_distribution": action_counts,
                "recent_actions": [t.get("action", "") for t in recent],
            }
        finally:
            conn.close()

    def _build_chat_prompt(
        self,
        agent_profile: dict[str, Any],
        agent_state: dict[str, Any],
        round_context: int,
        user_message: str,
        history: list[ChatMessage],
    ) -> str:
        name = agent_profile.get("name", agent_profile.get("user_name", "Agent"))
        bio = agent_profile.get("bio", "")

        history_text = ""
        if history:
            lines = []
            for msg in history[-10:]:
                speaker = msg.agent_name if msg.role == "agent" else "用户"
                lines.append(f"{speaker}: {msg.content}")
            history_text = f"\n过往对话:\n" + "\n".join(lines)

        return f"""你现在扮演一个社交媒体仿真中的虚拟用户。

角色信息:
- 名称: {name}
- 简介: {bio}
- 当前是第 {round_context} 轮仿真

截至本轮的状态:
- 发帖数: {agent_state.get('post_count', 0)}
- 总行为数: {agent_state.get('total_actions', 0)}
- 最近行为: {', '.join(agent_state.get('recent_actions', []))}

规则:
1. 你只知道到第 {round_context} 轮为止的信息，不知道之后发生的事
2. 以该角色的身份和视角回答
3. 回答简洁自然，像真实社交媒体用户那样说话
4. 用中文回答
{history_text}

用户提问: {user_message}"""

    def _build_roundtable_prompt(
        self,
        speaker_profile: dict[str, Any],
        speaker_state: dict[str, Any],
        all_profiles: dict[int, dict[str, Any]],
        round_context: int,
        topic: str,
        prior_messages: list[ChatMessage],
        round_num: int,
    ) -> str:
        name = speaker_profile.get("name", speaker_profile.get("user_name", "Agent"))
        bio = speaker_profile.get("bio", "")

        participants = ", ".join(
            p.get("name", p.get("user_name", f"agent_{aid}"))
            for aid, p in all_profiles.items()
        )

        prior_text = ""
        if prior_messages:
            lines = [f"{m.agent_name}: {m.content}" for m in prior_messages[-15:]]
            prior_text = "\n之前的讨论:\n" + "\n".join(lines)

        return f"""你正在参加一场圆桌讨论，扮演社交媒体仿真中的虚拟用户。

你的角色:
- 名称: {name}
- 简介: {bio}
- 当前状态: 发帖 {speaker_state.get('post_count', 0)} 篇, 行为 {speaker_state.get('total_actions', 0)} 次

参与者: {participants}
讨论话题: {topic}
当前是第 {round_num + 1} 轮讨论 (基于仿真第 {round_context} 轮的上下文)
{prior_text}

请以 {name} 的身份发言。要求:
1. 基于你的角色特点和经历发言
2. 回应其他人的观点，可以同意、补充或反驳
3. 简洁有力，2-4 句话
4. 用中文"""
