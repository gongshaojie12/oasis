# 万象 WANXIANG · 部署指南（单机版）

适用于 MVP / 内部演示 / 小规模生产（< 10 RPS）。多机/k8s 是后续工作。

## 方式 A：本机直跑（最快）

需要 Python 3.10/3.11、已装好 wanxiang 依赖的环境（本机开发推荐 conda env）。

```bash
# 启动开发服务
python -m wanxiang.api.server
# 或自定义端口
WANXIANG_PORT=9090 python -m wanxiang.api.server

# 自检配置（不启动 uvicorn）
python -m wanxiang.api.server --print-config
```

## 方式 B：Docker（推荐生产/演示环境）

```bash
# 1. 准备环境变量
cp .env.example .env
# 编辑 .env 填入 WANXIANG_DEEPSEEK_API_KEY 等

# 2. 构建并启动
docker compose up -d --build

# 3. 验证
curl http://localhost:8000/healthz
# {"status":"ok","version":"0.0.1"}

# 4. 调用模拟（stub provider 不需 key）
curl -X POST http://localhost:8000/v1/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "distribution_path": "/app/wanxiang/datasources/distributions/cn_z_generation_v1.yaml",
    "n": 50, "seed": 42,
    "scenario": {"material":"新品 ¥6","question":"0-10 评分","kind":"rate"},
    "rounds": 0,
    "model": {"provider":"stub"}
  }' | head -c 500
```

### 完整 SaaS 栈部署 (Stage 1+2)

万象的 `docker-compose.yml` 提供两种部署模式：

#### 模式 1：完整栈 (生产推荐)

包含 API + PostgreSQL + Redis + Celery worker 共 4 个服务：

```bash
cp .env.example .env
vim .env   # 填入 DeepSeek API Key 等
docker compose up -d
```

`.env` 里默认 `COMPOSE_PROFILES=full`，所以 `docker compose up` 直接拉起：

- `wanxiang-api` (FastAPI HTTP 服务) :8000
- `wanxiang-postgres` (PostgreSQL 16) :内部 5432
- `wanxiang-redis` (Redis 7) :内部 6379
- `wanxiang-celery` (Celery worker, 默认并发 4)

数据持久化：

- `wanxiang_pgdata` Docker volume — PG 数据库
- `wanxiang_redisdata` Docker volume — Redis AOF 持久化

#### 模式 2：MVP 单机 (开发/小客户)

仅 API + SQLite + 进程内 asyncio：

```bash
docker compose --profile minimal up -d
```

启动 `wanxiang-api-minimal` 一个服务，所有数据写在 `wanxiang_sqlite` volume 的 `wanxiang.db` 单文件。

#### 模式切换的环境变量

| 变量 | 完整栈 | MVP 单机 |
|---|---|---|
| `WANXIANG_TASKS_DB` | `postgresql://wanxiang:wanxiang@postgres:5432/wanxiang` | `/app/data/wanxiang.db` |
| `WANXIANG_EVENT_BUS` | `redis` | `memory` |
| `WANXIANG_TASK_QUEUE` | `celery` | `asyncio` |
| `WANXIANG_REDIS_URL` | `redis://redis:6379/2` | (未用) |
| `WANXIANG_CELERY_BROKER` | `redis://redis:6379/0` | (未用) |

切换是**零代码改动**——所有切换由环境变量驱动，代码侧分别有 `InMemoryEventBus`/`RedisEventBus` + `asyncio.create_task`/`celery .delay()` 两套实现。

#### 健康检查

```bash
curl http://localhost:8000/healthz   # API
docker compose ps                    # 所有服务状态
docker logs wanxiang-celery --tail 50  # worker 日志
```

#### 备份

```bash
# PG 备份
docker exec wanxiang-postgres pg_dump -U wanxiang wanxiang > backup.sql
# Redis (AOF 已经持久化, volume 拷贝即可)
docker run --rm -v wanxiang_redisdata:/data -v $(pwd):/backup alpine \
  tar czf /backup/redis-backup.tar.gz -C /data .
```

#### 扩容到多 worker

```bash
# 扩容 Celery worker 实例数 (无需改 yaml)
docker compose up -d --scale celery-worker=4
```

#### 阶段升级路径

