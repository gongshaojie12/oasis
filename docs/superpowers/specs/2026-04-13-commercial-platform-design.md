# OASIS 商业化平台设计文档

## 概述

将 OASIS 开源社交媒体模拟器打造为一个完整的商业化 SaaS 平台，覆盖 6 大业务方向、8 个社交平台、多 LLM 模型支持，面向国内企业客户。

### 核心决策

| 维度 | 决策 |
|------|------|
| 业务范围 | 6 个商业方向全做 |
| 团队 | 1 人开发 |
| 前端 | Nuxt 3 + Naive UI |
| 部署 | 国内轻量云服务器 |
| 数据库 | SQLite（可切换 PostgreSQL） |
| 认证 | 手机号 + 短信验证码 |
| 支付 | 前期对公转账，平台内管理配额 |
| LLM | 多模型支持（DeepSeek/通义/字节/MiniMax/智谱/Kimi） |
| 平台 | Twitter + Reddit + 6 个国内平台 |
| 可视化 | Dashboard + PDF 报告 |
| 多租户 | 企业 ID 简单隔离 |
| 任务执行 | 异步 + 实时进度 |
| UI 风格 | 简洁、大方、科技感 |

---

## 一、系统架构

```
国内用户
  ↓
国内 CDN（静态资源加速）
  ↓
┌──────────────────────────────────────────────┐
│         国内轻量云服务器 (~100-300 元/月)       │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  Nuxt 3 (SSR + Nitro API)              │  │
│  │  ├── 前端页面渲染                        │  │
│  │  ├── /api/auth/*     用户认证            │  │
│  │  ├── /api/sim/*      模拟任务管理         │  │
│  │  ├── /api/report/*   报告查看/下载        │  │
│  │  ├── /api/admin/*    企业/套餐/配额       │  │
│  │  └── /api/platform/* 平台配置            │  │
│  └──────────┬────────────────────────────┘  │
│             │                                │
│  ┌──────────┴──────┐  ┌──────────────────┐  │
│  │  SQLite / PG     │  │  本地文件存储      │  │
│  │  (用户/订单/任务) │  │  (报告/PDF/数据)  │  │
│  └─────────────────┘  └──────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  FastAPI 模拟服务                        │  │
│  │  ├── 任务队列管理                        │  │
│  │  ├── OASIS 模拟引擎                     │  │
│  │  ├── 进度上报 → Nuxt API                │  │
│  │  ├── 结果写入 → 本地存储                 │  │
│  │  └── LLM API 调用                       │  │
│  │      (DeepSeek/通义/字节/MiniMax/...)    │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

### 各层职责

| 层 | 技术 | 职责 | 运行环境 |
|---|------|------|---------|
| 前端 | Nuxt 3 + Naive UI | 页面渲染、交互 | 服务器 Node.js |
| API 层 | Nitro Server Routes | 认证、业务逻辑、任务调度 | 服务器 Node.js |
| 数据层 | Drizzle ORM + SQLite/PG | 结构化数据 | 服务器本地 |
| 文件层 | 本地磁盘 | 报告、PDF、导出文件 | 服务器本地 |
| 模拟层 | FastAPI + OASIS | 模拟执行、进度上报、结果输出 | 服务器 Python |

### 通信协议

| 通信路径 | 协议 | 用途 |
|---------|------|------|
| 前端 ↔ Nitro | HTTPS REST API | 常规业务请求 |
| 前端 ↔ Nitro | SSE | 模拟实时进度推送 |
| Nitro → FastAPI | HTTP + API Key | 下发模拟任务 |
| FastAPI → Nitro | HTTP Callback | 上报进度、推送结果 |

---

## 二、数据库设计

使用 Drizzle ORM，支持 SQLite 和 PostgreSQL 自由切换（通过环境变量 `DATABASE_TYPE` 控制）。

### 表结构

```sql
-- 企业表
enterprises
├── id              TEXT PK (nanoid)
├── name            TEXT NOT NULL
├── contact_phone   TEXT
├── status          TEXT DEFAULT 'active'  -- active / suspended
├── plan_type       TEXT DEFAULT 'basic'   -- basic / professional / enterprise
├── sim_quota       INTEGER DEFAULT 0
├── quota_expires   TEXT
├── created_at      TEXT
├── updated_at      TEXT

-- 用户表
users
├── id              TEXT PK (nanoid)
├── enterprise_id   TEXT FK → enterprises.id
├── phone           TEXT UNIQUE NOT NULL
├── name            TEXT
├── role            TEXT DEFAULT 'user'    -- admin / user
├── last_login_at   TEXT
├── created_at      TEXT
├── updated_at      TEXT

