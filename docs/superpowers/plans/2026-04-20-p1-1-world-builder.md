# P1-1: 世界构建器 (World Builder) 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建可视化知识图谱编辑器，用户通过拖拽式界面构建社交世界的人物关系、组织架构和话题关联，并可将图谱直接转化为仿真配置。

**Architecture:** 图谱数据以 JSON 格式存储在 SQLite/PostgreSQL 中（与基因组模式一致），Engine 层提供图分析算法和图谱→仿真映射，前端使用 ECharts graph 类型实现力导向布局的可视化编辑器。

**Tech Stack:** TypeScript (Nuxt 4, Naive UI, ECharts graph), Python (FastAPI, Pydantic), Drizzle ORM, Zod

---

## 文件结构

### 新建文件

```
engine/
├── graph/
│   ├── __init__.py           — 模块导出
│   ├── schema.py             — 图谱 Pydantic 数据模型
│   ├── analyzer.py           — 图分析算法 (影响力、社区检测)
│   └── mapper.py             — 图谱 → 仿真配置映射

web/
├── server/
│   └── api/world-builder/
│       ├── index.get.ts      — 图谱列表
│       ├── index.post.ts     — 创建图谱
│       ├── [id].get.ts       — 图谱详情 + 节点/边数据
│       ├── [id].put.ts       — 更新图谱 (含节点/边批量更新)
│       ├── [id].delete.ts    — 删除图谱
│       ├── [id]/
│       │   ├── analyze.post.ts   — 运行图分析
│       │   └── to-simulation.post.ts — 转化为仿真配置
│       └── import.post.ts    — 导入图谱 (JSON)
├── app/
│   ├── pages/world-builder/
│   │   ├── index.vue         — 图谱列表页
│   │   └── [id].vue          — 可视化图谱编辑器
│   ├── components/
│   │   ├── GraphEditor.vue       — 图谱力导向编辑器核心组件
│   │   ├── GraphNodePanel.vue    — 节点属性编辑面板
│   │   └── GraphToolbar.vue      — 工具栏 (添加节点/边、布局、导出)
│   └── stores/
│       └── world-builder.ts  — 图谱 Pinia Store
```

### 修改文件

```
web/server/database/schema/sqlite.ts  — 添加 knowledge_graphs 表
web/server/database/schema/pg.ts      — 同上
web/server/database/schema/index.ts   — 新增导出
engine/main.py                         — 添加图分析和映射 API
web/app/components/layout/Sidebar.vue — 添加「世界构建」导航
```

---

## Task 1: 图谱数据模型 (Engine)

**Files:**
- Create: `engine/graph/__init__.py`
- Create: `engine/graph/schema.py`
- Test: `engine/tests/test_graph_schema.py`

- [ ] **Step 1: 创建图谱数据模型**

```python
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
        self.edges.append(edge)

    def remove_edge(self, edge_id: str) -> None:
        self.edges = [e for e in self.edges if e.id != edge_id]


class AnalysisResult(BaseModel):
    influence_scores: dict[str, float] = Field(default_factory=dict)
    communities: list[list[str]] = Field(default_factory=list)
    density: float = 0.0
    node_count: int = 0
    edge_count: int = 0
```

- [ ] **Step 2: 创建 __init__.py**

```python
# engine/graph/__init__.py
from .schema import (
    AnalysisResult,
    EdgeType,
    GraphData,
    GraphEdge,
    GraphNode,
    NodeType,
)

__all__ = [
    "AnalysisResult",
    "EdgeType",
    "GraphData",
    "GraphEdge",
    "GraphNode",
    "NodeType",
]
```

- [ ] **Step 3: 编写测试**

```python
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
```

- [ ] **Step 4: 提交**

```bash
git add engine/graph/ engine/tests/test_graph_schema.py
git commit -m "feat(graph): add knowledge graph data models"
```

---

## Task 2: 图分析算法

**Files:**
- Create: `engine/graph/analyzer.py`
- Test: `engine/tests/test_graph_analyzer.py`

- [ ] **Step 1: 实现图分析器**

```python
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
```

- [ ] **Step 2: 编写测试**

```python
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
    # c is isolated
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
```

- [ ] **Step 3: 更新导出并提交**

在 `engine/graph/__init__.py` 添加:
```python
from .analyzer import GraphAnalyzer
```

```bash
git add engine/graph/ engine/tests/test_graph_analyzer.py
git commit -m "feat(graph): implement graph analyzer with influence and community detection"
```

---

## Task 3: 图谱→仿真映射

**Files:**
- Create: `engine/graph/mapper.py`
- Test: `engine/tests/test_graph_mapper.py`

- [ ] **Step 1: 实现映射器**

```python
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
```