| 客户量 | 配置 | 升级动作 |
|---|---|---|
| MVP 试用 | minimal profile, 2C4G | — |
| ≤10 付费客户 | 完整栈, 4C8G 单机 | `docker compose up -d` |
| ≤100 付费客户 | 完整栈, 8C16G 单机 + PG 调优 | 增加 `CELERY_CONCURRENCY` |
| 100+ 付费客户 | 多机 Docker Swarm / K8s | PG 主从 + Redis Sentinel + 多 worker pod |

## 配置项

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `WANXIANG_HOST` | `0.0.0.0` | 监听地址 |
| `WANXIANG_PORT` | `8000` | 监听端口 |
| `WANXIANG_LOG_LEVEL` | `info` | `critical/error/warning/info/debug/trace` |
| `WANXIANG_WORKERS` | `1` | uvicorn worker 进程数（>1 启用多 worker） |
| `WANXIANG_DEEPSEEK_API_KEY` | _(空)_ | DeepSeek key；不填则客户端必须每次请求都传 `model.api_key` |
| `WANXIANG_TENANTS_JSON` | _(空)_ | 多租户表 JSON 数组；不填则只内置一个 demo 租户（见下） |

### 多租户与鉴权（M3-3）

`/v1/*` 路径需要 `X-API-Key` 头。默认内置一个 demo 租户：

| api_key | tenant_id | RPM 上限 |
|---|---|---|
| `demo-key` | `demo` | 60 |

生产环境通过 `WANXIANG_TENANTS_JSON` 注入真实租户表（JSON 数组）：

```bash
WANXIANG_TENANTS_JSON='[
  {"tenant_id":"acme","api_key":"sk-acme-2026","rpm_limit":120},
  {"tenant_id":"beta","api_key":"sk-beta-xxxx","rpm_limit":60}
]'
```

调用示例：

