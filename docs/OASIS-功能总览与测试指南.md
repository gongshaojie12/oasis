# OASIS 社交仿真平台 — 功能总览与本地测试指南

## 一、平台概述

OASIS (Open Agents Social Interaction Simulations) 是一个企业级社交媒体仿真平台，基于 CAMEL-AI 的 OASIS 多智能体仿真引擎构建。平台支持在 8 大社交平台（Twitter、Reddit、微博、小红书、抖音、快手、B站、视频号）上进行大规模 Agent 仿真。

### 系统架构

```
用户浏览器
  │
  ├── HTTP ──→ Web 容器 (Nuxt 4 + Naive UI, 端口 3000)
  │              ├── SSR 前端渲染
  │              ├── API 路由层 (Zod 校验 + Drizzle ORM)
  │              └── SQLite 数据库
  │
  └── WS ───→ Web 容器 ──→ Engine 容器 (FastAPI, 端口 8000)
                              ├── OASIS 仿真核心 (多 Agent 模拟)
                              ├── 7 大 LLM 提供商 (DeepSeek/Qwen/豆包/...)
                              ├── 基因组繁殖算法
                              ├── 多分析师辩论引擎
                              ├── 场景作曲家 (NL→Config)
                              └── WebSocket 实时控制
```

### 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Nuxt 4 + Vue 3 + Naive UI + ECharts + Pinia |
| 服务端 | Nitro (h3) + Drizzle ORM + SQLite/PostgreSQL |
| 引擎 | Python 3.10 + FastAPI + OASIS Core + CAMEL-AI |
| 部署 | Docker Compose，双容器架构 |
| 国际化 | @nuxtjs/i18n，中文/英文双语 |

---

## 二、功能清单

### 基础功能（项目原有）

| 功能 | 说明 | 入口 |
|------|------|------|
| 企业与用户管理 | 多租户、手机号/管理员登录、配额管理 | `/login`, `/register`, `/admin/login` |
| 仿真管理 | 创建/查看/取消/重试仿真任务 | `/simulations` |
| 仿真创建向导 | 3 步向导：业务类型→平台参数→确认 | `/simulations/create` |
| 实时进度 | SSE 推送仿真执行进度 | `/simulations/:id` |
| 报告系统 | 仿真结果报告、导出 | `/reports` |
| 模板管理 | Agent 模板和仿真模板的 CRUD | `/templates` |
| LLM 密钥管理 | 7 大 LLM 提供商的 API Key 管理与测试 | `/settings` |
| 操作日志 | 全平台操作审计日志 | `/settings` |

### P0 阶段 — 核心创新功能

#### P0-1 人格基因组 (Persona Genome)

**功能**: 从自然语言描述中提取结构化的 Agent 人格参数（大五人格、MBTI、兴趣标签等），支持基因组繁殖（交叉/变异/混合策略）批量生成多样化 Agent 群体。

| 模块 | 文件 | 说明 |
|------|------|------|
| 基因组 Schema | `engine/genome/schema.py` | GenomeData 数据模型，含 20+ 人格维度 |
| 基因组提取器 | `engine/genome/extractor.py` | LLM 驱动的文本→基因组映射 |
| 基因组繁殖器 | `engine/genome/breeder.py` | 交叉/变异/混合三种繁殖策略 |
| API 端点 | `engine/main.py` | `/engine/genomes/extract`, `/breed` |
| 前端页面 | `web/app/pages/genomes/` | 列表/创建/编辑/繁殖 4 个页面 |
| Pinia Store | `web/app/stores/genomes.ts` | 基因组状态管理 |
| 雷达图组件 | `web/app/components/GenomeRadar.vue` | 人格维度可视化 |
| 群体预览 | `web/app/components/PopulationPreview.vue` | 繁殖结果预览 |

**用户操作流程**:
1. 进入 `/genomes/create`，输入自然语言描述（如"一个喜欢科技、性格外向的 25 岁程序员"）
2. AI 提取出结构化基因组 → 展示雷达图
3. 进入 `/genomes/breed`，选择种子基因组 → 配置繁殖参数 → 批量生成 Agent 群体