- [ ] **Step 2: 编写测试**

```python
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
```

- [ ] **Step 3: 更新导出并提交**

在 `engine/graph/__init__.py` 添加:
```python
from .mapper import GraphToSimulationMapper
```

```bash
git add engine/graph/ engine/tests/test_graph_mapper.py
git commit -m "feat(graph): implement graph-to-simulation mapper"
```

---

## Task 4: Engine 图谱 API 端点

**Files:**
- Modify: `engine/main.py`

- [ ] **Step 1: 在 main.py 添加图谱端点**

在 `engine/main.py` 中添加：

```python
# === 新增 import ===
from engine.graph.schema import GraphData
from engine.graph.analyzer import GraphAnalyzer
from engine.graph.mapper import GraphToSimulationMapper

# === 新增请求模型 ===
class GraphAnalyzeRequest(BaseModel):
    graph_data: dict[str, Any]

class GraphMapRequest(BaseModel):
    graph_data: dict[str, Any]

# === 新增端点 ===
@app.post(
    "/engine/graph/analyze",
    dependencies=[Depends(verify_internal_key)],
)
async def analyze_graph(body: GraphAnalyzeRequest):
    graph = GraphData.model_validate(body.graph_data)
    analyzer = GraphAnalyzer(graph)
    result = analyzer.analyze()
    return result.model_dump()


@app.post(
    "/engine/graph/to-simulation",
    dependencies=[Depends(verify_internal_key)],
)
async def graph_to_simulation(body: GraphMapRequest):
    graph = GraphData.model_validate(body.graph_data)
    mapper = GraphToSimulationMapper(graph)
    return mapper.map()
```

- [ ] **Step 2: 提交**

```bash
git add engine/main.py
git commit -m "feat(engine): add graph analysis and mapping API endpoints"
```

---

## Task 5: 数据库表定义

**Files:**
- Modify: `web/server/database/schema/sqlite.ts`
- Modify: `web/server/database/schema/pg.ts`
- Modify: `web/server/database/schema/index.ts`

- [ ] **Step 1: 在 sqlite.ts 添加 knowledge_graphs 表**

```typescript
export const knowledgeGraphs = sqliteTable('knowledge_graphs', {
  id: text('id').primaryKey(),
  enterpriseId: text('enterprise_id').notNull().references(() => enterprises.id),
  name: text('name').notNull(),
  description: text('description'),
  graphData: text('graph_data').notNull(),
  nodeCount: integer('node_count').default(0).notNull(),
  edgeCount: integer('edge_count').default(0).notNull(),
  metadata: text('metadata'),
  createdAt: text('created_at').notNull(),
  updatedAt: text('updated_at').notNull(),
})
```

- [ ] **Step 2: 在 pg.ts 添加同样的表**

同 sqlite 结构，使用 `pgTable`。

- [ ] **Step 3: 更新 index.ts 导出**

添加 `knowledgeGraphs` 到导出列表。

- [ ] **Step 4: 提交**

```bash
git add web/server/database/schema/
git commit -m "feat(db): add knowledge_graphs table"
```

---

## Task 6: Server 端图谱 API

**Files:**
- Create: `web/server/api/world-builder/index.get.ts`
- Create: `web/server/api/world-builder/index.post.ts`
- Create: `web/server/api/world-builder/[id].get.ts`
- Create: `web/server/api/world-builder/[id].put.ts`
- Create: `web/server/api/world-builder/[id].delete.ts`
- Create: `web/server/api/world-builder/[id]/analyze.post.ts`
- Create: `web/server/api/world-builder/[id]/to-simulation.post.ts`
- Create: `web/server/api/world-builder/import.post.ts`

- [ ] **Step 1: 创建列表 API**

```typescript
// web/server/api/world-builder/index.get.ts
import { eq, desc } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { knowledgeGraphs } from '~~/server/database/schema'
import { success } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select({
    id: knowledgeGraphs.id,
    name: knowledgeGraphs.name,
    description: knowledgeGraphs.description,
    nodeCount: knowledgeGraphs.nodeCount,
    edgeCount: knowledgeGraphs.edgeCount,
    createdAt: knowledgeGraphs.createdAt,
    updatedAt: knowledgeGraphs.updatedAt,
  }).from(knowledgeGraphs)
    .where(eq(knowledgeGraphs.enterpriseId, enterpriseId))
    .orderBy(desc(knowledgeGraphs.createdAt))
    .limit(50)

  return success(items)
})
```

- [ ] **Step 2: 创建新建 API**

