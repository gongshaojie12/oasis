# OASIS 平台功能扩展设计方案

> 日期：2026-04-20  
> 版本：v1.0  
> 分支：dev-0.0.1  
> 状态：设计评审中

---

## 一、项目背景

### 1.1 当前状态

OASIS（Open Agent Social Interaction Simulations）是一个基于 LLM 的多 Agent 社交媒体仿真平台，当前已具备：

- **8 个社交平台**仿真支持（Twitter、Reddit、微博、小红书、抖音、快手、B站、微信视频号）
- **6 种业务类型**（营销仿真、舆情预测、推荐系统测试、学术研究、数字孪生、合成数据）
- **28+ 种 Agent 行为**（发帖、评论、点赞、转发、关注等）
- **7 个 LLM 供应商**集成（Deepseek、通义千问、豆包、MiniMax、智谱、Kimi、OpenAI）
- **Web 管理后台**（Nuxt 4 + Naive UI）
- **引擎服务**（FastAPI + 异步任务队列）
- **企业管理**（配额、计费、审计日志）
- **模板系统**（Agent 模板、仿真模板）

### 1.2 待提升方向

| 方向 | 当前状态 | 目标状态 |
|------|----------|----------|
| Agent 生成 | 手动编辑 JSON Profile | 多源智能生成 + 群体繁殖 |
| 仿真报告 | 自动生成基础 JSON + 简单图表 | 多视角辩论分析 + 交互式图表 |
| 知识图谱 | Neo4j 已集成但未启用 | 可视化世界构建器 |
| 深度交互 | 仅 engine 层 interview 功能 | 时间机器 + What-If 分支 |
| 国际化 | 纯中文 | 中英文切换 |
| 场景配置 | 手动填写参数 | 自然语言 → 结构化参数 |
| 工作流 | 列表 + 详情页 | 自适应任务控制中心 |
| 仿真控制 | SSE 单向进度 + 取消 | WebSocket 双向实时控制 |

### 1.3 差异化策略

本方案借鉴了同类产品的功能思路，但在架构和实现上进行了原创设计，核心差异化点：

| 维度 | 同类产品常见做法 | 我们的创新 |
|------|------------------|------------|
| Profile 生成 | 从文档单一来源抽取 | **多源输入 + 人格基因组编码 + 群体繁殖** |
| 报告分析 | 单 Agent ReACT 模式 | **多分析师辩论 + 时间线叙事** |
| 知识图谱 | 依赖外部 SaaS（如 Zep Cloud） | **本地 Neo4j + 可视化节点编辑器** |
| 深度交互 | 仿真后静态对话 | **时间轴回溯 + What-If 分支仿真** |
| 场景配置 | 纯 LLM 生成参数 | **自然语言映射 + 场景 DNA 混合** |
| 工作流 | 线性固定步骤 | **自适应仪表盘 + 仿真健康度** |
| 仿真控制 | 子进程 IPC（暂停/停止） | **WebSocket 双向 + 中途事件注入** |

---

## 二、功能设计

---

### P0-1：人格基因组（Persona Genome）— 智能 Agent Profile 生成

#### 2.1.1 概述

将 Agent 的人格特征结构化为一套可量化、可遗传、可变异的"基因组"编码。支持从多种数据源提取种子人格，并通过"繁殖"和"突变"算法批量生成大规模多样化 Agent 群体。

#### 2.1.2 核心概念

**人格基因组结构：**

```json
{
  "genome_id": "pg_001",
  "version": 1,
  "traits": {
    "openness": 0.82,
    "conscientiousness": 0.65,
    "extraversion": 0.71,
    "agreeableness": 0.45,
    "neuroticism": 0.33
  },
  "social_behavior": {
    "activity_level": 0.8,
    "content_creation_ratio": 0.6,
    "interaction_preference": "reply_heavy",
    "influence_weight": 0.7,
    "echo_chamber_tendency": 0.4
  },
  "opinion_spectrum": {
    "topic_stances": {
      "新能源汽车": 0.85,
      "人工智能监管": -0.3
    },
    "persuadability": 0.4,
    "stance_volatility": 0.2
  },
  "demographics": {
    "age_range": [25, 35],
    "profession": "software_engineer",
    "interests": ["technology", "gaming", "finance"],
    "mbti": "INTJ"
  },
  "behavioral_patterns": {
    "peak_activity_hours": [9, 12, 20, 23],
    "avg_post_length": "medium",
    "emoji_usage": 0.3,
    "hashtag_usage": 0.5
  }
}
```

#### 2.1.3 多源输入

