# engine/graph/mapper.py
from __future__ import annotations

from typing import Any

from .schema import GraphData, NodeType, EdgeType


class GraphToSimulationMapper:
    def __init__(self, graph: GraphData):
        self._graph = graph

    def map(self) -> dict[str, Any]:
        agents = self._map_agents()
        seed_content = self._map_seed_content()
        follow_pairs = self._map_follows()

        return {
            "agent_profiles": agents,
            "seed_content": seed_content,
            "follow_pairs": follow_pairs,
            "num_agents": len(agents),
        }

    def _map_agents(self) -> list[dict[str, Any]]:
        agents = []
        for node in self._graph.nodes:
            if node.type != NodeType.PERSON:
                continue

            interests = []
            for e in self._graph.edges:
                if e.source == node.id and e.type == EdgeType.INTERESTED_IN:
                    target = self._graph.get_node(e.target)
                    if target:
                        interests.append(target.label)

            org = None
            for e in self._graph.edges:
                if e.source == node.id and e.type == EdgeType.BELONGS_TO:
                    target = self._graph.get_node(e.target)
                    if target and target.type == NodeType.ORGANIZATION:
                        org = target.label

            profile: dict[str, Any] = {
                "name": node.label,
                "graph_node_id": node.id,
                "interests": interests,
            }
            if org:
                profile["organization"] = org
            profile.update(node.properties)
            agents.append(profile)

        return agents

    def _map_seed_content(self) -> list[dict[str, Any]]:
        seeds = []
        for node in self._graph.nodes:
            if node.type == NodeType.CONTENT:
                seeds.append({
                    "content": node.properties.get("text", node.label),
                    "author_node_id": self._find_publisher(node.id),
                })
            elif node.type == NodeType.TOPIC:
                seeds.append({
                    "content": f"#{node.label}",
                    "topic": node.label,
                })
        return seeds

    def _find_publisher(self, content_id: str) -> str | None:
        for e in self._graph.edges:
            if e.target == content_id and e.type == EdgeType.PUBLISHES:
                return e.source
        return None

    def _map_follows(self) -> list[dict[str, str]]:
        pairs = []
        for e in self._graph.edges:
            if e.type == EdgeType.FOLLOWS:
                pairs.append({"follower": e.source, "followee": e.target})
        return pairs