```typescript
// web/server/api/world-builder/index.post.ts
import { z } from 'zod'
import { useDB } from '~~/server/database'
import { knowledgeGraphs, operationLogs } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  graphData: z.object({
    nodes: z.array(z.any()).default([]),
    edges: z.array(z.any()).default([]),
  }).optional(),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const { userId, enterpriseId } = event.context.user!
  const db = useDB()
  const timestamp = now()
  const id = generateId()

  const graphData = parsed.data.graphData || { nodes: [], edges: [] }

  await db.insert(knowledgeGraphs).values({
    id, enterpriseId,
    name: parsed.data.name,
    description: parsed.data.description || null,
    graphData: JSON.stringify(graphData),
    nodeCount: graphData.nodes.length,
    edgeCount: graphData.edges.length,
    createdAt: timestamp, updatedAt: timestamp,
  })

  await db.insert(operationLogs).values({
    id: generateId(), enterpriseId, userId,
    action: 'create_graph', resourceType: 'knowledge_graph', resourceId: id,
    createdAt: timestamp,
  })

  return success({ id, name: parsed.data.name })
})
```

- [ ] **Step 3: 创建详情/更新/删除 API**

```typescript
// web/server/api/world-builder/[id].get.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { knowledgeGraphs } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const items = await db.select().from(knowledgeGraphs)
    .where(and(eq(knowledgeGraphs.id, id), eq(knowledgeGraphs.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '图谱不存在')

  const item = items[0]
  return success({
    ...item,
    graphData: JSON.parse(item.graphData),
    metadata: item.metadata ? JSON.parse(item.metadata) : null,
  })
})
```

```typescript
// web/server/api/world-builder/[id].put.ts
import { z } from 'zod'
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { knowledgeGraphs } from '~~/server/database/schema'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100).optional(),
  description: z.string().max(500).optional(),
  graphData: z.object({
    nodes: z.array(z.any()),
    edges: z.array(z.any()),
  }).optional(),
})

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '参数错误')

  const existing = await db.select().from(knowledgeGraphs)
    .where(and(eq(knowledgeGraphs.id, id), eq(knowledgeGraphs.enterpriseId, enterpriseId)))
    .limit(1)

  if (existing.length === 0) return error(ErrorCodes.NOT_FOUND, '图谱不存在')

  const updates: any = { updatedAt: now() }
  if (parsed.data.name) updates.name = parsed.data.name
  if (parsed.data.description !== undefined) updates.description = parsed.data.description
  if (parsed.data.graphData) {
    updates.graphData = JSON.stringify(parsed.data.graphData)
    updates.nodeCount = parsed.data.graphData.nodes.length
    updates.edgeCount = parsed.data.graphData.edges.length
  }

  await db.update(knowledgeGraphs).set(updates).where(eq(knowledgeGraphs.id, id))
  return success({ id })
})
```

```typescript
// web/server/api/world-builder/[id].delete.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { knowledgeGraphs } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()

  const existing = await db.select().from(knowledgeGraphs)
    .where(and(eq(knowledgeGraphs.id, id), eq(knowledgeGraphs.enterpriseId, enterpriseId)))
    .limit(1)

  if (existing.length === 0) return error(ErrorCodes.NOT_FOUND, '图谱不存在')

  await db.delete(knowledgeGraphs).where(eq(knowledgeGraphs.id, id))
  return success({ id })
})
```

- [ ] **Step 4: 创建分析和映射子 API**

```typescript
// web/server/api/world-builder/[id]/analyze.post.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { knowledgeGraphs } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const items = await db.select().from(knowledgeGraphs)
    .where(and(eq(knowledgeGraphs.id, id), eq(knowledgeGraphs.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '图谱不存在')

  const graphData = JSON.parse(items[0].graphData)

  try {
    const result = await $fetch(`${config.engineUrl}/engine/graph/analyze`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: { graph_data: graphData },
    })

    await db.update(knowledgeGraphs).set({
      metadata: JSON.stringify(result),
    }).where(eq(knowledgeGraphs.id, id))

    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '图分析失败: ' + (e.message || ''))
  }
})
```

```typescript
// web/server/api/world-builder/[id]/to-simulation.post.ts
import { eq, and } from 'drizzle-orm'
import { useDB } from '~~/server/database'
import { knowledgeGraphs } from '~~/server/database/schema'
import { success, error, ErrorCodes } from '~~/server/utils/response'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')!
  const { enterpriseId } = event.context.user!
  const db = useDB()
  const config = useRuntimeConfig()

  const items = await db.select().from(knowledgeGraphs)
    .where(and(eq(knowledgeGraphs.id, id), eq(knowledgeGraphs.enterpriseId, enterpriseId)))
    .limit(1)

  if (items.length === 0) return error(ErrorCodes.NOT_FOUND, '图谱不存在')

  const graphData = JSON.parse(items[0].graphData)

  try {
    const result = await $fetch(`${config.engineUrl}/engine/graph/to-simulation`, {
      method: 'POST',
      headers: { 'X-Internal-Key': config.internalApiKey, 'Content-Type': 'application/json' },
      body: { graph_data: graphData },
    })
    return success(result)
  } catch (e: any) {
    return error(ErrorCodes.ENGINE_DISPATCH_FAILED, '映射失败: ' + (e.message || ''))
  }
})
```

