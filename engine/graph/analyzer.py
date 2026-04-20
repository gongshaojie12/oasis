# engine/graph/analyzer.py
from __future__ import annotations

from .schema import GraphData, AnalysisResult, NodeType


class GraphAnalyzer:
    def __init__(self, graph: GraphData):
        self._graph = graph

    def analyze(self) -> AnalysisResult:
        return AnalysisResult(
            influence_scores=self._compute_influence(),
            communities=self._detect_communities(),
            density=self._compute_density(),
            node_count=len(self._graph.nodes),
            edge_count=len(self._graph.edges),
        )

    def _compute_influence(self, iterations: int = 20, damping: float = 0.85) -> dict[str, float]:
        nodes = [n.id for n in self._graph.nodes]
        if not nodes:
            return {}

        scores = {nid: 1.0 / len(nodes) for nid in nodes}
        inbound: dict[str, list[str]] = {nid: [] for nid in nodes}
        outbound_count: dict[str, int] = {nid: 0 for nid in nodes}

        for e in self._graph.edges:
            if e.source in inbound and e.target in inbound:
                inbound[e.target].append(e.source)
                outbound_count[e.source] = outbound_count.get(e.source, 0) + 1

        for _ in range(iterations):
            new_scores = {}
            for nid in nodes:
                rank_sum = sum(
                    scores[src] / max(outbound_count[src], 1) for src in inbound[nid]
                )
                new_scores[nid] = (1 - damping) / len(nodes) + damping * rank_sum
            scores = new_scores

        return {k: round(v, 4) for k, v in sorted(scores.items(), key=lambda x: -x[1])}

    def _detect_communities(self) -> list[list[str]]:
        if not self._graph.nodes:
            return []

        adj: dict[str, set[str]] = {n.id: set() for n in self._graph.nodes}
        for e in self._graph.edges:
            if e.source in adj and e.target in adj:
                adj[e.source].add(e.target)
                adj[e.target].add(e.source)

        visited: set[str] = set()
        communities: list[list[str]] = []

        for nid in adj:
            if nid in visited:
                continue
            community: list[str] = []
            stack = [nid]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                community.append(current)
                stack.extend(adj[current] - visited)
            communities.append(sorted(community))

        return sorted(communities, key=lambda c: -len(c))

    def _compute_density(self) -> float:
        n = len(self._graph.nodes)
        if n < 2:
            return 0.0
        max_edges = n * (n - 1)
        return round(len(self._graph.edges) / max_edges, 4)