-- 短信验证码表
sms_codes
├── id              TEXT PK
├── phone           TEXT NOT NULL
├── code            TEXT NOT NULL
├── expires_at      TEXT NOT NULL
├── used            INTEGER DEFAULT 0
├── created_at      TEXT

-- 模拟任务表
simulations
├── id              TEXT PK (nanoid)
├── enterprise_id   TEXT FK → enterprises.id
├── user_id         TEXT FK → users.id
├── name            TEXT NOT NULL
├── type            TEXT NOT NULL
│   -- marketing_sim / sentiment_predict / recsys_test
│   -- research / digital_twin / synthetic_data
├── platform        TEXT NOT NULL
├── config          TEXT NOT NULL          -- JSON
├── status          TEXT DEFAULT 'pending' -- pending/running/completed/failed
├── progress        INTEGER DEFAULT 0
├── agent_count     INTEGER
├── time_steps      INTEGER
├── llm_model       TEXT
├── started_at      TEXT
├── completed_at    TEXT
├── error_message   TEXT
├── created_at      TEXT
├── updated_at      TEXT

-- 模拟报告表
reports
├── id              TEXT PK
├── simulation_id   TEXT FK → simulations.id
├── enterprise_id   TEXT FK → enterprises.id
├── title           TEXT NOT NULL
├── summary         TEXT
├── dashboard_data  TEXT                   -- JSON
├── pdf_url         TEXT
├── raw_data_url    TEXT
├── created_at      TEXT

-- 订单表
orders
├── id              TEXT PK
├── enterprise_id   TEXT FK → enterprises.id
├── plan_type       TEXT NOT NULL
├── amount          INTEGER NOT NULL       -- 金额(分)
├── sim_quota       INTEGER NOT NULL
├── duration_days   INTEGER NOT NULL
├── status          TEXT DEFAULT 'pending' -- pending / paid / expired
├── paid_at         TEXT
├── notes           TEXT
├── created_at      TEXT
├── updated_at      TEXT

-- Agent 画像模板表
agent_templates
├── id              TEXT PK
├── enterprise_id   TEXT              -- NULL = 系统预置
├── platform        TEXT NOT NULL
├── name            TEXT NOT NULL
├── profile_config  TEXT NOT NULL     -- JSON
├── is_public       INTEGER DEFAULT 0
├── created_at      TEXT
├── updated_at      TEXT

-- 模拟模板表
simulation_templates
├── id              TEXT PK
├── enterprise_id   TEXT              -- NULL = 系统预置
├── name            TEXT NOT NULL
├── type            TEXT NOT NULL     -- 业务类型
├── platform        TEXT NOT NULL
├── config          TEXT NOT NULL     -- JSON: 完整模拟配置
├── is_public       INTEGER DEFAULT 0
├── created_at      TEXT
├── updated_at      TEXT