- [ ] **Step 5: 创建导入 API**

```typescript
// web/server/api/world-builder/import.post.ts
import { z } from 'zod'
import { useDB } from '~~/server/database'
import { knowledgeGraphs, operationLogs } from '~~/server/database/schema'
import { generateId } from '~~/server/utils/id'
import { now } from '~~/server/utils/time'
import { success, error, ErrorCodes } from '~~/server/utils/response'

const bodySchema = z.object({
  name: z.string().min(1).max(100),
  graphData: z.object({
    nodes: z.array(z.any()),
    edges: z.array(z.any()),
  }),
})

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const parsed = bodySchema.safeParse(body)
  if (!parsed.success) return error(ErrorCodes.VALIDATION_ERROR, '导入数据格式错误')

  const { userId, enterpriseId } = event.context.user!
  const db = useDB()
  const timestamp = now()
  const id = generateId()

  await db.insert(knowledgeGraphs).values({
    id, enterpriseId,
    name: parsed.data.name,
    graphData: JSON.stringify(parsed.data.graphData),
    nodeCount: parsed.data.graphData.nodes.length,
    edgeCount: parsed.data.graphData.edges.length,
    createdAt: timestamp, updatedAt: timestamp,
  })

  await db.insert(operationLogs).values({
    id: generateId(), enterpriseId, userId,
    action: 'import_graph', resourceType: 'knowledge_graph', resourceId: id,
    createdAt: timestamp,
  })

  return success({ id, name: parsed.data.name, nodeCount: parsed.data.graphData.nodes.length })
})
```

- [ ] **Step 6: 提交**

```bash
git add web/server/api/world-builder/
git commit -m "feat(api): add world builder CRUD, analysis, mapping, and import endpoints"
```

---

## Task 7: Frontend Store

**Files:**
- Create: `web/app/stores/world-builder.ts`

- [ ] **Step 1: 创建 Store**