```bash
curl -X POST http://localhost:8000/v1/simulate \
  -H "X-API-Key: demo-key" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

超过 RPM 返回 `429` + `Retry-After` 头。响应头 `x-tenant-id` 为权威租户 ID
（来自 API key），客户端自带的 `X-Tenant-Id` 在 `/v1/*` 路径会被忽略。

`/healthz` 与 `/`（chat.html）不需要鉴权。

### 异步任务（M3-2）

大规模模拟（n > 500）建议走异步路径，避免 HTTP 超时：

```bash
# 1. 创建任务，立即返 202 + task_id
curl -X POST http://localhost:8000/v1/simulations/async \
  -H "X-API-Key: demo-key" -H "Content-Type: application/json" \
  -d '{...}'
# => {"task_id": "...", "status": "pending", ...}

# 2. 轮询状态（pending/running/done/failed）
curl http://localhost:8000/v1/simulations/<task_id> \
  -H "X-API-Key: demo-key"
# => {"status":"done", "result":{...}, ...}
```

任务存储为进程内（重启丢失）；生产规模化需替换为 Redis-backed store。

### SSE 流式进度 (M3-11)

`GET /v1/simulations/{task_id}/events` —— 订阅一个异步任务的进度流。
返回 `text/event-stream`，事件 schema：

| event   | data |
|---------|------|
| started | `{"task_id":..., "n":..., "rounds":..., "kind":...}` |
| progress| `{"task_id":..., "round":..., "stage":...}` *（占位，当前未发出；预留给 SocialRoundsRunner/BatchRunner 后续接入）* |
| done    | `{"task_id":..., "n_valid":..., "n_total":...}` |
| error   | `{"task_id":..., "error":...}` |

订阅迟到的客户端会先收到所有历史事件（环形 buffer，默认 1024 条），再切到 live。
租户隔离：只能订阅自己 tenant 创建的 task，否则 404。

```bash
# 用 curl 订阅（-N 关闭缓冲）
curl -N -H "X-API-Key: demo-key" \
  http://localhost:8000/v1/simulations/<task_id>/events
```

事件总线为进程内（与 task store 同生命周期）；多副本部署需替换为 Redis pub/sub。

### 持久化（M3-6 / M3-9 SQLite ↔ PostgreSQL 自由切换）

`WANXIANG_TASKS_DB` 接受 DSN，按 scheme 自动派发：

| DSN | 后端 | 用途 |
|---|---|---|
| _(未设)_ | 内存 | 开发 / 演示 |
| `/data/wanxiang.db` 或 `sqlite:///data/wanxiang.db` | SQLite | 单机生产、小规模 (<10 RPS) |
| `postgresql://user:pass@host:port/dbname` | PostgreSQL | 多机 / 大规模 / 多副本 |

切换零代码改动：换环境变量即可。表结构两边一致（`simulation_tasks` + tenant 索引），所有日期/JSON 字段均 TEXT 存储，便于跨库迁移。

Docker compose（Postgres 版）：
```yaml
services:
  api:
    environment:
      - WANXIANG_TASKS_DB=postgresql://wanxiang:secret@db:5432/wanxiang
    depends_on: [db]
  db:
    image: postgres:16
    environment:
      - POSTGRES_USER=wanxiang
      - POSTGRES_PASSWORD=secret
      - POSTGRES_DB=wanxiang
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

历史列表 API：
```bash
curl http://localhost:8000/v1/simulations?limit=20 -H "X-API-Key: demo-key"
```

### 可观测性（M3-7）

**请求追踪**
所有响应自动带 `X-Request-Id` 头；客户端可主动传 `X-Request-Id` 用作链路 ID。

**指标采集**
`GET /metrics` 返回内存累积的计数器与直方图 JSON（非鉴权，建议在网络/防火墙层面只对内网开放）。包含：
- `auth.success` / `auth.failure` / `auth.rate_limited`（按 tenant_id / reason 维度）
- `simulate.requested`（按 kind / mode：sync|async）
- `simulate.completed`（按 status：done|failed）
- `simulate.elapsed_ms`（histogram，按 kind）

样例：
```bash
curl http://localhost:8000/metrics
```

**结构化访问日志**
默认人类可读 text 格式。设置 `WANXIANG_LOG_JSON=1` 启用一行 JSON 日志（适合 ELK/Loki/CloudWatch 解析）。`/healthz` 和 `/metrics` 自动从 access 日志中过滤掉（避免噪声）。

## 健康检查

- `GET /healthz` 返回 `{"status":"ok"}` 即服务存活
- Dockerfile 内置 HEALTHCHECK 每 30s 探测一次

## 接入文档

- OpenAPI 自动文档：`http://<host>:8000/docs`
- ReDoc 视图：`http://<host>:8000/redoc`

### 场景模板（M4）

无需手写 `ScenarioConfig`——选模板，填空，喂给 `/v1/simulate`。

| id | 类型 | 用途 |
|---|---|---|
| `consumer_concept_test` | choose | 消费洞察 · 新品概念测试 |
| `marketing_ad_ab_test` | rate | 营销预测 · 广告创意 A/B |
| `brand_sentiment_probe` | sentiment | 品牌舆情 · 情感探测 |

```bash
# 列表
curl http://localhost:8000/v1/templates -H "X-API-Key: demo-key"

# 单个详情（含模板原文与变量定义）
curl http://localhost:8000/v1/templates/marketing_ad_ab_test \
  -H "X-API-Key: demo-key"

# 实例化（拿到 scenario payload）
curl -X POST http://localhost:8000/v1/templates/marketing_ad_ab_test/instantiate \
  -H "X-API-Key: demo-key" -H "Content-Type: application/json" \
  -d '{"values":{"brand":"X","product_name":"Y","category":"饮品",
                  "ad_copy":"0糖0卡","price":6},"options":null}'
# => {"material":"...","question":"...","kind":"rate","options":null}
# 这个 payload 直接放进 POST /v1/simulate 的 scenario 字段即可。
```

### NL 意图解析（M3-8）—— "AI 首席模拟官"

用户用中文描述需求，后端 LLM 自动抽出 SimulateRequest：

```bash
curl -X POST http://localhost:8000/v1/chat/parse \
  -H "X-API-Key: demo-key" -H "Content-Type: application/json" \
  -d '{"user_text":"测一线 Z 世代对新品轻气泡 ¥6 的购买意愿"}'
```

返回：
```json
{
  "intent": "simulate",
  "request": { /* 完整 SimulateRequest，可直接 POST /v1/simulate */ },
  "missing": [],
  "explanation": "识别为购买意愿打分场景",
  "confidence": 0.92
}
```

若 `missing` 非空，UI 应向用户补问。chat.html 集成下一步：把按钮换为输入框，让 LLM 走这条管线。

### L3 平台方言激活（M0-B-3 收官）

`SimulateRequest.platform` 字段（可选）让社交模式按目标平台调整 peer signal 措辞：

| platform | relationship | 措辞示例 |
|---|---|---|
| `wechat` | strong | "你的好友圈里 X 占 60%（强关系传播）" |
| `reddit` | none | "社区热门 X，份额 60%" |
| `twitter` | weak/following | "关注的人里 X 占 60%" |
| `xiaohongshu` / `douyin` | weak/recommend | "算法推荐里 X 最受关注，份额 60%" |

仅在 `rounds > 0`（社交模式）生效；decision_only 模式忽略 platform。

```bash
curl -X POST http://localhost:8000/v1/simulate \
  -H "X-API-Key: demo-key" -H "Content-Type: application/json" \
  -d '{"distribution_path":"...","n":100,"scenario":{...},
       "rounds":2, "platform":"wechat", "model":{"provider":"stub"}}'
