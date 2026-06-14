# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""per_focal_peer_signal: friend-graph 可见性过滤。"""
from wanxiang.simulation.decision import DecisionResult
from wanxiang.simulation.scenario import DecisionKind
from wanxiang.simulation.social import per_focal_peer_signal
from wanxiang.social_graph.graph import FriendGraph


def _mk_results(n: int = 5) -> list[DecisionResult]:
    """5 个 RATE 结果，第 i 个 value=i+1（1..5），便于区分。"""
    return [
        DecisionResult(
            agent_id=i, kind=DecisionKind.RATE, value=i + 1,
            raw=f'{{"score":{i + 1}}}', error=None)
        for i in range(n)
    ]


def test_per_focal_no_friends_returns_neutral():
    """0 好友 → 中立占位（无 peer 数据泄漏）。"""
    results = _mk_results()
    g = FriendGraph()
    # a0 没有任何边
    out = per_focal_peer_signal(
        focal_idx=0, all_results=results,
        friend_graph=g, persona_ids=[f"a{i}" for i in range(5)])
    # 中立文案不应包含 mean 数字 (任何 1..5 的均值 1.0/2.0/.../3.0)
    # 也不应包含 "均值" 之类的统计字样
    assert "均值" not in out
    assert isinstance(out, str) and len(out) > 0


def test_per_focal_one_friend_uses_only_that_friend():
    """focal 仅与 a2 是朋友 → 聚合只看 a2.value=3。"""
    results = _mk_results()
    g = FriendGraph()
    g.add_edge("a0", "a2")
    out = per_focal_peer_signal(
        focal_idx=0, all_results=results,
        friend_graph=g, persona_ids=[f"a{i}" for i in range(5)])
    # 只有一个朋友 → mean=3.0
    assert "3.0" in out or "3" in out


def test_per_focal_multiple_friends_mean_matches_friends_only():
    """focal a0 与 a1(=2) 和 a3(=4) 朋友 → mean=3.0；不应包含 a2/a4。"""
    results = _mk_results()
    g = FriendGraph()
    g.add_edge("a0", "a1")
    g.add_edge("a0", "a3")
    out = per_focal_peer_signal(
        focal_idx=0, all_results=results,
        friend_graph=g, persona_ids=[f"a{i}" for i in range(5)])
    # (2 + 4) / 2 = 3.0
    assert "3.0" in out


def test_per_focal_excludes_self_even_if_in_neighbors():
    """防御：哪怕 graph 错误地把 focal 列为自己的邻居，也不应聚合 focal 自己。"""
    results = _mk_results()
    g = FriendGraph()
    g.adjacency["a0"] = {"a0", "a2"}  # 故意污染
    g.adjacency["a2"] = {"a0"}
    out = per_focal_peer_signal(
        focal_idx=0, all_results=results,
        friend_graph=g, persona_ids=[f"a{i}" for i in range(5)])
    # 只能看 a2 → mean=3.0；如果错把 a0(=1) 算进去 mean=2.0
    assert "3.0" in out
    assert "2.0" not in out


def test_per_focal_unknown_focal_id_returns_neutral():
    """persona_ids 缺该 focal → 视作无朋友。"""
    results = _mk_results()
    g = FriendGraph()
    g.add_edge("a0", "a1")
    # persona_ids 不含 a0
    out = per_focal_peer_signal(
        focal_idx=0, all_results=results,
        friend_graph=g, persona_ids=["X", "a1", "a2", "a3", "a4"])
    # focal 实际 id 是 "X"，无任何朋友 → 中立
    assert "均值" not in out


def test_per_focal_with_choose_kind():
    """CHOOSE 也按朋友子集聚合。"""
    results = [
        DecisionResult(agent_id=0, kind=DecisionKind.CHOOSE,
                       value="A", raw='{"option":"A"}', error=None),
        DecisionResult(agent_id=1, kind=DecisionKind.CHOOSE,
                       value="B", raw='{"option":"B"}', error=None),
        DecisionResult(agent_id=2, kind=DecisionKind.CHOOSE,
                       value="B", raw='{"option":"B"}', error=None),
        DecisionResult(agent_id=3, kind=DecisionKind.CHOOSE,
                       value="C", raw='{"option":"C"}', error=None),
    ]
    g = FriendGraph()
    # a0 的朋友只有 a1(B) 和 a3(C) → 都是 1 票，按字典序 top=B
    g.add_edge("a0", "a1")
    g.add_edge("a0", "a3")
    out = per_focal_peer_signal(
        focal_idx=0, all_results=results,
        friend_graph=g, persona_ids=[f"a{i}" for i in range(4)])
    # peer 集合里没有 "A"（a0 自己）也没有非朋友 a2，但要包含 B 或 C
    assert "B" in out or "C" in out