```typescript
// web/app/stores/world-builder.ts
import { defineStore } from 'pinia'

export interface GraphSummary {
  id: string
  name: string
  description: string | null
  nodeCount: number
  edgeCount: number
  createdAt: string
  updatedAt: string
}

export interface GraphDetail extends GraphSummary {
  graphData: { nodes: any[]; edges: any[] }
  metadata: any
}

export const useWorldBuilderStore = defineStore('worldBuilder', {
  state: () => ({
    items: [] as GraphSummary[],
    current: null as GraphDetail | null,
    loading: false,
  }),

  actions: {
    async fetchList() {
      this.loading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>('/api/world-builder')
        if (res.code === 0) this.items = res.data
        return res
      } finally {
        this.loading = false
      }
    },

    async fetchOne(id: string) {
      this.loading = true
      try {
        const { $api } = useApi()
        const res = await $api<any>(`/api/world-builder/${id}`)
        if (res.code === 0) this.current = res.data
        return res
      } finally {
        this.loading = false
      }
    },

    async create(name: string, description?: string) {
      const { $api } = useApi()
      return await $api<any>('/api/world-builder', {
        method: 'POST',
        body: { name, description },
      })
    },

    async update(id: string, data: any) {
      const { $api } = useApi()
      return await $api<any>(`/api/world-builder/${id}`, {
        method: 'PUT',
        body: data,
      })
    },

    async remove(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/world-builder/${id}`, { method: 'DELETE' })
    },

    async analyze(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/world-builder/${id}/analyze`, { method: 'POST' })
    },

    async toSimulation(id: string) {
      const { $api } = useApi()
      return await $api<any>(`/api/world-builder/${id}/to-simulation`, { method: 'POST' })
    },

    async importGraph(name: string, graphData: any) {
      const { $api } = useApi()
      return await $api<any>('/api/world-builder/import', {
        method: 'POST',
        body: { name, graphData },
      })
    },
  },
})
```

- [ ] **Step 2: 提交**

```bash
git add web/app/stores/world-builder.ts
git commit -m "feat(store): add world builder Pinia store"
```

---

## Task 8: 图谱编辑器核心组件

**Files:**
- Create: `web/app/components/GraphEditor.vue`
- Create: `web/app/components/GraphNodePanel.vue`
- Create: `web/app/components/GraphToolbar.vue`

- [ ] **Step 1: 创建工具栏组件**

```vue
<!-- web/app/components/GraphToolbar.vue -->
<template>
  <n-space>
    <n-dropdown :options="nodeOptions" @select="$emit('addNode', $event)">
      <n-button type="primary" size="small">添加节点</n-button>
    </n-dropdown>
    <n-button size="small" @click="$emit('autoLayout')">自动布局</n-button>
    <n-button size="small" @click="$emit('analyze')">运行分析</n-button>
    <n-button size="small" @click="$emit('exportJson')">导出 JSON</n-button>
    <n-button size="small" type="info" @click="$emit('toSimulation')">转为仿真</n-button>
  </n-space>
</template>

<script setup lang="ts">
defineEmits<{
  addNode: [type: string]
  autoLayout: []
  analyze: []
  exportJson: []
  toSimulation: []
}>()

const nodeOptions = [
  { label: '人物 (Person)', key: 'person' },
  { label: '组织 (Organization)', key: 'organization' },
  { label: '话题 (Topic)', key: 'topic' },
  { label: '社区 (Community)', key: 'community' },
  { label: '内容 (Content)', key: 'content' },
]
</script>
```

- [ ] **Step 2: 创建节点属性面板**

```vue
<!-- web/app/components/GraphNodePanel.vue -->
<template>
  <n-drawer :show="!!node" :width="320" placement="right" @update:show="$emit('close')">
    <n-drawer-content :title="node ? `编辑: ${node.label}` : ''" closable>
      <n-form v-if="node" label-placement="top" size="small">
        <n-form-item label="名称">
          <n-input v-model:value="form.label" />
        </n-form-item>
        <n-form-item label="类型">
          <n-tag :type="typeColor(node.type)" size="small">{{ typeLabel(node.type) }}</n-tag>
        </n-form-item>
        <n-form-item label="自定义属性">
          <n-dynamic-input
            v-model:value="propEntries"
            :on-create="() => ({ key: '', value: '' })"
          >
            <template #default="{ value }">
              <n-space>
                <n-input v-model:value="value.key" placeholder="键" style="width: 100px" />
                <n-input v-model:value="value.value" placeholder="值" style="width: 120px" />
              </n-space>
            </template>
          </n-dynamic-input>
        </n-form-item>
        <n-space>
          <n-button type="primary" size="small" @click="save">保存</n-button>
          <n-button type="error" size="small" @click="$emit('delete', node.id)">删除节点</n-button>
        </n-space>
      </n-form>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{ node: any | null }>()
const emit = defineEmits<{
  close: []
  save: [data: any]
  delete: [id: string]
}>()

const form = ref({ label: '' })
const propEntries = ref<{ key: string; value: string }[]>([])

watch(() => props.node, (n) => {
  if (n) {
    form.value.label = n.label
    propEntries.value = Object.entries(n.properties || {}).map(([key, value]) => ({
      key, value: String(value),
    }))
  }
}, { immediate: true })

const typeLabels: Record<string, string> = {
  person: '人物', organization: '组织', topic: '话题', community: '社区', content: '内容',
}

const typeColors: Record<string, string> = {
  person: 'info', organization: 'success', topic: 'warning', community: 'error', content: 'default',
}

function typeLabel(t: string) { return typeLabels[t] || t }
function typeColor(t: string): any { return typeColors[t] || 'default' }

function save() {
  const properties: Record<string, string> = {}
  for (const e of propEntries.value) {
    if (e.key) properties[e.key] = e.value
  }
  emit('save', { ...props.node, label: form.value.label, properties })
}
</script>
```

- [ ] **Step 3: 创建图谱编辑器核心组件**

```vue
<!-- web/app/components/GraphEditor.vue -->
<template>
  <div style="position: relative; width: 100%; height: 100%">
    <div ref="chartRef" style="width: 100%; height: 100%" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'

echarts.use([CanvasRenderer, GraphChart, TooltipComponent, LegendComponent])

interface Node { id: string; type: string; label: string; x: number; y: number; properties: any }
interface Edge { id: string; source: string; target: string; type: string; weight: number; properties: any }

const props = defineProps<{
  nodes: Node[]
  edges: Edge[]
}>()

const emit = defineEmits<{
  nodeClick: [node: Node]
  nodePositionUpdate: [id: string, x: number, y: number]
}>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const categoryColors: Record<string, string> = {
  person: '#5470c6',
  organization: '#91cc75',
  topic: '#fac858',
  community: '#ee6666',
  content: '#73c0de',
}

const categoryNames: Record<string, string> = {
  person: '人物',
  organization: '组织',
  topic: '话题',
  community: '社区',
  content: '内容',
}

function getCategories() {
  return Object.entries(categoryNames).map(([key, name]) => ({ name }))
}

function getCategoryIndex(type: string) {
  const keys = Object.keys(categoryNames)
  return keys.indexOf(type)
}

function render() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
    chart.on('click', (params: any) => {
      if (params.dataType === 'node') {
        const node = props.nodes.find(n => n.id === params.data.id)
        if (node) emit('nodeClick', node)
      }
    })
  }

  const echartsNodes = props.nodes.map(n => ({
    id: n.id,
    name: n.label,
    x: n.x || Math.random() * 600,
    y: n.y || Math.random() * 400,
    symbolSize: n.type === 'person' ? 40 : 30,
    category: getCategoryIndex(n.type),
    itemStyle: { color: categoryColors[n.type] || '#999' },
    label: { show: true, position: 'bottom', fontSize: 11 },
  }))

  const edgeTypeLabels: Record<string, string> = {
    follows: '关注', opposes: '对立', belongs_to: '隶属',
    interested_in: '兴趣', influences: '影响', publishes: '发布',
  }

  const echartsEdges = props.edges.map(e => ({
    source: e.source,
    target: e.target,
    label: { show: true, formatter: edgeTypeLabels[e.type] || e.type, fontSize: 9 },
    lineStyle: {
      width: Math.max(1, e.weight * 2),
      curveness: 0.2,
      type: e.type === 'opposes' ? 'dashed' as const : 'solid' as const,
    },
  }))

  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { data: getCategories().map(c => c.name), top: 10 },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      force: { repulsion: 200, edgeLength: [80, 200], gravity: 0.1 },
      categories: getCategories(),
      data: echartsNodes,
      links: echartsEdges,
      emphasis: { focus: 'adjacency', lineStyle: { width: 4 } },
    }],
  }, true)
}

onMounted(() => nextTick(render))
onUnmounted(() => { if (chart) { chart.dispose(); chart = null } })
watch([() => props.nodes, () => props.edges], () => nextTick(render), { deep: true })
</script>
```

- [ ] **Step 4: 提交**

```bash
git add web/app/components/GraphEditor.vue web/app/components/GraphNodePanel.vue web/app/components/GraphToolbar.vue
git commit -m "feat(ui): add graph editor, node panel, and toolbar components"
```

---

## Task 9: 图谱列表页

**Files:**
- Create: `web/app/pages/world-builder/index.vue`

- [ ] **Step 1: 创建列表页**

```vue
<!-- web/app/pages/world-builder/index.vue -->
<template>
  <div>
    <CommonPageHeader title="世界构建器" subtitle="通过知识图谱构建社交世界">
      <template #actions>
        <n-space>
          <n-button type="primary" @click="showCreate = true">新建图谱</n-button>
          <n-button @click="showImport = true">导入 JSON</n-button>
        </n-space>
      </template>
    </CommonPageHeader>

    <n-spin :show="store.loading">
      <n-empty v-if="!store.items.length && !store.loading" description="还没有图谱，创建一个开始构建世界">
        <template #extra>
          <n-button type="primary" @click="showCreate = true">新建图谱</n-button>
        </template>
      </n-empty>

      <n-grid v-if="store.items.length" :cols="3" :x-gap="16" :y-gap="16">
        <n-gi v-for="g in store.items" :key="g.id">
          <n-card hoverable style="cursor: pointer" @click="router.push(`/world-builder/${g.id}`)">
            <template #header>{{ g.name }}</template>
            <template #header-extra>
              <n-popconfirm @positive-click="handleDelete(g.id)">
                <template #trigger>
                  <n-button size="tiny" quaternary type="error" @click.stop>删除</n-button>
                </template>
                确定删除此图谱？
              </n-popconfirm>
            </template>
            <n-space vertical>
              <n-text v-if="g.description" depth="3">{{ g.description }}</n-text>
              <n-space>
                <n-tag size="small" type="info">{{ g.nodeCount }} 个节点</n-tag>
                <n-tag size="small" type="success">{{ g.edgeCount }} 条关系</n-tag>
              </n-space>
              <n-text depth="3" style="font-size: 12px">{{ formatTime(g.updatedAt) }}</n-text>
            </n-space>
          </n-card>
        </n-gi>
      </n-grid>
    </n-spin>

    <n-modal v-model:show="showCreate" title="新建图谱" preset="card" style="width: 450px">
      <n-form>
        <n-form-item label="名称">
          <n-input v-model:value="createForm.name" placeholder="输入图谱名称" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="createForm.description" type="textarea" placeholder="可选描述" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button type="primary" @click="handleCreate" :loading="creating">创建</n-button>
      </template>
    </n-modal>

    <n-modal v-model:show="showImport" title="导入图谱" preset="card" style="width: 500px">
      <n-form>
        <n-form-item label="名称">
          <n-input v-model:value="importForm.name" placeholder="图谱名称" />
        </n-form-item>
        <n-form-item label="JSON 数据">
          <n-input v-model:value="importForm.json" type="textarea" :rows="8" placeholder='{"nodes": [...], "edges": [...]}' />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button type="primary" @click="handleImport" :loading="importing">导入</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useWorldBuilderStore } from '~/stores/world-builder'

const router = useRouter()
const message = useMessage()
const store = useWorldBuilderStore()

const showCreate = ref(false)
const showImport = ref(false)
const creating = ref(false)
const importing = ref(false)
const createForm = ref({ name: '', description: '' })
const importForm = ref({ name: '', json: '' })

function formatTime(t: string) { return t ? new Date(t).toLocaleString('zh-CN') : '-' }

async function handleCreate() {
  if (!createForm.value.name) return message.warning('请输入名称')
  creating.value = true
  const res = await store.create(createForm.value.name, createForm.value.description)
  creating.value = false
  if (res.code === 0) {
    showCreate.value = false
    router.push(`/world-builder/${res.data.id}`)
  } else {
    message.error(res.message)
  }
}

async function handleImport() {
  if (!importForm.value.name || !importForm.value.json) return message.warning('请填写完整')
  importing.value = true
  try {
    const graphData = JSON.parse(importForm.value.json)
    const res = await store.importGraph(importForm.value.name, graphData)
    if (res.code === 0) {
      showImport.value = false
      message.success(`已导入 ${res.data.nodeCount} 个节点`)
      await store.fetchList()
    } else {
      message.error(res.message)
    }
  } catch {
    message.error('JSON 格式错误')
  }
  importing.value = false
}

async function handleDelete(id: string) {
  const res = await store.remove(id)
  if (res.code === 0) {
    message.success('已删除')
    await store.fetchList()
  }
}

onMounted(() => store.fetchList())
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/pages/world-builder/index.vue
git commit -m "feat(ui): add world builder listing page"
```

---

## Task 10: 图谱编辑器页面

**Files:**
- Create: `web/app/pages/world-builder/[id].vue`

- [ ] **Step 1: 创建编辑器页面**

```vue
<!-- web/app/pages/world-builder/[id].vue -->
<template>
  <div style="display: flex; flex-direction: column; height: calc(100vh - 120px)">
    <CommonPageHeader :title="store.current?.name || '图谱编辑器'">
      <template #actions>
        <GraphToolbar
          @add-node="addNode"
          @auto-layout="autoLayout"
          @analyze="runAnalyze"
          @export-json="exportJson"
          @to-simulation="toSimulation"
        />
      </template>
    </CommonPageHeader>

    <n-spin :show="store.loading" style="flex: 1; min-height: 0">
      <div style="display: flex; height: 100%">
        <div style="flex: 1; position: relative">
          <GraphEditor
            :nodes="nodes"
            :edges="edges"
            @node-click="selectedNode = $event"
          />

          <div v-if="analysisResult" style="position: absolute; bottom: 16px; left: 16px; z-index: 10">
            <n-card size="small" style="max-width: 300px; opacity: 0.95">
              <template #header>分析结果</template>
              <n-space vertical size="small">
                <n-text>节点: {{ analysisResult.node_count }} | 边: {{ analysisResult.edge_count }}</n-text>
                <n-text>密度: {{ analysisResult.density }}</n-text>
                <n-text>社区数: {{ analysisResult.communities?.length || 0 }}</n-text>
              </n-space>
            </n-card>
          </div>
        </div>
      </div>
    </n-spin>

    <GraphNodePanel
      :node="selectedNode"
      @close="selectedNode = null"
      @save="updateNode"
      @delete="deleteNode"
    />

    <n-modal v-model:show="showEdgeModal" title="添加关系" preset="card" style="width: 400px">
      <n-form>
        <n-form-item label="起点">
          <n-select v-model:value="edgeForm.source" :options="nodeSelectOptions" />
        </n-form-item>
        <n-form-item label="终点">
          <n-select v-model:value="edgeForm.target" :options="nodeSelectOptions" />
        </n-form-item>
        <n-form-item label="关系类型">
          <n-select v-model:value="edgeForm.type" :options="edgeTypeOptions" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-button type="primary" @click="addEdge">添加</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useWorldBuilderStore } from '~/stores/world-builder'

const route = useRoute()
const message = useMessage()
const store = useWorldBuilderStore()

const id = route.params.id as string
const selectedNode = ref<any>(null)
const analysisResult = ref<any>(null)
const showEdgeModal = ref(false)
const edgeForm = ref({ source: '', target: '', type: 'follows' })

const nodes = computed(() => store.current?.graphData?.nodes || [])
const edges = computed(() => store.current?.graphData?.edges || [])

const nodeSelectOptions = computed(() =>
  nodes.value.map((n: any) => ({ label: n.label, value: n.id }))
)

const edgeTypeOptions = [
  { label: '关注 (follows)', value: 'follows' },
  { label: '对立 (opposes)', value: 'opposes' },
  { label: '隶属 (belongs_to)', value: 'belongs_to' },
  { label: '兴趣 (interested_in)', value: 'interested_in' },
  { label: '影响 (influences)', value: 'influences' },
  { label: '发布 (publishes)', value: 'publishes' },
]

let counter = 0

function addNode(type: string) {
  counter++
  const typeLabels: Record<string, string> = {
    person: '人物', organization: '组织', topic: '话题', community: '社区', content: '内容',
  }
  const node = {
    id: `n_${Date.now()}_${counter}`,
    type,
    label: `${typeLabels[type] || type} ${counter}`,
    x: 300 + Math.random() * 200,
    y: 200 + Math.random() * 200,
    properties: {},
  }
  const newNodes = [...nodes.value, node]
  saveGraph(newNodes, edges.value)
  showEdgeModal.value = true
  edgeForm.value.source = node.id
}

function addEdge() {
  if (!edgeForm.value.source || !edgeForm.value.target) return message.warning('请选择起点和终点')
  if (edgeForm.value.source === edgeForm.value.target) return message.warning('不能自连接')
  const edge = {
    id: `e_${Date.now()}`,
    source: edgeForm.value.source,
    target: edgeForm.value.target,
    type: edgeForm.value.type,
    weight: 1.0,
    properties: {},
  }
  saveGraph(nodes.value, [...edges.value, edge])
  showEdgeModal.value = false
}

function updateNode(data: any) {
  const newNodes = nodes.value.map((n: any) => n.id === data.id ? data : n)
  saveGraph(newNodes, edges.value)
  selectedNode.value = null
}

function deleteNode(nodeId: string) {
  const newNodes = nodes.value.filter((n: any) => n.id !== nodeId)
  const newEdges = edges.value.filter((e: any) => e.source !== nodeId && e.target !== nodeId)
  saveGraph(newNodes, newEdges)
  selectedNode.value = null
}

function autoLayout() {
  const newNodes = nodes.value.map((n: any, i: number) => ({
    ...n,
    x: 300 + Math.cos(i * 2 * Math.PI / nodes.value.length) * 200,
    y: 300 + Math.sin(i * 2 * Math.PI / nodes.value.length) * 200,
  }))
  saveGraph(newNodes, edges.value)
}

async function saveGraph(newNodes: any[], newEdges: any[]) {
  const res = await store.update(id, {
    graphData: { nodes: newNodes, edges: newEdges },
  })
  if (res.code === 0) {
    await store.fetchOne(id)
  }
}

async function runAnalyze() {
  const res = await store.analyze(id)
  if (res.code === 0) {
    analysisResult.value = res.data
    message.success('分析完成')
  } else {
    message.error(res.message)
  }
}

function exportJson() {
  const data = JSON.stringify(store.current?.graphData || {}, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${store.current?.name || 'graph'}.json`
  a.click()
  URL.revokeObjectURL(url)
}