```

未知 platform 返 400。

### 因果归因 + 反事实推演（M6 收官）

**因果归因**：基线场景 + N 个可移除的"因素"片段 → 每个因素的贡献排名（移除前后指标差）。
**反事实推演**：基线 + N 个替代方案（改 material/question/options）→ 对比每个方案 vs 基线的指标差。

```bash
# 因果
curl -X POST http://localhost:8000/v1/causal -H "X-API-Key: demo-key" \
  -H "Content-Type: application/json" -d '{
    "baseline": { /* 完整 SimulateRequest */ },
    "factors": [
      {"id":"value_prop","label":"健康卖点","snippet":"0糖0卡"},
      {"id":"channel","label":"小红书种草","snippet":"小红书"}
    ]}'

# 反事实
curl -X POST http://localhost:8000/v1/counterfactual -H "X-API-Key: demo-key" \
  -H "Content-Type: application/json" -d '{
    "baseline": { /* 完整 SimulateRequest */ },
    "baseline_label": "原价 ¥6",
    "alternatives": [
      {"id":"cheap","label":"降到 ¥5","material_override":"... ¥5 ..."},
      {"id":"pricey","label":"涨到 ¥10","material_override":"... ¥10 ..."}
    ]}'
```

返回结构带 `rank` / `delta` / `delta_vs_baseline`，可直接喂给 `build_report(... causal=..., counterfactual=...)` 生成完整 Markdown 报告（含"## 因果归因"与"## 反事实推演"两节）。

### 真计费 / Usage（M3-10）

每次模拟（同步或异步）都会自动写入 `usage_events` 表，按 mode 计 cost_units：

| mode | 触发条件 | 计费公式 |
|---|---|---|
| `decision_only` | rounds=0 | `n` |
| `social` | rounds>0 且无 platform | `n × (rounds + 1)` |
| `platform` | rounds>0 且有 platform | `ceil(n × (rounds + 1) × 1.5)` |

查询：
```bash
# 当前月
curl http://localhost:8000/v1/usage/current -H "X-API-Key: demo-key"
# 指定月
curl "http://localhost:8000/v1/usage/monthly?year=2026&month=6" -H "X-API-Key: demo-key"
```
返回 `{period, total_cost_units, by_mode, by_status, events[…100]}`。租户严格隔离。

数据存储沿用 `WANXIANG_TASKS_DB`（SQLite / PG / 内存）；同一 DSN 同时存 task 与 usage（两张独立表）。

### 报告增强 (M6+)

在 M6 基础（aggregate 统计 + 因果归因 + 反事实推演）之上，新增 4 项报告维度：

| 维度 | 模块 | 触发条件 | 说明 |
|---|---|---|---|
| 劝退原因构成 | `wanxiang/reporting/rejection.py` | RATE/SENTIMENT/CLICK_PROBABILITY 低于阈值，或 CHOOSE 非首选 | 关键词桶（中英双语）归类被拒/低评样本的 `reasoning` 文本 |
| 群体情绪演化 | `wanxiang/reporting/trajectory.py` | `rounds > 0`（社交模式）且 ≥2 轮 | 每轮的 `n_valid / mean / p25 / p75`，揭示从众/分化趋势 |
| LLM 自然语言解读 | `wanxiang/reporting/commentary.py` | 任意时刻，由调用方提供 `model_call` | 150-250 字中文执行摘要，结论先行，不复述数字 |
| PDF 导出 | `wanxiang/reporting/pdf.py` | 任意 markdown 报告 | 纯 Python（`reportlab` + 内置 `STSong-Light` CIDFont），无外部二进制依赖 |

`build_report(...)` 新增三个可选 kwarg：`rejection_analysis` / `trajectory` / `commentary`。
`render_markdown(...)` 在原有节之后追加「## 劝退原因构成」「## 群体情绪演化」「## LLM 解读」三节（按需）。

**PDF 端点**：

```bash
# 直接喂 markdown
curl -X POST http://localhost:8000/v1/reports/pdf \
  -H "X-API-Key: demo-key" -H "Content-Type: application/json" \
  -d '{"markdown": "# 报告\n\n正文"}' \
  -o report.pdf

