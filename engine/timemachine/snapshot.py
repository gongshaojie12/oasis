# engine/timemachine/snapshot.py
from __future__ import annotations

import sqlite3
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentSnapshot(BaseModel):
    agent_id: int
    user_name: str
    post_count: int = 0
    action_count: int = 0
    recent_actions: list[str] = Field(default_factory=list)


class RoundSnapshot(BaseModel):
    round_number: int
    posts: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    agent_summaries: list[AgentSnapshot] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class SnapshotExtractor:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def extract_all(self, num_steps: int) -> list[RoundSnapshot]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            snapshots = []
            for round_num in range(1, num_steps + 1):
                snap = self._extract_round(conn, round_num)
                snapshots.append(snap)
            return snapshots
        finally:
            conn.close()

    def extract_round(self, round_number: int) -> RoundSnapshot:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            return self._extract_round(conn, round_number)
        finally:
            conn.close()

    def _extract_round(self, conn: sqlite3.Connection, round_number: int) -> RoundSnapshot:
        cursor = conn.cursor()

        traces = [
            dict(r) for r in cursor.execute(
                "SELECT * FROM trace WHERE info LIKE ?",
                (f'%"step": {round_number}%',),
            ).fetchall()
        ]

        if not traces:
            traces = self._get_traces_by_position(cursor, round_number)

        posts = [
            dict(r) for r in cursor.execute("SELECT * FROM post").fetchall()
        ]
        round_posts = self._filter_posts_for_round(posts, traces)

        users = [dict(r) for r in cursor.execute("SELECT * FROM user").fetchall()]
        agent_summaries = self._build_agent_summaries(users, traces)

        action_counts: dict[str, int] = {}
        for t in traces:
            action = t.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1

        metrics = {
            "total_actions": len(traces),
            "total_posts_this_round": len(round_posts),
            "action_distribution": action_counts,
        }

        return RoundSnapshot(
            round_number=round_number,
            posts=round_posts[:50],
            actions=traces[:100],
            agent_summaries=agent_summaries,
            metrics=metrics,
        )

    def _get_traces_by_position(
        self, cursor: sqlite3.Cursor, round_number: int
    ) -> list[dict[str, Any]]:
        all_traces = [dict(r) for r in cursor.execute("SELECT * FROM trace ORDER BY created_at").fetchall()]
        if not all_traces:
            return []

        agent_ids = set(t["user_id"] for t in all_traces)
        num_agents = len(agent_ids)
        if num_agents == 0:
            return []

        start = (round_number - 1) * num_agents
        end = round_number * num_agents
        return all_traces[start:end]

    def _filter_posts_for_round(
        self, all_posts: list[dict[str, Any]], round_traces: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        create_post_user_ids = set()
        for t in round_traces:
            if t.get("action") in ("CREATE_POST", "REPOST", "create_post", "repost"):
                create_post_user_ids.add(t.get("user_id"))

        if not create_post_user_ids:
            return []

        return [p for p in all_posts if p.get("user_id") in create_post_user_ids]

    def _build_agent_summaries(
        self, users: list[dict[str, Any]], round_traces: list[dict[str, Any]]
    ) -> list[AgentSnapshot]:
        agent_actions: dict[int, list[str]] = {}
        for t in round_traces:
            uid = t.get("user_id", 0)
            action = t.get("action", "unknown")
            agent_actions.setdefault(uid, []).append(action)

        user_map = {u["user_id"]: u for u in users}
        summaries = []
        for uid, actions in agent_actions.items():
            user = user_map.get(uid, {})
            summaries.append(AgentSnapshot(
                agent_id=uid,
                user_name=user.get("user_name", f"agent_{uid}"),
                action_count=len(actions),
                recent_actions=actions[:5],
            ))

        summaries.sort(key=lambda s: s.action_count, reverse=True)
        return summaries[:20]