async function toSimulation() {
  const res = await store.toSimulation(id)
  if (res.code === 0) {
    message.success(`已生成 ${res.data.num_agents} 个 Agent 的仿真配置`)
  } else {
    message.error(res.message)
  }
}

onMounted(() => store.fetchOne(id))
</script>
```

- [ ] **Step 2: 提交**

```bash
git add web/app/pages/world-builder/[id].vue
git commit -m "feat(ui): add world builder graph editor page"
```

---

## Task 11: 侧边栏导航

**Files:**
- Modify: `web/app/components/layout/Sidebar.vue`

- [ ] **Step 1: 添加世界构建器导航项**

在 menuItems 数组中 `深度分析` 项之后添加：

```typescript
{ path: '/world-builder', icon: 'carbon:network-3-reference', label: '世界构建' },
```

- [ ] **Step 2: 提交**

```bash
git add web/app/components/layout/Sidebar.vue
git commit -m "feat(ui): add world builder navigation to sidebar"
```

---

## Task 12: 最终审查

- [ ] **Step 1: 验证所有文件**

检查:
1. Engine graph 模块所有文件存在且导出正确
2. 数据库表在 sqlite/pg/index 中一致
3. 所有 API 端点有 enterpriseId 隔离
4. 前端组件正确引用

- [ ] **Step 2: 最终提交**

```bash
git add -A
git commit -m "feat(world-builder): complete P1-1 knowledge graph world builder"
```
