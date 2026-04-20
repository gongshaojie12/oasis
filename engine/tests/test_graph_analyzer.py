# engine/tests/test_graph_analyzer.py
from engine.graph.schema import GraphData, GraphNode, GraphEdge, NodeType, EdgeType
from engine.graph.analyzer import GraphAnalyzer


def _make_graph() -> GraphData:
    g = GraphData()
    g.add_node(GraphNode(id="a", type=NodeType.PERSON, label="Alice"))
    g.add_node(GraphNode(id="b", type=NodeType.PERSON, label="Bob"))
    g.add_node(GraphNode(id="c", type=NodeType.PERSON, label="Charlie"))
    g.add_edge(GraphEdge(id="e1", source="a", target="b", type=EdgeType.FOLLOWS))
    g.add_edge(GraphEdge(id="e2", source="b", target="c", type=EdgeType.FOLLOWS))
    g.add_edge(GraphEdge(id="e3", source="c", target="a", type=EdgeType.FOLLOWS))
    return g


def test_influence_scores():
    analyzer = GraphAnalyzer(_make_graph())
    result = analyzer.analyze()
    assert len(result.influence_scores) == 3
    assert all(v > 0 for v in result.influence_scores.values())


def test_community_detection():
    g = GraphData()
    g.add_node(GraphNode(id="a", type=NodeType.PERSON, label="A"))
    g.add_node(GraphNode(id="b", type=NodeType.PERSON, label="B"))
    g.add_node(GraphNode(id="c", type=NodeType.PERSON, label="C"))
    g.add_edge(GraphEdge(id="e1", source="a", target="b", type=EdgeType.FOLLOWS))
    analyzer = GraphAnalyzer(g)
    result = analyzer.analyze()
    assert len(result.communities) == 2


def test_density():
    analyzer = GraphAnalyzer(_make_graph())
    result = analyzer.analyze()
    assert 0 < result.density <= 1.0
    assert result.node_count == 3
    assert result.edge_count == 3


def test_empty_graph():
    analyzer = GraphAnalyzer(GraphData())
    result = analyzer.analyze()
    assert result.density == 0.0
    assert result.communities == []
