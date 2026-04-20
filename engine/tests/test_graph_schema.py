# engine/tests/test_graph_schema.py
from engine.graph.schema import GraphData, GraphNode, GraphEdge, NodeType, EdgeType


def test_graph_data_add_node():
    g = GraphData()
    node = GraphNode(id="n1", type=NodeType.PERSON, label="Alice")
    g.add_node(node)
    assert len(g.nodes) == 1
    assert g.get_node("n1") is not None


def test_graph_data_remove_node_cascades_edges():
    g = GraphData()
    g.add_node(GraphNode(id="n1", type=NodeType.PERSON, label="A"))
    g.add_node(GraphNode(id="n2", type=NodeType.PERSON, label="B"))
    g.add_edge(GraphEdge(id="e1", source="n1", target="n2", type=EdgeType.FOLLOWS))
    g.remove_node("n1")
    assert len(g.nodes) == 1
    assert len(g.edges) == 0


def test_graph_data_serialization():
    g = GraphData()
    g.add_node(GraphNode(id="n1", type=NodeType.TOPIC, label="AI", properties={"trending": True}))
    d = g.model_dump()
    restored = GraphData.model_validate(d)
    assert restored.nodes[0].label == "AI"
    assert restored.nodes[0].properties["trending"] is True


def test_edge_types():
    for et in EdgeType:
        edge = GraphEdge(id=f"e_{et.value}", source="a", target="b", type=et)
        assert edge.type == et