| 输入源 | 说明 | 提取方式 |
|--------|------|----------|
| **文档上传** | PDF、Markdown、TXT | LLM 提取人物特征并映射到基因组 |
| **URL 抓取** | 网页内容 | Web Fetch + LLM 分析 |
| **CSV/JSON 批量导入** | 结构化数据 | 字段映射 + 缺失值 LLM 补全 |
| **自然语言描述** | 用户口头描述人群画像 | LLM 解析为基因组参数 |
| **历史仿真数据** | 过往仿真中表现突出的 Agent | 从 trace 表反向提取行为模式 |

#### 2.1.4 群体繁殖算法

```
输入：N 个种子基因组 + 目标数量 M + 突变率 μ
输出：M 个多样化基因组

算法：
1. 选择繁殖策略：
   - 克隆突变（单亲 + 随机扰动）
   - 交叉繁殖（双亲特质混合）
   - 分布采样（基于种子统计分布生成新个体）

2. 对每个新个体：
   a. 从种子池随机选取 1-2 个父本
   b. 基因交叉：各维度按权重混合
   c. 突变：以概率 μ 对各维度添加高斯噪声
   d. 约束校验：确保值在合理范围内
   e. 一致性检查：确保特质组合逻辑自洽

3. 群体多样性检验：
   - 计算群体内基因组的方差
   - 若多样性低于阈值，增大突变率重试
```

#### 2.1.5 群体画像预览

生成前提供可视化预览：

- **雷达图**：五大人格特质分布
- **散点图**：观点光谱二维投影
- **直方图**：年龄、活跃度、影响力分布
- **热力图**：特质间相关性矩阵

用户可调整参数后实时刷新预览，满意后确认生成。

#### 2.1.6 技术实现

**新增数据库表：**

```sql
-- 人格基因组模板表
CREATE TABLE persona_genomes (
  id TEXT PRIMARY KEY,
  enterprise_id TEXT NOT NULL,
  name TEXT NOT NULL,
  source_type TEXT NOT NULL,  -- 'document', 'url', 'csv', 'manual', 'trace'
  genome_data JSON NOT NULL,
  tags JSON,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

-- 基因组批次表（繁殖任务）
CREATE TABLE genome_batches (
  id TEXT PRIMARY KEY,
  enterprise_id TEXT NOT NULL,
  seed_genome_ids JSON NOT NULL,
  target_count INTEGER NOT NULL,
  mutation_rate REAL DEFAULT 0.15,
  strategy TEXT DEFAULT 'crossover',  -- 'clone_mutate', 'crossover', 'distribution'
  status TEXT DEFAULT 'pending',
  result_genome_ids JSON,
  created_at INTEGER NOT NULL
);
```

**新增 API 端点：**

```
POST   /api/genomes/extract       — 从数据源提取基因组
POST   /api/genomes/breed         — 批量繁殖
GET    /api/genomes               — 列表
GET    /api/genomes/:id           — 详情
PUT    /api/genomes/:id           — 编辑
DELETE /api/genomes/:id           — 删除
GET    /api/genomes/preview       — 群体画像预览
POST   /api/genomes/to-profiles   — 基因组 → OASIS Agent Profile 转换
```

**新增前端页面：**

- `/genomes` — 基因组管理列表
- `/genomes/create` — 多源输入创建
- `/genomes/breed` — 群体繁殖配置 + 预览
- `/genomes/:id` — 基因组详情 + 编辑

---

### P0-2：多视角辩论分析（Multi-Analyst Debate）— 智能报告系统

#### 2.2.1 概述

仿真完成后，由多个 AI 分析师角色独立分析仿真数据，然后进行交叉辩论，最终综合产出深度报告。报告包含时间线叙事、交互式图表和多维度洞察。

#### 2.2.2 分析师角色设计