# 或喂已完成异步任务的 ID（从 task_store 取 result.markdown）
curl -X POST http://localhost:8000/v1/reports/pdf \
  -H "X-API-Key: demo-key" -H "Content-Type: application/json" \
  -d '{"task_id": "<uuid>"}' \
  -o report.pdf
```

约束：`markdown` 与 `task_id` 必须二选一（同给或同空 → 400）；
任务不存在或非自有 → 404；未完成 → 409；reportlab 未安装 → 503。

依赖安装：

```bash
pip install reportlab        # ~2 MB pure Python
```

### 变量组合自动展开 (M5)

`POST /v1/simulations/sweep` —— 一次请求触发笛卡尔展开后的多次同步模拟。
典型用法：A/B 投放对比（多份文案 × 多个渠道 = N 次模拟一键跑完）。

请求体在普通 `SimulateRequest` 字段基础上加 `variable_grid`：
每个 key 是一个变量轴，value 是该轴的候选值列表。
`scenario.material` 和 `scenario.question` 中的 `{var}` 占位符会被自动替换。

```bash
curl -X POST http://localhost:8000/v1/simulations/sweep \
  -H "X-API-Key: demo-key" -H "Content-Type: application/json" \
  -d '{
    "distribution_path": "wanxiang/datasources/distributions/cn_z_generation_v1.yaml",
    "n": 30, "seed": 1,
    "scenario": {
      "material": "看到广告：{copy}",
      "question": "在{channel}你会买吗？",
      "kind": "rate"
    },
    "rounds": 0,
    "model": {"provider": "stub"},
    "variable_grid": {
      "copy": ["五折大促", "买二送一"],
      "channel": ["小红书", "抖音", "视频号"]
    }
  }'