#### P0-2 多分析师辩论报告 (Multi-Analyst Debate)

**功能**: 仿真完成后，4 位 AI 分析师（数据分析师、社会学家、心理学家、魔鬼代言人）从不同视角解读仿真数据，通过多轮辩论产出更深入的分析报告。

| 模块 | 文件 | 说明 |
|------|------|------|
| 分析师基类 | `engine/analysts/base.py` | AnalysisContext 数据模型 |
| 4 位分析师 | `engine/analysts/data_analyst.py` 等 | 各自的分析 Prompt 和关注点 |
| 辩论引擎 | `engine/analysts/debate.py` | 多轮辩论编排 + 仲裁总结 |
| API 端点 | `engine/main.py` | `/engine/analysis/run`, `/analysis/:id` |
| 前端页面 | `web/app/pages/analysis/` | 分析列表 + 详情页 |
| 辩论日志组件 | `web/app/components/DebateLog.vue` | 分轮展示辩论过程 |
| 时间线叙事 | `web/app/components/TimelineNarrative.vue` | 事件时间线 |
| 分析仪表盘 | `web/app/components/AnalysisDashboard.vue` | ECharts 图表 |

### P1 阶段 — 深度交互

#### P1-1 世界构建器 (World Builder)

**功能**: 可视化构建知识图谱（实体关系网络），定义 Agent 之间的社会关系（KOL、普通用户、机器人等），分析图谱影响力和社区结构，一键映射为仿真配置。

| 模块 | 文件 | 说明 |
|------|------|------|
| 图数据模型 | `engine/graph/schema.py` | GraphData, GraphNode, GraphEdge |
| 图分析器 | `engine/graph/analyzer.py` | 影响力检测、社区发现、瓶颈节点 |
| 图→仿真映射 | `engine/graph/mapper.py` | 知识图谱自动转换为 Agent 配置 |
| API 端点 | `engine/main.py` | `/engine/graph/analyze`, `/to-simulation` |
| 前端编辑器 | `web/app/pages/world-builder/[id].vue` | ECharts graph 图编辑 |
| 工具栏/节点面板 | `web/app/components/GraphToolbar.vue` 等 | 节点/边的增删改 |
| 数据库 | `knowledge_graphs` 表 | SQLite JSON 列存储图数据 |

#### P1-2 时间机器 (Time Machine)

**功能**: 仿真完成后，回溯任意轮次的快照，查看每轮 Agent 行为和帖子，与历史 Agent 对话（角色扮演），发起多 Agent 圆桌讨论，支持回放播放。

| 模块 | 文件 | 说明 |
|------|------|------|
| 快照提取器 | `engine/timemachine/snapshot.py` | 从仿真 SQLite 提取按轮次的快照 |
| Agent 对话引擎 | `engine/timemachine/chat.py` | 基于上下文的角色扮演对话 |
| API 端点 | `engine/main.py` | `/engine/timemachine/snapshots`, `/chat`, `/roundtable` |
| 时间轴组件 | `web/app/components/TimelineSlider.vue` | 轮次滑块 |
| 快照查看器 | `web/app/components/SnapshotViewer.vue` | 指标+帖子+Agent 列表 |
| 对话面板 | `web/app/components/AgentChatPanel.vue` | 消息气泡式对话 |
| 回放播放器 | `web/app/components/ReplayPlayer.vue` | 0.5x-4x 变速播放 |
| 数据库 | `simulation_snapshots`, `agent_conversations` 表 | 快照缓存 + 对话持久化 |

### P2 阶段 — 智能化

#### P2-1 国际化 (i18n)

**功能**: 全平台中文/英文双语支持，浏览器自动检测语言，一键切换，Cookie 持久化。