| 角色 | 视角 | 关注点 |
|------|------|--------|
| **数据分析师** (Data Analyst) | 定量分析 | 数据趋势、统计指标、异常检测 |
| **社会学家** (Sociologist) | 群体行为 | 群体极化、信息茧房、舆论演化 |
| **心理学家** (Psychologist) | 个体动机 | Agent 行为动机、情感变化、认知偏差 |
| **魔鬼代言人** (Devil's Advocate) | 反面论证 | 挑战其他分析师的结论、提出替代解释 |

#### 2.2.3 辩论流程

```
阶段一：独立分析（并行）
├── 数据分析师 → 读取 trace 数据 → 生成定量分析报告
├── 社会学家 → 读取社交网络数据 → 生成群体行为分析
├── 心理学家 → 读取 Agent 行为序列 → 生成个体分析
└── 魔鬼代言人 → 等待其他三位的初步结论

阶段二：交叉辩论（串行，2-3 轮）
├── 轮次 1：各分析师阅读他人报告，提出质疑和补充
├── 轮次 2：回应质疑，修正或坚持观点
└── 轮次 3（可选）：魔鬼代言人做最终挑战

阶段三：综合报告（串行）
├── 主持人 Agent 综合所有分析和辩论
├── 生成结构化报告（共识、分歧、开放问题）
└── 附录：各分析师的原始报告 + 辩论记录
```

#### 2.2.4 报告结构

```markdown
# 仿真分析报告

## 执行摘要
  - 一段话总结核心发现

## 时间线叙事
  - 按仿真轮次展开的"故事"
  - 关键转折点标注
  - 信息传播路径可视化

## 多维度分析
  ### 数据视角
    - 统计指标与趋势图表（可交互）
    - 异常点标注与解释
  ### 社会学视角
    - 群体极化分析
    - 信息茧房检测
    - 舆论领袖识别
  ### 心理学视角
    - 典型 Agent 行为剖析
    - 情感变化轨迹
    - 认知偏差案例

## 辩论要点
  - 共识结论
  - 分歧观点（含双方论据）
  - 开放问题

## 可交互图表仪表盘
  - 情感走势折线图
  - 传播网络力导向图
  - Agent 影响力排行榜
  - 话题热度时序图

## 附录
  - 各分析师原始报告
  - 辩论完整记录
  - 原始数据摘要
```

#### 2.2.5 对比分析功能

支持多次仿真结果横向对比：

- 选择 2-N 个已完成的仿真
- 自动对齐时间线
- 并排展示关键指标差异
- LLM 生成差异分析摘要

#### 2.2.6 技术实现

**新增数据库表：**

```sql
-- 分析报告表（扩展现有 reports 表）
CREATE TABLE analysis_reports (
  id TEXT PRIMARY KEY,
  simulation_id TEXT NOT NULL,
  enterprise_id TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  -- 各分析师的独立报告
  analyst_reports JSON,
  -- 辩论记录
  debate_log JSON,
  -- 综合报告
  final_report JSON,
  -- 交互式图表数据
  chart_data JSON,
  -- 时间线叙事数据
  timeline_data JSON,
  created_at INTEGER NOT NULL,
  completed_at INTEGER
);

-- 报告对比表
CREATE TABLE report_comparisons (
  id TEXT PRIMARY KEY,
  enterprise_id TEXT NOT NULL,
  report_ids JSON NOT NULL,
  comparison_data JSON,
  created_at INTEGER NOT NULL
);
```

**新增 API 端点：**

```
POST   /api/analysis/generate          — 触发多视角分析（异步）
GET    /api/analysis/:id/status        — 查询分析进度
GET    /api/analysis/:id               — 获取完整报告
GET    /api/analysis/:id/timeline      — 获取时间线叙事
GET    /api/analysis/:id/charts        — 获取图表数据
GET    /api/analysis/:id/debate        — 获取辩论记录
POST   /api/analysis/compare           — 创建对比分析
```

**新增前端页面：**

- `/analysis/:id` — 报告详情（含交互式图表、时间线、辩论记录）
- `/analysis/compare` — 多仿真对比视图

**Engine 新增模块：**

```
engine/
├── analysts/
│   ├── base.py            — 分析师基类
│   ├── data_analyst.py    — 数据分析师
│   ├── sociologist.py     — 社会学家
│   ├── psychologist.py    — 心理学家
│   ├── devils_advocate.py — 魔鬼代言人
│   ├── moderator.py       — 主持人（综合报告）
│   └── debate.py          — 辩论引擎
```

---

### P1-1：世界构建器（World Builder）— 知识图谱

#### 2.3.1 概述

激活 OASIS 已有的 Neo4j 集成，构建可视化的"世界构建器"。用户通过拖拽式节点编辑器构建社交世界的知识结构，包括人物关系网络、组织架构、话题关联等。全部本地化运行，无需外部 SaaS 依赖。

#### 2.3.2 核心功能

**节点类型：**

| 节点类型 | 说明 | 示例 |
|----------|------|------|
| Person | 人物实体 | KOL、普通用户、组织代表 |
| Organization | 组织机构 | 公司、媒体、政府机构 |
| Topic | 话题/事件 | 热搜话题、新闻事件 |
| Community | 社区/群组 | 粉丝群、兴趣小组 |
| Content | 内容节点 | 种子帖子、关键文章 |

**关系类型：**

| 关系 | 说明 | 属性 |
|------|------|------|
| FOLLOWS | 关注关系 | weight（亲密度） |
| OPPOSES | 对立关系 | intensity（对立程度） |
| BELONGS_TO | 隶属关系 | role（角色） |
| INTERESTED_IN | 兴趣关联 | strength（兴趣强度） |
| INFLUENCES | 影响关系 | direction, weight |
| PUBLISHES | 发布关系 | — |

**可视化编辑器功能：**

- 拖拽创建节点
- 连线定义关系
- 节点属性面板（双击编辑）
- 自动布局算法（力导向、层次、圆形）
- 缩放、平移、框选
- 子图筛选（按节点类型、关系类型）
- 导入/导出（JSON 格式）

#### 2.3.3 社会织网模型

在基础图谱之上，构建社会动力学模型：

- **影响力流向分析**：基于 PageRank 变体计算节点影响力
- **观点聚类**：将持相似立场的 Agent 自动聚类并可视化
- **信息传播路径预测**：基于图结构预测信息从源头到各节点的传播路径
- **社区检测**：自动发现紧密连接的社区结构

#### 2.3.4 图谱 → 仿真映射

知识图谱可直接转化为仿真配置：

```
图谱节点（Person） → Agent Profile（人格基因组）
图谱关系（FOLLOWS） → Agent 初始关注列表
图谱节点（Topic） → 种子内容 + 事件注入
图谱节点（Community） → 仿真中的群组配置
图谱关系（INFLUENCES） → Agent 影响力权重
```

#### 2.3.5 技术实现

**依赖：**
- Neo4j 5.x（已在 pyproject.toml 中）
- D3.js 或 vis-network（前端图谱渲染）
- igraph（已有，用于图分析算法）

**新增 API 端点：**

```
POST   /api/world-builder/graphs          — 创建图谱
GET    /api/world-builder/graphs          — 图谱列表
GET    /api/world-builder/graphs/:id      — 图谱详情 + 数据
PUT    /api/world-builder/graphs/:id      — 更新图谱
DELETE /api/world-builder/graphs/:id      — 删除图谱

POST   /api/world-builder/graphs/:id/nodes    — 添加节点
PUT    /api/world-builder/graphs/:id/nodes/:nid — 更新节点
DELETE /api/world-builder/graphs/:id/nodes/:nid — 删除节点
POST   /api/world-builder/graphs/:id/edges    — 添加关系
DELETE /api/world-builder/graphs/:id/edges/:eid — 删除关系

POST   /api/world-builder/graphs/:id/analyze  — 运行社会织网分析
POST   /api/world-builder/graphs/:id/to-simulation — 图谱 → 仿真配置
POST   /api/world-builder/import               — 导入图谱（JSON/文档）
GET    /api/world-builder/graphs/:id/export    — 导出图谱
```

**新增前端页面：**

- `/world-builder` — 图谱列表
- `/world-builder/:id` — 可视化节点编辑器
- `/world-builder/import` — 导入向导

**新增数据库表：**

```sql
CREATE TABLE knowledge_graphs (
  id TEXT PRIMARY KEY,
  enterprise_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  node_count INTEGER DEFAULT 0,
  edge_count INTEGER DEFAULT 0,
  neo4j_graph_id TEXT,
  metadata JSON,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
```

---

### P1-2：时间机器（Time Machine）— 深度交互

#### 2.4.1 概述

提供时间轴回溯和 What-If 分支能力。用户可以"穿越"到仿真的任意时刻，与当时状态的 Agent 对话，或者创建分支运行平行仿真。

#### 2.4.2 时间轴回溯

**核心机制：**

仿真过程中，每一轮的完整状态被快照保存：

```json
{
  "round": 5,
  "timestamp": "2026-04-20T10:30:00Z",
  "snapshot": {
    "posts": [...],
    "agent_states": {
      "agent_001": {
        "follower_count": 125,
        "post_count": 8,
        "recent_actions": ["CREATE_POST", "LIKE_POST"],
        "sentiment": 0.65,
        "current_stance": {"新能源汽车": 0.8}
      }
    },
    "platform_metrics": {
      "total_posts": 342,
      "total_interactions": 1205,
      "trending_topics": ["#新能源"]
    }
  }
}
```

**交互方式：**

- 拖动时间轴滑块到任意轮次
- 页面展示该时刻的平台快照（帖子流、热搜、统计指标）
- 点击任意 Agent 头像开始对话
- Agent 的回答基于该时刻的状态和记忆（不包含未来信息）

#### 2.4.3 What-If 分支

```
原始仿真时间线：  ●—●—●—●—●—●—●—●—●—●
                              ↑
                        用户在第5轮创建分支
                              │
分支仿真：                    ●—●—●—●—●
                        （注入不同事件后重新运行）
```

**分支操作：**

1. 选择时间轴上的任意轮次作为分支点
2. 配置分支条件：
   - 注入新事件（如"某KOL发布爆炸性言论"）
   - 修改某个 Agent 的立场或行为
   - 添加/移除 Agent
   - 改变推荐算法参数
3. 运行分支仿真（从分支点继续）
4. 对比原始和分支的结果差异

#### 2.4.4 群体圆桌会议

同时邀请多个 Agent 进行"圆桌讨论"：

- 用户设定讨论话题
- 选择 2-8 个 Agent 参与
- Agent 基于各自人格和当前状态进行多轮对话
- 用户可随时插入提问或引导话题

#### 2.4.5 情境重放

仿真过程的"视频回放"：

- 按轮次自动播放，展示每轮的帖子流和互动
- 高亮关键事件（爆款帖子、舆论转折点）
- 播放速度控制（0.5x - 4x）
- 可暂停在任意时刻查看详情

#### 2.4.6 技术实现

**新增数据库表：**

```sql
-- 仿真快照表
CREATE TABLE simulation_snapshots (
  id TEXT PRIMARY KEY,
  simulation_id TEXT NOT NULL,
  round_number INTEGER NOT NULL,
  snapshot_data JSON NOT NULL,  -- 压缩存储
  created_at INTEGER NOT NULL,
  UNIQUE(simulation_id, round_number)
);

-- What-If 分支表
CREATE TABLE simulation_branches (
  id TEXT PRIMARY KEY,
  parent_simulation_id TEXT NOT NULL,
  branch_point_round INTEGER NOT NULL,
  branch_config JSON NOT NULL,  -- 分支条件配置
  child_simulation_id TEXT,     -- 分支仿真的 ID
  status TEXT DEFAULT 'pending',
  created_at INTEGER NOT NULL
);

-- 对话记录表
CREATE TABLE agent_conversations (
  id TEXT PRIMARY KEY,
  simulation_id TEXT NOT NULL,
  round_context INTEGER NOT NULL,  -- 对话基于哪一轮的状态
  participants JSON NOT NULL,      -- 参与的 Agent IDs
  messages JSON NOT NULL,
  conversation_type TEXT NOT NULL,  -- 'interview', 'roundtable'
  created_at INTEGER NOT NULL
);
```

**新增 API 端点：**

```
GET    /api/timemachine/:simId/snapshots           — 获取快照列表
GET    /api/timemachine/:simId/snapshots/:round     — 获取特定轮次快照
POST   /api/timemachine/:simId/branch               — 创建 What-If 分支
GET    /api/timemachine/:simId/branches              — 获取分支列表
POST   /api/timemachine/:simId/chat                  — 与 Agent 对话（指定轮次上下文）
POST   /api/timemachine/:simId/roundtable            — 发起圆桌会议
GET    /api/timemachine/:simId/replay                — 获取重放数据
```

**新增前端页面：**

- `/simulations/:id/timemachine` — 时间机器主界面（时间轴 + 快照 + 对话）
- `/simulations/:id/branches` — 分支管理与对比
- `/simulations/:id/replay` — 情境重放播放器

---

### P2-1：国际化（i18n）

#### 2.5.1 概述

为整个 Web 前端添加中英文国际化支持，采用 Vue i18n 方案。

#### 2.5.2 实现方案

**技术选型：**

- `@nuxtjs/i18n` — Nuxt 官方 i18n 模块
- 语言检测策略：浏览器语言 → 用户偏好 → 默认中文

**语言文件结构：**

```
web/
├── i18n/
│   ├── locales/
│   │   ├── zh-CN.json    — 简体中文
│   │   └── en-US.json    — 英文
│   └── config.ts         — i18n 配置
```

**翻译范围：**

| 模块 | 预估词条数 |
|------|-----------|
| 通用（导航、按钮、状态） | ~100 |
| 仪表盘 | ~30 |
| 仿真管理 | ~80 |
| 报告 | ~50 |
| 模板 | ~40 |
| 设置 | ~60 |
| 新增功能（基因组、时间机器等） | ~200 |
| **合计** | **~560** |

**语言切换组件：**

- 在 Header 组件中添加语言切换下拉框
- 切换后持久化到 localStorage + 用户偏好设置
- 无需刷新页面即可切换

#### 2.5.3 注意事项

- 日期时间格式国际化（dayjs locale）
- 数字格式（千分位分隔符）
- API 错误信息国际化（后端返回错误码，前端映射文案）
- ECharts 图表文案国际化

---

### P2-2：场景作曲家（Scenario Composer）— 动态配置生成

#### 2.6.1 概述

用自然语言描述仿真场景，AI 自动映射为完整的仿真配置参数。支持场景模板混合（"场景 DNA"）、参数可视化调优和智能推荐。

#### 2.6.2 核心流程

```
用户输入自然语言
    ↓
LLM 解析意图
    ↓
映射到结构化配置
    ↓
展示可视化参数面板
    ↓
用户微调参数
    ↓
生成最终仿真配置
```

**示例：**

用户输入：
> "模拟一场关于新能源汽车补贴政策取消的微博舆论战，大约 500 个用户，持续 3 天，要有明显的支持和反对两派"

AI 映射结果：

```json
{
  "platform": "weibo",
  "num_agents": 500,
  "num_steps": 72,
  "seed_content": "重磅！新能源汽车购置补贴将于下月全面取消...",
  "agent_distribution": {
    "supporters": { "ratio": 0.4, "stance_range": [0.5, 0.9] },
    "opponents": { "ratio": 0.4, "stance_range": [-0.9, -0.5] },
    "neutrals": { "ratio": 0.2, "stance_range": [-0.2, 0.2] }
  },
  "event_injections": [
    { "round": 24, "content": "权威媒体发布详细政策解读" },
    { "round": 48, "content": "车企回应：将自行承担部分补贴" }
  ],
  "available_actions": ["CREATE_POST", "COMMENT", "LIKE", "REPOST", "FOLLOW"]
}
```

#### 2.6.3 场景 DNA 混合

每个场景模板有一组"DNA"编码：

```json
{
  "scenario_dna": {
    "conflict_level": 0.8,
    "information_density": 0.6,
    "viral_potential": 0.7,
    "sentiment_polarity": 0.9,
    "temporal_dynamics": "escalation",
    "agent_diversity": 0.7,
    "platform_fit": ["weibo", "twitter"]
  }
}
```

混合示例：
- **场景A**（电商营销）DNA + **场景B**（舆论危机）DNA → 新场景（产品公关危机营销应对）
- 按比例混合各维度参数，LLM 补全混合后的具体配置

#### 2.6.4 参数可视化调优

生成配置后展示可视化面板：

- **滑块**：Agent 数量、仿真轮次、突变率
- **饼图**：Agent 立场分布（实时更新）
- **时间轴编辑器**：拖拽调整事件注入时机
- **雷达图**：场景 DNA 维度展示
- **预估面板**：预估 LLM 调用次数、耗时、Token 消耗

#### 2.6.5 技术实现

**新增 API 端点：**

```
POST   /api/composer/parse       — 自然语言 → 结构化配置
POST   /api/composer/mix         — 场景 DNA 混合
GET    /api/composer/recommend   — 基于历史推荐场景
POST   /api/composer/estimate    — 预估资源消耗
```

**新增前端：**

- 在 `/simulations/create` 页面新增"AI 编排"模式
- 场景 DNA 可视化混合器组件
- 参数可视化调优面板组件

---

### P3-1：任务控制中心（Mission Control）— 引导式工作流

#### 2.7.1 概述

将 Dashboard 升级为自适应的"任务控制中心"，根据仿真生命周期阶段自动切换视图，提供仿真健康度指标和快捷操作。

#### 2.7.2 生命周期阶段

| 阶段 | 视图 | 核心信息 |
|------|------|----------|
| **准备** (Prepare) | 配置概览 + 资源就绪状态 | Agent 数量、LLM 可用性、配额余量 |
| **发射** (Launch) | 倒计时 + 发射按钮 | 最终配置确认、预估耗时 |
| **监控** (Monitor) | 实时仪表盘 | 进度、健康度、实时数据流 |
| **分析** (Analyze) | 报告 + 交互入口 | 分析报告、时间机器、对比 |

#### 2.7.3 仿真健康度指标

实时监控仿真运行状态：

```json
{
  "health_score": 0.85,
  "indicators": {
    "agent_activity": 0.92,    // Agent 活跃比例
    "response_quality": 0.78,  // LLM 响应质量评分
    "action_diversity": 0.85,  // 行为多样性（非全做同一操作）
    "system_load": 0.65,       // 系统负载
    "error_rate": 0.02         // 错误率
  }
}
```

健康度低于阈值时自动告警，建议用户调整参数或暂停仿真。

#### 2.7.4 快捷操作中心

根据当前上下文显示最相关的操作：

- **无仿真时**：创建新仿真、导入模板、管理 Agent
- **仿真运行中**：查看进度、暂停/恢复、注入事件
- **仿真完成后**：查看报告、进入时间机器、创建分支、开始对比分析

#### 2.7.5 技术实现

- 改造现有 `/dashboard` 页面
- 新增 `MissionControl.vue` 组件
- 新增 `HealthIndicator.vue` 组件
- 新增 `QuickActions.vue` 组件
- 新增 API：`GET /api/simulations/:id/health` — 实时健康度数据

---

### P3-2：直播控制台（Live Control Panel）— 仿真实时控制

#### 2.8.1 概述

将现有的 SSE 单向进度推送升级为 WebSocket 双向通信，支持仿真运行中的实时控制操作，包括暂停/恢复、速度调节、事件注入和实时数据流。

#### 2.8.2 WebSocket 协议

**消息格式：**

```typescript
interface WSMessage {
  type: 'command' | 'event' | 'data' | 'status';
  payload: any;
  timestamp: number;
}
```

**下行消息（Server → Client）：**

| type | 说明 | payload |
|------|------|---------|
| `status` | 仿真状态更新 | `{ status, round, progress }` |
| `data:post` | 新帖子产生 | `{ post }` |
| `data:action` | Agent 行为 | `{ agent_id, action, params }` |
| `data:metrics` | 实时指标 | `{ metrics }` |
| `data:health` | 健康度更新 | `{ health_score, indicators }` |

**上行消息（Client → Server）：**

| type | 说明 | payload |
|------|------|---------|
| `command:pause` | 暂停仿真 | — |
| `command:resume` | 恢复仿真 | — |
| `command:speed` | 调整速度 | `{ speed: 0.5 | 1 | 2 | 4 }` |
| `command:inject` | 注入事件 | `{ content, agent_id? }` |
| `command:step` | 单步执行 | — |

#### 2.8.3 中途事件注入

在仿真运行过程中，用户可以注入以下类型的事件：

| 事件类型 | 说明 | 示例 |
|----------|------|------|
| **突发新闻** | 以系统帖子形式出现 | "央视发布重磅新闻..." |
| **KOL 入场** | 动态添加高影响力 Agent | 添加一个大V进入讨论 |
| **话题热搜** | 强制推送特定话题到推荐 | 某话题突然上热搜 |
| **Agent 行为触发** | 让特定 Agent 执行指定操作 | 让某 Agent 发表特定言论 |
| **参数调整** | 修改推荐算法参数 | 改变推荐的随机vs个性化比例 |

#### 2.8.4 实时数据流展示

仿真运行时展示实时数据：

- **帖子流**：实时滚动显示新产生的帖子
- **情感仪表盘**：实时更新的群体情感指标
- **网络拓扑**：实时演化的关注网络（简化版）
- **行为分布**：当前轮次的行为类型分布饼图

#### 2.8.5 技术实现

**Engine 侧：**

```
engine/
├── websocket/
│   ├── handler.py      — WebSocket 连接管理
│   ├── protocol.py     — 消息协议定义
│   └── commands.py     — 命令处理器
```

- FastAPI 原生支持 WebSocket
- 在 SimulationRunner 中添加命令队列
- 每轮执行前检查命令队列（暂停/事件注入/速度变更）

**Web 侧：**

- 新增 `useWebSocket.ts` composable（替代 `useSSE.ts`）
- 新增 `LiveControlPanel.vue` 组件
- 新增 `PostStream.vue` 实时帖子流组件
- 新增 `EventInjector.vue` 事件注入面板
- SSE 保留作为降级方案（WebSocket 不可用时回退）

---

## 三、架构总览

### 3.1 系统架构

```
┌─────────────────────────────────────────────────┐
│                   前端 (Nuxt 4)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ 任务控制  │ │ 世界构建  │ │ 时间机器/控制台  │ │
│  │  中心     │ │   器     │ │                  │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ 人格基因  │ │ 场景作曲  │ │  报告/分析       │ │
│  │   组     │ │   家     │ │                  │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│                    │ HTTP + WebSocket             │
└────────────────────┼────────────────────────────┘
                     │
┌────────────────────┼────────────────────────────┐
│             Nuxt Server (h3)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Auth API │ │ CRUD API │ │  WebSocket Proxy │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────────┐  ┌────────────────────────┐   │
│  │ SQLite/PG DB │  │ Neo4j Client           │   │
│  │ (Drizzle)    │  │ (图谱存储)              │   │
│  └──────────────┘  └────────────────────────┘   │
│                    │ HTTP + WebSocket             │
└────────────────────┼────────────────────────────┘
                     │
┌────────────────────┼────────────────────────────┐
│            Engine (FastAPI)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ 任务队列  │ │ 仿真运行  │ │ WebSocket 管理  │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ 基因组引擎│ │ 分析师团队│ │ 快照管理        │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│                    │                             │
│           ┌────────┴────────┐                    │
│           │  OASIS Core     │                    │
│           │  (多Agent仿真)   │                    │
│           └─────────────────┘                    │
└──────────────────────────────────────────────────┘
```

### 3.2 数据流

```
多源数据 → 人格基因组引擎 → Agent Profiles
                                    ↓
知识图谱 → 世界构建器 → 仿真配置  ←  场景作曲家 ← 自然语言
                          ↓
                     仿真运行 ←→ 直播控制台（WebSocket）
                          ↓
                     快照存储 → 时间机器
                          ↓
                     分析师辩论 → 多维报告 → 交互式探索
```

### 3.3 新增依赖

**前端：**

| 包名 | 用途 | 版本 |
|------|------|------|
| `@nuxtjs/i18n` | 国际化 | latest |
| `vis-network` | 图谱可视化编辑器 | latest |
| `echarts-wordcloud` | 词云图表 | latest |

**Engine (Python)：**

| 包名 | 用途 |
|------|------|
| `websockets` | WebSocket 支持（FastAPI 内置） |
| `PyMuPDF (fitz)` | PDF 文本提取 |
| `beautifulsoup4` | URL 内容抓取 |
| `chardet` | 编码检测 |

---

## 四、分阶段实施计划

### Phase 0（P0）— 核心价值

**目标：** 完成人格基因组 + 多视角辩论报告  
**预估工作量：** 大  

| 步骤 | 内容 | 涉及层 |
|------|------|--------|
| 0.1 | 人格基因组数据模型 + 数据库表 | Server |
| 0.2 | 基因组提取 API（多源输入） | Engine + Server |
| 0.3 | 群体繁殖算法实现 | Engine |
| 0.4 | 基因组管理前端页面 | Frontend |
| 0.5 | 群体画像预览组件 | Frontend |
| 0.6 | 分析师角色定义 + 辩论引擎 | Engine |
| 0.7 | 多视角报告生成 API | Engine + Server |
| 0.8 | 报告详情页升级（交互式图表 + 时间线） | Frontend |
| 0.9 | 报告对比功能 | Server + Frontend |
| 0.10 | 集成测试 | All |

### Phase 1（P1）— 体验升级

**目标：** 完成世界构建器 + 时间机器  
**预估工作量：** 大  
**依赖：** P0 完成

| 步骤 | 内容 | 涉及层 |
|------|------|--------|
| 1.1 | 激活 Neo4j 集成 + 图谱数据模型 | Engine + Server |
| 1.2 | 可视化节点编辑器（vis-network） | Frontend |
| 1.3 | 社会织网分析算法 | Engine |
| 1.4 | 图谱 → 仿真配置转换 | Engine + Server |
| 1.5 | 仿真快照存储机制 | Engine |
| 1.6 | 时间轴回溯 UI + Agent 对话 | Frontend + Server |
| 1.7 | What-If 分支创建与运行 | Engine + Server |
| 1.8 | 圆桌会议功能 | Engine + Server + Frontend |
| 1.9 | 情境重放播放器 | Frontend |
| 1.10 | 集成测试 | All |

### Phase 2（P2）— 易用性

**目标：** 完成 i18n + 场景作曲家  
**预估工作量：** 中  
**依赖：** P0 完成（P1 可并行）

| 步骤 | 内容 | 涉及层 |
|------|------|--------|
| 2.1 | i18n 基础设施搭建 | Frontend |
| 2.2 | 提取全部硬编码中文为语言键 | Frontend |
| 2.3 | 英文翻译 | Frontend |
| 2.4 | 语言切换组件 + 持久化 | Frontend |
| 2.5 | 自然语言解析 API | Engine + Server |
| 2.6 | 场景 DNA 模型 + 混合算法 | Engine |
| 2.7 | 场景作曲家 UI（AI 编排模式） | Frontend |
| 2.8 | 参数可视化调优面板 | Frontend |
| 2.9 | 历史场景智能推荐 | Server |
| 2.10 | 集成测试 | All |

### Phase 3（P3）— 体验打磨

**目标：** 完成任务控制中心 + 直播控制台  
**预估工作量：** 中  
**依赖：** P0、P1 完成

| 步骤 | 内容 | 涉及层 |
|------|------|--------|
| 3.1 | Dashboard → 任务控制中心改造 | Frontend |
| 3.2 | 仿真健康度指标 API | Engine + Server |
| 3.3 | 自适应视图切换逻辑 | Frontend |
| 3.4 | 快捷操作中心组件 | Frontend |
| 3.5 | WebSocket 基础设施搭建 | Engine + Server + Frontend |
| 3.6 | 暂停/恢复/速度控制实现 | Engine |
| 3.7 | 中途事件注入实现 | Engine + Server |
| 3.8 | 实时数据流展示组件 | Frontend |
| 3.9 | SSE 降级方案 | Frontend |
| 3.10 | 集成测试 | All |

---

## 五、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 多分析师辩论 LLM Token 消耗大 | 成本增加 | 提供"快速分析"（单分析师）和"深度分析"（多分析师辩论）两种模式 |
| 仿真快照数据量大 | 存储压力 | 增量快照 + JSON 压缩 + 可配置快照频率 |
| Neo4j 部署复杂性 | 用户门槛高 | 提供内嵌模式（igraph）作为 Neo4j 的轻量替代 |
| WebSocket 在部分网络环境不稳定 | 控制功能不可用 | SSE 降级方案 + 断线自动重连 |
| i18n 翻译维护成本 | 新功能需同步翻译 | 建立翻译键命名规范，新功能 PR 必须包含双语翻译 |
| 场景 DNA 混合可能产生不合理配置 | 仿真质量下降 | LLM 对混合结果做"合理性校验"，标注可能的问题 |

---

## 六、成功指标

| 指标 | 目标 |
|------|------|
| Agent 配置时间 | 从 30 分钟手动配置降低到 5 分钟智能生成 |
| 报告洞察深度 | 用户满意度评分 ≥ 4.0/5.0 |
| 场景配置效率 | 自然语言输入到配置完成 < 2 分钟 |
| 国际化覆盖 | 100% UI 文案双语支持 |
| 实时控制延迟 | 命令到响应 < 500ms |
| 分支仿真启动时间 | < 10 秒（不含运行时间） |
