# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""轻量好友图（M3+）。

仅在 wechat 等"熟人圈层"平台用于 peer signal 可见性过滤。
其他平台 (xhs/douyin/weibo/twitter/reddit) 保持公开广场不需要。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class FriendGraph:
    """无向图。邻居集合每边出现两次（双向存储）。"""
    adjacency: dict[str, set[str]] = field(default_factory=dict)

    def add_node(self, agent_id: str) -> None:
        self.adjacency.setdefault(agent_id, set())

    def add_edge(self, a: str, b: str) -> None:
        if a == b:
            return
        self.adjacency.setdefault(a, set()).add(b)
        self.adjacency.setdefault(b, set()).add(a)

    def neighbors(self, agent_id: str) -> set[str]:
        return self.adjacency.get(agent_id, set())

    def degree(self, agent_id: str) -> int:
        return len(self.adjacency.get(agent_id, set()))

    def n_nodes(self) -> int:
        return len(self.adjacency)

    def n_edges(self) -> int:
        return sum(len(v) for v in self.adjacency.values()) // 2


def generate_small_world(
    agent_ids: list[str],
    *,
    k: int = 6,
    rewire_p: float = 0.1,
    seed: int = 0,
) -> FriendGraph:
    """Watts–Strogatz 小世界图（适合熟人社交）。

    每个节点先连环形最近 k 个邻居，再以 rewire_p 概率重连远端。
    Deterministic given seed.
    若 len(agent_ids) <= k 则退化为完全图。
    """
    g = FriendGraph()
    n = len(agent_ids)
    for aid in agent_ids:
        g.add_node(aid)
    if n < 2:
        return g
    if n <= k:
        # 完全图
        for i in range(n):
            for j in range(i + 1, n):
                g.add_edge(agent_ids[i], agent_ids[j])
        return g
    rng = random.Random(seed)
    half = max(1, k // 2)
    # 环形最近邻
    for i in range(n):
        for off in range(1, half + 1):
            j = (i + off) % n
            g.add_edge(agent_ids[i], agent_ids[j])
    # 重连
    for i in range(n):
        for off in range(1, half + 1):
            if rng.random() < rewire_p:
                j = (i + off) % n
                # 选一个非邻居 + 非自身的新目标
                candidates = [a for a in agent_ids
                              if a != agent_ids[i]
                              and a not in g.neighbors(agent_ids[i])]
                if candidates:
                    new_j = rng.choice(candidates)
                    # 断开旧边、加新边
                    g.adjacency[agent_ids[i]].discard(agent_ids[j])
                    g.adjacency[agent_ids[j]].discard(agent_ids[i])
                    g.add_edge(agent_ids[i], new_j)
    return g
