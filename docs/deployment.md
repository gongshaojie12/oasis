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

## 下一步（路线图）

- ~~M3-2 异步任务：长时间模拟改为 task_id + 轮询，避免 HTTP 超时~~ ✓ 已完成
- ~~M3-3 多租户：API key 鉴权 + 配额（每租户 RPM 上限）~~ ✓ 已完成
- M3-4 chat.html 接入：前端从静态原型切到真实 API
- 持久化：sqlite/postgres 存沙盒与历史
