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

### 持久化（M3-6）

设置 `WANXIANG_TASKS_DB=/data/wanxiang.db`（任何宿主可写路径）启用 SQLite 持久化：

- 任务/结果跨重启保留
- 同一 tenant 可拉历史：`GET /v1/simulations?limit=20&offset=0`
- 不设此环境变量时回退为内存 store（开发/演示用）

Docker 用户在 `docker-compose.yml` 增加：

```yaml
services:
  api:
    environment:
      - WANXIANG_TASKS_DB=/data/wanxiang.db
    volumes:
      - ./data:/data
```

历史列表 API：

```bash
curl http://localhost:8000/v1/simulations?limit=20 \
  -H "X-API-Key: demo-key"
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

## 下一步（路线图）

- ~~M3-2 异步任务：长时间模拟改为 task_id + 轮询，避免 HTTP 超时~~ ✓ 已完成
- ~~M3-3 多租户：API key 鉴权 + 配额（每租户 RPM 上限）~~ ✓ 已完成
- M3-4 chat.html 接入：前端从静态原型切到真实 API
- 持久化：sqlite/postgres 存沙盒与历史