| 模块 | 文件 | 说明 |
|------|------|------|
| 配置 | `web/nuxt.config.ts` | @nuxtjs/i18n, strategy: 'no_prefix' |
| 中文语言包 | `web/locales/zh-CN.json` | 560+ 翻译键 |
| 英文语言包 | `web/locales/en-US.json` | 完整英文翻译 |
| 语言切换 | `web/app/components/layout/Header.vue` | 右上角 CN/EN 切换按钮 |

**覆盖范围**: 全部 21 个页面、26 个组件、导航栏、侧边栏、所有表单标签和提示信息。

#### P2-2 场景作曲家 (Scenario Composer)

**功能**: 用自然语言描述仿真场景（如"模拟 500 人的微博舆论战"），AI 自动解析为完整仿真配置。支持场景 DNA（冲突强度、传播潜力等 6 维度）混合，参数可视化调优，资源消耗预估。

| 模块 | 文件 | 说明 |
|------|------|------|
| 场景 Schema | `engine/composer/schema.py` | ScenarioConfig, ScenarioDNA, ResourceEstimate |
| NL→Config 解析器 | `engine/composer/parser.py` | LLM 驱动的自然语言解析 |
| DNA 混合器 | `engine/composer/mixer.py` | 加权混合两个场景 DNA |
| 资源估算器 | `engine/composer/estimator.py` | LLM 调用/Token/耗时/费用估算 |
| API 端点 | `engine/main.py` | `/engine/composer/parse`, `/mix`, `/recommend`, `/estimate` |
| 前端 AI 模式 | `web/app/pages/simulations/create.vue` | 新增"AI 编排"Tab |
| DNA 雷达图 | `web/app/components/composer/DNARadarChart.vue` | 6 维度雷达可视化 |
| 参数面板 | `web/app/components/composer/ParameterPanel.vue` | 滑块/饼图/事件编辑 |
| DNA 混合器 | `web/app/components/composer/DNAMixer.vue` | 双场景混合界面 |

**用户操作流程**:
1. 进入 `/simulations/create` → 切换到"AI 编排"Tab
2. 输入自然语言描述 → 点击"AI 解析"
3. 查看生成的配置：DNA 雷达图 + 参数面板 + 资源估算
4. 可选：使用 DNA 混合器混合两个模板场景
5. 点击"使用此配置"→ 自动填入表单 → 确认提交

### P3 阶段 — 运营级体验

#### P3-1 任务控制中心 (Mission Control)

**功能**: 将 Dashboard 升级为自适应任务控制中心，根据仿真生命周期阶段（准备→发射→监控→分析）自动切换视图，显示仿真健康度指标，提供上下文相关的快捷操作。

| 模块 | 文件 | 说明 |
|------|------|------|
| 健康度端点 | `engine/main.py` | `/engine/simulations/health` |
| 健康度代理 | `web/server/api/simulations/[id]/health.get.ts` | Nuxt 代理层 |
| 健康仪表盘 | `web/app/components/mission/HealthIndicator.vue` | ECharts 仪表盘 + 5 项指标 |
| 快捷操作 | `web/app/components/mission/QuickActions.vue` | 阶段感知的操作入口 |
| Dashboard 页面 | `web/app/pages/dashboard.vue` | 生命周期步进器 + 健康监控 |

**健康度指标**: Agent 活跃度、响应质量、行为多样性、系统负载、错误率 → 加权综合评分。

#### P3-2 直播控制台 (Live Control Panel)

**功能**: WebSocket 双向通信，支持仿真运行中的实时控制（暂停/恢复/变速/单步执行），中途事件注入（突发新闻、KOL 入场等），实时帖子流展示。

