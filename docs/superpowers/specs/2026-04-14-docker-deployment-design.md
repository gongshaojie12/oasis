# Docker Deployment Design Spec

## Overview

为 OASIS 商业平台提供 Docker Compose 生产部署方案，目标服务器为 CentOS 2核2G，通过阿里云 DNS 域名解析直接访问。

## Architecture

```
用户 (域名:80) → 阿里云DNS → 服务器IP:80
                                 → web 容器 (Nuxt 3 SSR, 端口 80)
                                     ↕ 内部网络 (http://engine:8000)
                                 → engine 容器 (FastAPI, 端口 8000, 不对外暴露)

数据持久化 (宿主机挂载):
  - ./data/sqlite/oasis.db   → web 容器
  - ./data/reports/           → engine 容器 (模拟报告产出)
```

## Containers

### web (Nuxt 3)

- **Base image**: `node:20-alpine` (multi-stage build)
- **Build stage**: 安装依赖 + `nuxt build` 产出 `.output/`
- **Runtime stage**: 仅复制 `.output/` + `node_modules`（生产依赖），alpine 运行
- **Memory limit**: 512MB
- **Port**: 80 (对外)
- **Env**: DATABASE_TYPE, DATABASE_URL, JWT_SECRET, ENGINE_URL, INTERNAL_API_KEY, ENCRYPTION_KEY, SMS_ACCESS_KEY, SMS_ACCESS_SECRET
- **Health check**: `curl -f http://localhost:3000/api/health`
- **Note**: Nuxt Nitro 默认监听 3000，通过 docker-compose ports 映射为 80:3000

### engine (FastAPI)

- **Base image**: `python:3.10-slim` (multi-stage build)
- **Build stage**: 安装 engine/requirements.txt
- **Runtime stage**: 复制依赖 + engine/ + oasis/ 代码
- **Memory limit**: 768MB
- **Port**: 8000 (仅内部网络)
- **Env**: NUXT_CALLBACK_URL, INTERNAL_API_KEY, MAX_CONCURRENT_TASKS, DEFAULT_LLM_PROVIDER, DEFAULT_LLM_MODEL, 各 LLM API Key
- **Health check**: `curl -f http://localhost:8000/engine/health`
- **Command**: `uvicorn engine.main:app --host 0.0.0.0 --port 8000`

## File Structure

```
project-root/
  docker/
    web.Dockerfile          # Nuxt 3 多阶段构建
    engine.Dockerfile       # FastAPI 多阶段构建
  docker-compose.prod.yml   # 生产编排
  .dockerignore             # 排除不需要的文件
  .env.production.example   # 生产环境变量模板（合并 web + engine）
  deploy.sh                 # 一键部署脚本
```

## Environment Configuration

统一 `.env.production` 文件管理所有环境变量：

```env
# === Web (Nuxt) ===
DATABASE_TYPE=sqlite
DATABASE_URL=file:./data/oasis.db
JWT_SECRET=<随机32位字符串>
ENCRYPTION_KEY=<64位hex字符串>
INTERNAL_API_KEY=<随机密钥>
ENGINE_URL=http://engine:8000
SMS_ACCESS_KEY=
SMS_ACCESS_SECRET=

# === Engine (FastAPI) ===
NUXT_CALLBACK_URL=http://web:3000
MAX_CONCURRENT_TASKS=2
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=
QWEN_API_KEY=
DOUBAO_API_KEY=
MINIMAX_API_KEY=
ZHIPU_API_KEY=
KIMI_API_KEY=
OPENAI_API_KEY=

# === Host ===
HOST_PORT=80
```

Web 和 Engine 容器各自只读取自己需要的变量，多余变量会被忽略。

## Data Persistence

| 宿主机路径 | 容器挂载点 | 用途 |
|-----------|-----------|------|
| `./data/sqlite/` | web `/app/data/` | SQLite 数据库文件 |
| `./data/reports/` | engine `/app/reports/` | 模拟报告产出 |

容器重建/升级不丢数据。

## PostgreSQL Migration Path

切换到 PostgreSQL 只需：
1. 在 `docker-compose.prod.yml` 中添加 `postgres` 服务
2. 修改 `.env.production`：`DATABASE_TYPE=pg`，`DATABASE_URL=postgresql://...`
3. 运行 Drizzle migration

现有 Drizzle schema 已有 `pg.ts` 和 `sqlite.ts` 双版本，代码无需改动。

## Deploy Script

`deploy.sh` 提供一键操作：

```bash
./deploy.sh start    # 首次启动：构建 + 启动
./deploy.sh stop     # 停止
./deploy.sh restart  # 重启
./deploy.sh update   # 拉取最新代码 + 重新构建 + 滚动重启
./deploy.sh logs     # 查看日志
./deploy.sh status   # 查看状态
```

## Memory Budget (2G)

| Component | Estimated |
|-----------|-----------|
| CentOS OS + system | ~300MB |
| Docker daemon | ~150MB |
| web container (Nuxt SSR) | ~200-400MB |
| engine container (FastAPI idle) | ~100-200MB |
| **Total (idle)** | **~750MB-1050MB** |
| **Available for simulations** | **~950MB-1250MB** |

模拟运行时 Agent 内存按需分配，MAX_CONCURRENT_TASKS 控制并发上限。

## Restart Policy

两个容器均设置 `restart: unless-stopped`，崩溃自动重启，手动 stop 不会自动启动。

## Security

- Engine 端口不对外暴露（仅 Docker 内部网络）
- INTERNAL_API_KEY 保护 web ↔ engine 通信
- `.env.production` 文件权限设置为 600（仅 root 可读）
- `.dockerignore` 排除 `.env*`、`.git`、`node_modules` 等