-- LLM 调用记录表
llm_usage
├── id              TEXT PK
├── simulation_id   TEXT FK → simulations.id
├── enterprise_id   TEXT FK → enterprises.id
├── provider        TEXT
├── model           TEXT
├── input_tokens    INTEGER
├── output_tokens   INTEGER
├── cost_yuan       REAL
├── agent_tier      TEXT              -- core / normal / background
├── created_at      TEXT
```

### 数据隔离

所有业务表包含 `enterprise_id`，API 中间件自动注入，确保企业间数据隔离。

### 文件存储结构

```
storage/
├── reports/{enterprise_id}/{simulation_id}/
│   ├── report.pdf
│   ├── dashboard.json
│   └── raw_data.csv
├── templates/{enterprise_id}/{template_id}.json
└── exports/{enterprise_id}/{export_id}.zip
```

---

## 三、6 大业务模块

6 个业务方向共享同一个模拟引擎，区别在于配置参数、Agent 画像和结果分析维度。

### 模块 1：社交营销模拟器

- **用途：** 品牌投放前预演不同策略的效果
- **流程：** 选平台 → 配 Agent → 设投放策略 → A/B 对照 → 模拟 → 分析
- **配置参数：** 平台、Agent 数量、策略组（KOL 配置 + 文案内容）
- **分析维度：** 传播量、互动率、情感倾向、关键意见形成、策略对比

### 模块 2：舆情预测与预警

- **用途：** 模拟危机事件爆发后的舆论传播，测试公关策略
- **流程：** 定义危机事件 → 配社群画像 → 设公关响应策略 → 模拟 → 对比
- **配置参数：** 危机事件描述、受众分布（支持/反对/围观）、响应策略组
- **分析维度：** 舆情走势曲线、负面峰值、关键传播节点、最优响应窗口

### 模块 3：推荐算法测试沙箱

- **用途：** 测试不同推荐策略对用户行为的影响
- **流程：** 选基础算法 → 调参数 → 配内容池 → 模拟 → 对比指标
- **配置参数：** 算法组（类型 + 参数）、内容池分布
- **分析维度：** 点击率、停留时间、内容多样性、信息茧房指数

### 模块 4：社会科学研究平台

- **用途：** 学术研究模拟社会现象
- **流程：** 选研究模板 → 配实验变量 → 设对照组 → 模拟 → 导出数据
- **配置参数：** 研究模板、网络拓扑、意见分布、影响者比例
- **分析维度：** 意见分布变化、聚类系数、极化指数、传播路径图

### 模块 5：数字孪生社区

- **用途：** 为产品团队创建目标社区的数字镜像
- **流程：** 配社区画像 → 设初始状态 → 注入干预 → 模拟 → 观察
- **配置参数：** 社区主题、活跃度、核心用户比例、干预事件序列
- **分析维度：** DAU 变化、内容产出量、用户情绪、社区健康度

### 模块 6：合成数据工厂

- **用途：** 批量生成高质量社交媒体训练数据
- **流程：** 选平台和数据类型 → 配规格 → 设多样性 → 生成 → 下载
- **配置参数：** 数据类型、数量、话题、风格分布、输出格式
- **分析维度：** 多样性评分、质量抽检、去重率

---

## 四、8 个社交平台适配

每个平台只需实现 3 层差异化：ActionType、RecSys、AgentPrompt。

### 已有平台

| 平台 | 状态 |
|------|------|
| Twitter | 已实现 |
| Reddit | 已实现 |

### 新增平台

| 平台 | 新增 Action | 推荐系统 | Agent 风格 | 代码量 |
|------|------------|---------|-----------|--------|
| **微博** | 无（同 Twitter） | 热度 + 热搜话题加权 | 围观吃瓜、情绪化 | ~100 行 |
| **小红书** | COLLECT_POST, SHARE_POST | 双通道（搜索 + 发现页），收藏 > 点赞 | 年轻女性、种草文化、emoji 密集 | ~200 行 |
| **抖音** | COLLECT_POST | 流量池（50→200→全量） | 碎片化消费、强互动 | ~300 行 |
| **快手** | SEND_GIFT, POST_SHUOSHUO | 社交 + 算法，关注页权重高 | 下沉市场、老铁文化 | ~200 行 |
| **B站** | SEND_DANMAKU, GIVE_COIN, TRIPLE_TAP | 兴趣标签 + 关注 + 热门 | Z 世代、梗文化 | ~300 行 |
| **微信视频号** | SHARE_TO_FRIENDS | 社交 + 算法混合，朋友点赞优先 | 中年、正能量、分享驱动 | ~400 行 |

### 平台注册机制

通过注册模式实现可插拔：

```python
# 模拟引擎端
class PlatformRegistry:
    def register(self, name, action_types, recsys_class, prompt_template): ...
    def get(self, name) -> PlatformConfig: ...