| 模块 | 文件 | 说明 |
|------|------|------|
| WS 协议 | `engine/websocket/protocol.py` | 消息类型定义（command/data/status） |
| 命令队列 | `engine/websocket/commands.py` | pause/resume/speed/inject/step |
| 连接管理 | `engine/websocket/handler.py` | SimulationWSManager，多连接广播 |
| WS 端点 | `engine/main.py` | `/engine/ws/{task_id}` |
| 前端 Composable | `web/app/composables/useWebSocket.ts` | WS 连接 + 自动重连 + 命令方法 |
| 控制面板 | `web/app/components/live/LiveControlPanel.vue` | 暂停/恢复/变速/单步 |
| 帖子流 | `web/app/components/live/PostStream.vue` | 实时滚动帖子 |
| 事件注入 | `web/app/components/live/EventInjector.vue` | 注入自定义事件 |

---

## 三、数据库表结构（19 张表）

| 表名 | 说明 |
|------|------|
| `enterprises` | 企业/租户 |
| `users` | 用户账号 |
| `sms_codes` | 短信验证码 |
| `operation_logs` | 操作审计日志 |
| `simulations` | 仿真任务 |
| `simulation_templates` | 仿真模板 |
| `simulation_snapshots` | 时间机器快照缓存 |
| `agent_conversations` | Agent 对话记录 |
| `persona_genomes` | 人格基因组 |
| `genome_batches` | 基因组繁殖批次 |
| `agent_templates` | Agent 模板 |
| `reports` | 仿真报告 |
| `analysis_reports` | 多分析师辩论报告 |
| `report_comparisons` | 报告对比 |
| `knowledge_graphs` | 知识图谱 |
| `llm_keys` | LLM API 密钥（加密存储） |
| `llm_usage` | Token 用量追踪 |
| `orders` | 配额订单 |

---

## 四、API 端点汇总

### Engine 端点（FastAPI, 端口 8000）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/engine/health` | 健康检查 |
| POST | `/engine/tasks` | 提交仿真任务 |
| GET | `/engine/tasks/:id` | 查询任务状态 |
| POST | `/engine/tasks/:id/cancel` | 取消任务 |
| POST | `/engine/genomes/extract` | 提取基因组 |
| POST | `/engine/genomes/breed` | 繁殖基因组 |
| POST | `/engine/analysis/run` | 启动多分析师辩论 |
| GET | `/engine/analysis/:id` | 查询分析状态 |
| POST | `/engine/graph/analyze` | 分析知识图谱 |
| POST | `/engine/graph/to-simulation` | 图谱→仿真映射 |
| POST | `/engine/timemachine/snapshots` | 提取快照 |
| POST | `/engine/timemachine/chat` | Agent 对话 |
| POST | `/engine/timemachine/roundtable` | 多 Agent 圆桌 |
| POST | `/engine/composer/parse` | 自然语言→配置 |
| POST | `/engine/composer/mix` | 场景 DNA 混合 |
| GET | `/engine/composer/recommend` | 推荐场景模板 |
| POST | `/engine/composer/estimate` | 资源消耗估算 |
| POST | `/engine/simulations/health` | 仿真健康度 |
| WS | `/engine/ws/:task_id` | WebSocket 实时控制 |

### Web API 端点（Nuxt/Nitro, 端口 3000）

共 70+ 端点，主要分组：

- `/api/auth/*` — 认证（登录/注册/短信）
- `/api/simulations/*` — 仿真 CRUD + 进度 + 健康度
- `/api/genomes/*` — 基因组管理 + 提取 + 繁殖
- `/api/analysis/*` — 分析报告
- `/api/reports/*` — 仿真报告 + 导出
- `/api/templates/*` — 模板管理
- `/api/world-builder/*` — 知识图谱 CRUD + 分析
- `/api/timemachine/*` — 时间机器（快照/对话/圆桌/回放）
- `/api/composer/*` — 场景作曲家（解析/混合/推荐/估算）
- `/api/enterprises/*` — 企业管理 + 用量
- `/api/llm/*` — LLM 密钥管理

---

## 五、前端页面与组件统计

| 类别 | 数量 | 说明 |
|------|------|------|
| 页面 | 21 | 含登录/注册/Dashboard/仿真/基因组/分析/世界构建/时间机器/报告/模板/设置 |
| 组件 | 26 | 布局 2 + 通用 3 + 业务 21 |
| Pinia Store | 8 | auth/simulations/genomes/reports/analysis/world-builder/timemachine/composer |
| Composable | 4 | useApi/useSSE/useMessage/useWebSocket |
| i18n 翻译键 | 560+ | 每种语言，覆盖全平台 |