```

响应：

```json
{
  "total_combos": 6,
  "combos": [
    {
      "combo_id": "channel=小红书|copy=五折大促",
      "values": {"channel": "小红书", "copy": "五折大促"},
      "task_id": null,
      "result": { /* 完整 SimulateResponse */ },
      "error": null
    }
  ]
}
```

约束与说明：

- 上限 `MAX_SWEEP_COMBOS = 100`：超出（如 11×11=121）→ 400。
- `variable_grid` 至少有一个轴，每个轴至少有一个值，否则 → 422。
- `combo_id` 按轴名字母序排列，`|` 分隔；占位符缺失时原样保留。
- 每个 combo 单独写一条 `usage` 事件（成功/失败都写），账单与实际消耗一致。
- 单个 combo 失败不会中断整体；失败信息装到该 combo 的 `error` 字段。
- 当前仅同步模式（按 combo 顺序执行）；异步 sweep 在后续里程碑提供。

## M4 媒体环境动态注入 (MVP)

在 `scenario.media_pool` 提供候选内容池，`feed_k` 指定每个 persona 决策前
看到的条数。排序器按"persona 兴趣关键词 ∩ item 标签/标题 + 偏好渠道加成"
挑出 top-K，作为 system prompt 的前置上下文（"【你最近在信息流看到的内容】"）。

```json
{
  "scenario": {
    "material": "X 品牌新品",
    "question": "买不买？",
    "kind": "rate",
    "media_pool": [
      {"item_id":"1","title":"闺蜜推荐","body":"用了三天皮肤变好",
       "channel":"xhs","tags":["beauty"]},
      {"item_id":"2","title":"同事吐槽","body":"踩雷了","channel":"weibo",
       "tags":["beauty"]}
    ],
    "feed_k": 2
  }
}
```

- 排序公式：`2 * |tags ∩ keywords| + |title_words ∩ keywords| + 3 * (channel 偏好命中)`，稳定排序。
- `keywords` 取自 `persona.personality` / `persona.demographic` 中所有 str / list[str] 值的 split。
- 偏好渠道取自 `persona.media` 的键集合（与 spec §M2 的媒体消费习惯对齐）。
- `feed_k=0` 或 `media_pool=[]` → 无注入（完全向后兼容）。
- 排序器是 `wanxiang.media.environment.KeywordRanker`（MVP）；接口
  `Ranker.rank(persona, pool, k)` 是未来接入 OASIS recsys / TwHIN /
  向量召回的扩展点——替换实现而不改外部 API。
- 注入位置：system prompt 顶部（feed → persona 画像 → 用户提问），
  以保证不被对话过程"洗掉"。

### 微信关系可见性 (M3+)

当 `platform=wechat` 时，social 模式自动构建小世界好友图（Watts-Strogatz, k=6,
rewire_p=0.1，seed 取自 `req.seed`）。每个 agent 在 social 轮次中只能"看到"
自己好友的 L2 输出 — 与微信朋友圈"非好友不可见"的产品特性一致。

实现位置：`wanxiang/social_graph/graph.py` + `wanxiang/simulation/social.py`
中的 `per_focal_peer_signal` / `SocialRoundsRunner._run_per_focal_round`。

其他平台 (xiaohongshu/douyin/weibo/twitter/reddit) 保持公开广场不变 —
仍使用全局聚合后的同辈参考，对外行为零回归。

n ≤ 6 时退化为完全图（所有人互为好友），适合小样本快速测试。
焦点 agent 若没有任何好友则注入中立占位 `（暂无同辈数据）`，决策回退到
仅基于 persona + scenario。

### 合规模块 (M3-12)

请求体可附 `compliance` 策略：

```json
{
  "compliance": {
    "redact_pii": true,            // 报告里所有 PII 替换为 [REDACTED:<kind>]
    "dp_epsilon": 1.0,             // 聚合数值加 ε-DP Laplace 噪声
    "dp_sensitivity": 1.0,         // 个体贡献敏感度（评分 0-10 建议 1.0）
    "moderate_material": true      // scenario.material 过预设审核器
  }
}
```

**PII 检测**：覆盖 中国手机号 / 18 位身份证 / 13-19 位银行卡 / 邮箱。重叠时按优先级
（身份证 > 银行卡 > 手机）排他匹配，避免误标。

**差分隐私**：Laplace(scale = sensitivity / epsilon)。`epsilon=1.0` 强保护，
`10.0` 弱保护。仅对数值 kind 的 `mean / p25 / p50 / p75` 加噪，CHOOSE 类型
聚合不受影响。结果同时写入 `report.aggregate` 与 `report.recommendation`，
便于 chat.html 工件卡与下游消费者共用。

**内容审核**：默认 `NoOpModerator`（全部 SAFE）。生产环境通过
`app.state.moderator =` 注入：

- `KeywordBlocklistModerator(["禁词1","禁词2"])` — 本地兜底
- 接阿里云/腾讯云/OpenAI moderation — 实现 `ModeratorProtocol.check(text)
  -> ModerationResult` 即可

不传 `compliance` 字段 → 行为完全等同于历史接口。

### 审计日志 (M3-13)

`GET /v1/audit/events?start=ISO&end=ISO&action=api_call&limit=100` — 查询当前租户审计记录。

**自动记录**：所有 POST/PUT/PATCH/DELETE 写操作（除 `/healthz`、`/metrics`、`/`、`/prototype/*`）
经 `AuditMiddleware` 自动落库，字段包含 `method` / `path` / `status` / `ip` /
`user_agent` / `request_id` / `tenant_id`。

**存储**：复用 `WANXIANG_TASKS_DB`（同 SQLite 文件或 PG 实例的独立 `audit_events` 表）。
未配置 DSN 时退回内存 store（仅本进程可见，重启后丢失）。

**租户隔离**：严格按 `X-API-Key` 鉴权后的 `tenant_id` 隔离查询，禁止跨租户读取。
未带或带错 API key → 401；422 校验失败的请求也会被审计（只要 API key 合法）。

**返回**：
```json
{
  "total": 42,
  "by_action": {"api_call": 42},
  "by_status": {"200": 30, "202": 8, "422": 4},
  "events": [
    {"event_id":"...","tenant_id":"acme","action":"api_call",
     "resource_type":"api","resource_id":null,"request_id":"...",
     "method":"POST","path":"/v1/simulate","status":200,
     "ip":"127.0.0.1","user_agent":"curl/8.0","detail":null,
     "recorded_at":"2026-06-14T14:37:58.660178+00:00"}
  ]
}
```

**容错**：审计写失败永远不会阻塞业务请求（中间件内 try/except pass）。

## 下一步（路线图）

- ~~M3-2 异步任务：长时间模拟改为 task_id + 轮询，避免 HTTP 超时~~ ✓ 已完成
- ~~M3-3 多租户：API key 鉴权 + 配额（每租户 RPM 上限）~~ ✓ 已完成
- M3-4 chat.html 接入：前端从静态原型切到真实 API
- 持久化：sqlite/postgres 存沙盒与历史

### 数据本地化与私有化部署 (合规, §8)

万象的设计严格遵循「数据不出境 + 模型可本地化」原则，便于通过金融/政企/医疗等
行业的合规审计：

**数据全程本地化**
- 任务/计费/审计三库（`WANXIANG_TASKS_DB`）默认 SQLite 单文件，落在客户自有机器；
  生产环境可改为客户内网 PostgreSQL（`postgresql://...` DSN，零代码切换）
- Persona 分布数据 `wanxiang/datasources/distributions/*.yaml` 是静态资源，客户可
  替换为自有授权分布（统计年鉴 / 行业报告 / 授权采购的脱敏面板）
- Scenario 物料、模拟结果、报告 PDF 全部在租户库内，未向第三方发送

**模型可私有化**
- 默认 `provider=stub` 离线 (开发/演示)
- `provider=deepseek` 走 DeepSeek API（请求出境）
- 客户私有部署：`provider=custom`，`base_url=https://内网LLM网关/v1`，
  `api_key=<内部密钥>` —— `wanxiang/models/adapter.py` 的 `wrap_camel_model`
  接 OpenAI 兼容协议，凡国内厂商 (通义/豆包/智谱/Yi/百川) 均支持

**租户级模型默认**（D3）
- `WANXIANG_TENANTS_JSON` 内每个 tenant 可附 `default_model_config`，金融客户
  绑定本地 vLLM 网关，互联网客户绑定 DeepSeek，互不干扰

**合规边界一图**

```
┌─────────── 客户内网 (数据不出境) ───────────┐
│ wanxiang process (Docker)                   │
│ ├─ tasks/usage/audit DB (sqlite or PG)      │
│ ├─ persona distributions (本地 yaml)         │
│ └─ HTTP API (内网域名/反向代理)              │
│                                              │
│         ↕  (仅模型推理出网，可关闭)          │
│                                              │
│  外网: 模型 API (可选)                       │
│  └─ DeepSeek / 通义 / 内网 vLLM             │
└──────────────────────────────────────────────┘
```

**合规自检清单**
- [ ] 已设置 `WANXIANG_TASKS_DB=postgresql://内网/...` （或 SQLite 落在客户存储）
- [ ] 已替换 `wanxiang/datasources/distributions/` 为客户授权的脱敏分布
- [ ] 已设置租户的 `default_model_config` 指向内网 LLM 网关
- [ ] 已通过 `compliance.redact_pii=true` 验证报告无 PII 漏出
- [ ] 已通过 `compliance.moderate_material=true` + 接入审核服务
- [ ] 已通过 GET /v1/audit/events 验证审计链完整