```

```typescript
// 前端配置表单
platforms = {
  xiaohongshu: {
    name: "小红书",
    actions: [...baseActions, "COLLECT_POST", "SHARE_POST"],
    recsys_options: ["search_recommend", "discover_feed"],
    config_schema: { /* 特有配置字段 */ }
  }
}
```

---

## 五、LLM 多模型适配

### 支持厂商

全部兼容 OpenAI API 协议，统一通过 `base_url` + `api_key` 切换：

| 厂商 | 模型 | base_url |
|------|------|----------|
| DeepSeek | deepseek-chat / deepseek-reasoner | api.deepseek.com |
| 通义千问 | qwen-plus / qwen-max / qwen-turbo | dashscope.aliyuncs.com/compatible-mode |
| 字节豆包 | doubao-*-pro / doubao-*-lite | ark.cn-beijing.volces.com |
| MiniMax | MiniMax-Text-01 / abab6.5s | api.minimax.chat/v1 |
| 智谱 | glm-4-plus / glm-4-flash | open.bigmodel.cn/api/paas/v4 |
| Kimi | moonshot-v1-8k / 32k / 128k | api.moonshot.cn/v1 |
| OpenAI | gpt-4o / gpt-4o-mini | api.openai.com |

### 成本分层策略

| Agent 层级 | 占比 | 模型 | 500 Agent 成本 |
|-----------|------|------|---------------|
| 核心（KOL/意见领袖） | 5-10% | 强模型（qwen-max 等） | - |
| 普通（活跃用户） | 20-30% | 中等（deepseek-chat） | - |
| 背景（沉默大多数） | 60-70% | 轻量/规则（glm-4-flash） | - |
| **分层总计** | | | **~10-30 元** |
| 全用强模型 | | | ~100-150 元 |

### 前端配置

用户可选默认推荐或自定义分层，企业版支持填入自有 API Key。

---

## 六、前端设计

### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| UI 组件库 | Naive UI | Vue 3 原生、中文文档、主题定制 |
| 图表库 | ECharts | 国内最成熟、类型全 |
| 图标 | Iconify | 统一方案，按需加载 |
| 表单校验 | VeeValidate + Zod | 类型安全 |
| 状态管理 | Pinia | Nuxt 3 官方推荐 |
| PDF 生成 | WeasyPrint（服务端） | Dashboard 渲染为 PDF |

### UI 风格

简洁、大方、科技感。深色主题 + 科技蓝/紫色调，大留白、卡片式布局。

### 页面清单

**公开页面：**
- `/login` — 手机号 + 短信验证码登录
- `/register` — 企业注册

**工作台：**
- `/dashboard` — 概览：最近任务、配额使用、快速入口

**模拟任务：**
- `/simulations` — 任务列表
- `/simulations/create` — 新建模拟（分步表单：业务类型→平台→参数→模型→确认）
- `/simulations/:id` — 任务详情 + 实时进度

**报告中心：**
- `/reports` — 报告列表
- `/reports/:id` — Dashboard 图表 + AI 结论 + PDF 下载

**模板管理：**
- `/templates/agents` — Agent 画像模板
- `/templates/simulations` — 模拟配置模板

**企业设置：**
- `/settings/enterprise` — 企业信息
- `/settings/plan` — 套餐与配额
- `/settings/keys` — LLM API Key 管理
- `/settings/logs` — 操作日志

### 布局结构

```
┌──────────────────────────────────────────────┐
│  顶部导航栏  Logo | 企业名 |        用户/退出  │
├──────────┬───────────────────────────────────┤
│ 侧边栏    │         主内容区                   │
│ 工作台    │                                   │
│ 模拟任务  │                                   │
│ 报告中心  │                                   │
│ 模板管理  │                                   │
│ 企业设置  │                                   │
├──────────┴───────────────────────────────────┤
│  底部状态栏（套餐类型 | 剩余次数 | 到期时间）      │
└──────────────────────────────────────────────┘
```

---

## 七、API 接口设计

### 接口清单

**认证：**
- `POST /api/auth/sms/send` — 发送验证码
- `POST /api/auth/login` — 登录
- `POST /api/auth/register` — 注册
- `GET /api/auth/me` — 当前用户信息
- `POST /api/auth/logout` — 退出

**模拟任务：**
- `GET /api/simulations` — 列表（分页、筛选）
- `POST /api/simulations` — 创建任务
- `GET /api/simulations/:id` — 详情
- `GET /api/simulations/:id/progress` — 实时进度（SSE）
- `POST /api/simulations/:id/cancel` — 取消
- `POST /api/simulations/:id/retry` — 重试

**报告：**
- `GET /api/reports` — 列表
- `GET /api/reports/:id` — 详情（Dashboard 数据）
- `GET /api/reports/:id/pdf` — 下载 PDF
- `GET /api/reports/:id/export` — 导出原始数据

**模板：**
- `GET/POST/PUT/DELETE /api/templates/agents/*`
- `GET/POST/PUT/DELETE /api/templates/simulations/*`

**企业：**
- `GET /api/enterprises/current` — 当前企业
- `PUT /api/enterprises/current` — 更新信息
- `GET /api/enterprises/usage` — 用量统计
- `GET /api/enterprises/logs` — 操作日志

**平台与 LLM：**
- `GET /api/platforms` — 支持的平台列表
- `GET /api/llm/providers` — 支持的模型列表
- `POST /api/llm/keys` — 保存 API Key
- `DELETE /api/llm/keys/:provider` — 删除 Key
- `POST /api/llm/keys/test` — 测试连通性

**内部接口（模拟引擎回调）：**
- `POST /api/internal/progress` — 上报进度
- `POST /api/internal/complete` — 模拟完成
- `POST /api/internal/error` — 模拟失败

### 统一响应格式

```json
{ "code": 0, "data": { ... }, "message": "ok" }
{ "code": 40001, "data": null, "message": "验证码已过期" }
```

错误码规则：400xx 认证、401xx 权限、402xx 配额、500xx 服务端。

---

## 八、异步任务与进度推送

### 任务生命周期

```
用户提交 → Nitro 校验配额/扣减 → 写入 DB (pending)
  → HTTP POST 到 FastAPI → 加入 asyncio 队列
  → 执行模拟（逐轮上报进度 → Nitro callback → 更新 DB）
  → 完成 → 回调 Nitro → 更新 DB + 短信通知
前端通过 SSE 连接实时获取进度，支持断线重连。
```

### 任务队列

Python 端使用 asyncio.Queue 实现轻量队列，不引入 Redis/Celery。

### 并发控制

| 套餐 | 最大并发 |
|------|---------|
| 基础版 | 1 |
| 专业版 | 3 |
| 企业版 | 5 |

---

## 九、项目目录结构

```
oasis/
├── oasis/                    # 现有 OASIS 核心引擎（不动）
│
├── web/                      # 商业化平台（Nuxt 3）
│   ├── nuxt.config.ts
│   ├── package.json
│   ├── drizzle.config.ts
│   ├── server/
│   │   ├── api/              # Nitro API 路由
│   │   │   ├── auth/
│   │   │   ├── simulations/
│   │   │   ├── reports/
│   │   │   ├── templates/
│   │   │   ├── enterprises/
│   │   │   ├── platforms/
│   │   │   ├── llm/
│   │   │   └── internal/
│   │   ├── middleware/       # 认证、企业隔离、内部鉴权
│   │   ├── database/         # Drizzle schema、迁移、连接
│   │   └── utils/            # 短信、JWT、PDF、响应格式
│   ├── pages/                # 前端页面
│   ├── components/           # 可复用组件
│   ├── composables/          # 组合式函数
│   ├── layouts/              # 布局模板
│   ├── stores/               # Pinia 状态
│   └── assets/               # 样式、静态资源
│
├── engine/                   # 模拟服务（FastAPI）
│   ├── main.py
│   ├── config.py
│   ├── queue.py
│   ├── runner.py
│   ├── reporter.py
│   ├── callback.py
│   ├── platforms/            # 6 个国内平台适配
│   ├── llm/                  # 多模型管理
│   └── requirements.txt
│
├── business/                 # 商业文档（不动）
├── data/                     # 现有
├── docs/                     # 现有
├── examples/                 # 现有
├── test/                     # 现有
└── visualization/            # 现有
```

设计原则：不侵入现有 `oasis/` 代码，`engine/` 通过 import 调用 OASIS 核心。

---

## 十、安全与运维

### 安全

| 类别 | 措施 |
|------|------|
| 短信防刷 | 60 秒间隔，同 IP 每小时 10 次 |
| 验证码 | 5 分钟过期，用后失效 |
| Token | JWT access_token 2h，refresh_token 7d |
| 数据隔离 | 中间件自动注入 enterprise_id |
| 内部接口 | X-Internal-Key + IP 白名单 |
| 限流 | 普通 100 次/分，模拟提交 10 次/分 |
| 输入校验 | Zod schema |
| API Key 存储 | AES-256 加密 |

### 环境变量

```bash
# web/.env
DATABASE_TYPE=sqlite|postgresql
DATABASE_URL=...
JWT_SECRET=xxx
SMS_ACCESS_KEY=xxx
SMS_ACCESS_SECRET=xxx
INTERNAL_API_KEY=xxx
ENGINE_URL=http://localhost:8000
ENCRYPTION_KEY=xxx

# engine/.env
NUXT_CALLBACK_URL=http://localhost:3000
INTERNAL_API_KEY=xxx
MAX_CONCURRENT_TASKS=2
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat
```

### 运维

- **进程管理：** PM2 管理 Nuxt + FastAPI 两个进程
- **日志：** 按天滚动，模拟过程独立日志文件
- **备份：** SQLite 每日复制 / PostgreSQL 每日 pg_dump，保留 7 天
- **健康检查：** `/api/health` + `/engine/health`

### 成本

| 项目 | 月费 |
|------|------|
| 轻量云服务器（2C4G） | 100-300 元 |
| 短信 | ~10-50 元 |
| 域名 | ~5 元 |
| SSL | 0（Let's Encrypt） |
| LLM API | 按量（可转嫁客户） |
| **总计** | **~120-360 元/月** |