---

## 六、本地 Docker 测试步骤

### 6.1 前置条件

- **Docker Desktop** 已安装并运行（Windows/Mac）
  - Windows: https://www.docker.com/products/docker-desktop/
  - 确保 WSL 2 已启用
- **Git** 已安装
- **至少一个 LLM API Key**（用于运行仿真，如 DeepSeek）

验证 Docker：

```bash
docker --version          # Docker version 2x.x.x
docker compose version    # Docker Compose version v2.x.x
```

### 6.2 获取代码

```bash
cd D:\NLP\oasis   # 或你的项目路径
git checkout dev-0.0.1
```

### 6.3 配置环境变量

```bash
# 如果 .env.production 不存在，从模板创建
cp .env.production.example .env.production
```

编辑 `.env.production`，填入以下内容：

```env
# === 基础配置 ===
HOST_PORT=80
DATABASE_TYPE=sqlite
DATABASE_URL=file:./data/oasis.db

# === 安全密钥（本地测试可用以下固定值）===
JWT_SECRET=test-jwt-secret-at-least-32chars
ENCRYPTION_KEY=aabbccdd11223344aabbccdd11223344aabbccdd11223344aabbccdd11223344
INTERNAL_API_KEY=test-internal-key-12345

# === 管理员账号 ===
ADMIN_USERNAME=admin
ADMIN_PASSWORD=oasis-admin-2026

# === 测试手机号（免真实短信）===
TEST_PHONE=13800000000
TEST_SMS_CODE=888888

# === 短信服务（本地测试可留空）===
SMS_ACCESS_KEY=
SMS_ACCESS_SECRET=

# === 引擎配置 ===
MAX_CONCURRENT_TASKS=2
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat

# === LLM API Keys（至少填一个）===
DEEPSEEK_API_KEY=sk-你的deepseek密钥
QWEN_API_KEY=
DOUBAO_API_KEY=
MINIMAX_API_KEY=
ZHIPU_API_KEY=
KIMI_API_KEY=
OPENAI_API_KEY=
```

### 6.4 创建数据目录

```bash
mkdir -p data/sqlite data/reports
```

### 6.5 构建并启动

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

> 首次构建约 10-20 分钟（下载基础镜像 + 安装 Python/Node 依赖）。

### 6.6 查看日志

```bash
# 实时查看全部日志
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f

# 单独查看
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f web
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f engine
```

### 6.7 验证服务

```bash
# 查看容器状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps

# 预期输出：
# NAME           STATUS          PORTS
# oasis-web      Up (healthy)    0.0.0.0:80->3000/tcp
# oasis-engine   Up (healthy)
```

### 6.8 访问平台

打开浏览器：

| 地址 | 说明 |
|------|------|
| http://localhost | 首页 |
| http://localhost/admin/login | 管理员登录 → 用户名 `admin`，密码 `oasis-admin-2026` |
| http://localhost/register | 注册新账号 → 手机号 `13800000000`，验证码 `888888` |
| http://localhost/api/health | API 健康检查 |

### 6.9 功能测试路径

#### 测试 1：基本仿真流程

1. 管理员登录 → 进入 Dashboard
2. 点击"新建仿真" → 选择业务类型 → 配置参数（10 Agent, 3 轮）→ 提交
3. 观察实时进度条（SSE 推送）
4. 仿真完成后 → 点击"生成分析"→ 查看多分析师辩论报告
5. 点击"时间机器"→ 拖动时间轴查看各轮快照 → 点击 Agent 对话

#### 测试 2：AI 场景编排

