# engine/tests/test_graph_mapper.py
from engine.graph.schema import GraphData, GraphNode, GraphEdge, NodeType, EdgeType
from engine.graph.mapper import GraphToSimulationMapper


def test_map_agents():
    g = GraphData()
    g.add_node(GraphNode(id="p1", type=NodeType.PERSON, label="Alice"))
    g.add_node(GraphNode(id="t1", type=NodeType.TOPIC, label="AI"))
    g.add_edge(GraphEdge(id="e1", source="p1", target="t1", type=EdgeType.INTERESTED_IN))

    result = GraphToSimulationMapper(g).map()
    assert result["num_agents"] == 1
    assert result["agent_profiles"][0]["name"] == "Alice"
    assert "AI" in result["agent_profiles"][0]["interests"]


def test_map_seed_content():
    g = GraphData()
    g.add_node(GraphNode(id="c1", type=NodeType.CONTENT, label="First post", properties={"text": "Hello world"}))
    g.add_node(GraphNode(id="t1", type=NodeType.TOPIC, label="Technology"))

    result = GraphToSimulationMapper(g).map()
    assert len(result["seed_content"]) == 2


def test_map_follows():
    g = GraphData()
    g.add_node(GraphNode(id="p1", type=NodeType.PERSON, label="A"))
    g.add_node(GraphNode(id="p2", type=NodeType.PERSON, label="B"))
    g.add_edge(GraphEdge(id="e1", source="p1", target="p2", type=EdgeType.FOLLOWS))

    result = GraphToSimulationMapper(g).map()
    assert len(result["follow_pairs"]) == 1
    assert result["follow_pairs"][0] == {"follower": "p1", "followee": "p2"}


def test_empty_graph():
    result = GraphToSimulationMapper(GraphData()).map()
    assert result["num_agents"] == 0
    assert result["agent_profiles"] == []
