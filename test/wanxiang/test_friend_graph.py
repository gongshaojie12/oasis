# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""FriendGraph + generate_small_world."""
from wanxiang.social_graph.graph import FriendGraph, generate_small_world


def test_add_edge_is_bidirectional():
    g = FriendGraph()
    g.add_edge("a", "b")
    assert "b" in g.neighbors("a")
    assert "a" in g.neighbors("b")


def test_self_loop_ignored():
    g = FriendGraph()
    g.add_edge("a", "a")
    assert g.neighbors("a") == set()


def test_n_nodes_and_edges():
    g = FriendGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("c", "a")
    assert g.n_nodes() == 3
    assert g.n_edges() == 3


def test_generate_small_world_n_lt_k_is_complete():
    ids = [f"a{i}" for i in range(5)]
    g = generate_small_world(ids, k=6, seed=0)
    for a in ids:
        assert g.neighbors(a) == set(ids) - {a}


def test_generate_small_world_deterministic():
    ids = [f"a{i}" for i in range(20)]
    g1 = generate_small_world(ids, k=4, seed=42)
    g2 = generate_small_world(ids, k=4, seed=42)
    for a in ids:
        assert g1.neighbors(a) == g2.neighbors(a)


def test_generate_small_world_different_seeds_diverge():
    ids = [f"a{i}" for i in range(20)]
    g1 = generate_small_world(ids, k=4, rewire_p=0.5, seed=1)
    g2 = generate_small_world(ids, k=4, rewire_p=0.5, seed=2)
    diff = sum(1 for a in ids if g1.neighbors(a) != g2.neighbors(a))
    assert diff > 0


def test_generate_small_world_average_degree_near_k():
    ids = [f"a{i}" for i in range(50)]
    g = generate_small_world(ids, k=6, rewire_p=0.0, seed=0)
    # no rewire → exact k regular ring (each node has k neighbors)
    for a in ids:
        assert g.degree(a) == 6


def test_generate_small_world_n_zero_or_one():
    assert generate_small_world([], k=6).n_nodes() == 0
    g = generate_small_world(["solo"], k=6)
    assert g.n_nodes() == 1
    assert g.degree("solo") == 0


def test_neighbors_returns_empty_for_unknown_node():
    g = FriendGraph()
    assert g.neighbors("nobody") == set()


def test_degree_for_isolated_node():
    g = FriendGraph()
    g.add_node("solo")
    assert g.degree("solo") == 0
