# engine/graph/schema.py
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    TOPIC = "topic"
    COMMUNITY = "community"
    CONTENT = "content"


class EdgeType(str, Enum):
    FOLLOWS = "follows"
    OPPOSES = "opposes"
    BELONGS_TO = "belongs_to"
    INTERESTED_IN = "interested_in"
    INFLUENCES = "influences"
    PUBLISHES = "publishes"


class GraphNode(BaseModel):
    id: str
    type: NodeType
    label: str
    x: float = 0.0
    y: float = 0.0
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: EdgeType
    weight: float = Field(default=1.0, ge=0.0)
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphData(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def add_node(self, node: GraphNode) -> None:
        if self.get_node(node.id) is None:
            self.nodes.append(node)

    def remove_node(self, node_id: str) -> None:
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]

    def add_edge(self, edge: GraphEdge) -> None:
        if self.get_node(edge.source) is None or self.get_node(edge.target) is None:
            raise ValueError(f"Edge references non-existent node: {edge.source} -> {edge.target}")
        self.edges.append(edge)

    def remove_edge(self, edge_id: str) -> None:
        self.edges = [e for e in self.edges if e.id != edge_id]


class AnalysisResult(BaseModel):
    influence_scores: dict[str, float] = Field(default_factory=dict)
    communities: list[list[str]] = Field(default_factory=list)
    density: float = 0.0
    node_count: int = 0
    edge_count: int = 0