1. 进入 `/simulations/create` → 切换到"AI 编排"Tab
2. 输入描述："模拟一场关于新能源汽车补贴取消的微博舆论战，200 个用户，持续 2 天"
3. 点击"AI 解析" → 查看生成的 DNA 雷达图和参数
4. 调整参数 → 点击"使用此配置" → 确认提交

#### 测试 3：人格基因组

1. 进入 `/genomes/create` → 输入人格描述 → AI 提取
2. 进入 `/genomes/breed` → 选择种子 → 配置繁殖参数 → 批量生成
3. 查看群体多样性指标

#### 测试 4：世界构建器

1. 进入 `/world-builder` → 创建新图谱
2. 添加节点（KOL、普通用户、机器人）→ 添加关系边
3. 点击"分析" → 查看影响力排名和社区结构
4. 点击"映射到仿真" → 自动生成 Agent 配置

#### 测试 5：国际化

1. 点击右上角 Header 的语言切换按钮
2. 切换 CN ↔ EN，验证全平台文案切换
3. 刷新页面，验证语言设置持久化

### 6.10 停止服务

```bash
# 停止容器
docker compose -f docker-compose.prod.yml --env-file .env.production down

# 彻底清理（包括镜像）
docker compose -f docker-compose.prod.yml --env-file .env.production down --rmi local
```

### 6.11 常见问题

| 问题 | 解决方案 |
|------|---------|
| 端口 80 被占用 | `.env.production` 中改 `HOST_PORT=3080`，访问 http://localhost:3080 |
| Engine OOM | 改 `MAX_CONCURRENT_TASKS=1`，减少 Agent 数量 |
| 构建卡在 `pip install` | Docker Desktop 设置里增大内存限制到 4GB+ |
| `better-sqlite3` 编译失败 | Dockerfile 已包含编译工具，检查 WSL 2 是否正常 |
| 仿真提交报错"引擎调度失败" | 检查 `DEEPSEEK_API_KEY` 是否填写正确 |
| 页面空白/500 | `docker logs oasis-web` 查看具体错误 |

---

## 七、最低配置要求

| 资源 | 最低 | 推荐 |
|------|------|------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 15 GB | 30 GB |
| 网络 | 必须（LLM API 调用） | — |
| GPU | 不需要 | — |

> Engine 容器加载 OASIS 核心库（含 camel-ai, igraph, sentence-transformers 等）需要较多内存。仿真运行时内存占用与 Agent 数量正相关。

---

## 八、项目文件结构

```
oasis/
├── engine/                     # Python 仿真引擎
│   ├── main.py                 # FastAPI 入口 (19 端点 + 1 WS)
│   ├── config.py               # 配置管理
│   ├── runner.py               # OASIS 仿真执行器
│   ├── queue.py                # 任务队列
│   ├── reporter.py             # 进度上报
│   ├── callback.py             # Web 回调
│   ├── llm/                    # LLM 提供商抽象层
│   ├── genome/                 # P0-1 人格基因组
│   ├── analysts/               # P0-2 多分析师辩论
│   ├── graph/                  # P1-1 知识图谱
│   ├── timemachine/            # P1-2 时间机器
│   ├── composer/               # P2-2 场景作曲家
│   ├── websocket/              # P3-2 WebSocket 控制
│   ├── platforms/              # 中国社交平台扩展
│   └── tests/                  # 单元测试
│
├── web/                        # Nuxt 4 前端 + 服务端
│   ├── app/
│   │   ├── pages/              # 21 个页面
│   │   ├── components/         # 26 个组件
│   │   ├── stores/             # 8 个 Pinia Store
│   │   └── composables/        # 4 个 Composable
│   ├── server/
│   │   ├── api/                # 70+ API 路由
│   │   ├── database/           # Drizzle ORM Schema
│   │   └── utils/              # 工具函数
│   └── locales/                # i18n 语言包 (zh-CN, en-US)
│
├── oasis/                      # OASIS 核心仿真引擎（上游库）
├── docker/                     # Dockerfile
├── docs/                       # 文档
├── docker-compose.prod.yml     # 生产编排
└── .env.production             # 环境变量
```
