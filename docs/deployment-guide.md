# OASIS 部署指南

## 目录

- [项目架构](#项目架构)
- [文件说明](#文件说明)
- [一、Windows 本地测试部署](#一windows-本地测试部署)
- [二、CentOS 服务器生产部署](#二centos-服务器生产部署)
- [三、日常运维操作](#三日常运维操作)
- [四、故障排查](#四故障排查)
- [五、配置参数说明](#五配置参数说明)
- [六、PostgreSQL 迁移](#六postgresql-迁移)

---

## 项目架构

```
用户 (域名/IP:80) → Web 容器 (Nuxt 3, 端口 3000)
                         ↕ Docker 内部网络
                     Engine 容器 (FastAPI, 端口 8000, 不对外暴露)

数据持久化:
  ./data/sqlite/oasis.db  → Web 容器 (SQLite 数据库)
  ./data/reports/          → Engine 容器 (模拟报告)
```

| 容器 | 技术栈 | 内存限制 | 职责 |
|------|--------|---------|------|
| oasis-web | Node.js 20 (Alpine) | 512MB | 前端 SSR + API 路由 + 数据库 |
| oasis-engine | Python 3.10 (Slim) | 768MB | 模拟引擎 + LLM API 调用 |

---

## 文件说明

```
project-root/
  docker/
    web.Dockerfile          # Nuxt 3 多阶段构建镜像
    engine.Dockerfile       # FastAPI 多阶段构建镜像
  docker-compose.prod.yml   # Docker Compose 生产编排
  .env.production.example   # 环境变量模板（可提交到 Git）
  .env.production           # 实际环境变量（不提交到 Git，含密钥）
  deploy.sh                 # 一键部署脚本（Linux）
  .dockerignore             # Docker 构建排除文件
  data/                     # 数据持久化目录（自动创建）
    sqlite/                 # SQLite 数据库文件
    reports/                # 模拟报告产出
```

---

## 一、Windows 本地测试部署

### 1.1 前置条件

- **Docker Desktop for Windows**
  - 下载地址：https://www.docker.com/products/docker-desktop/
  - 安装后需要重启电脑
  - 启动 Docker Desktop，等待系统托盘的鲸鱼图标显示 "Docker Desktop is running"
  - 确保 WSL 2 已启用（Docker Desktop 安装向导会提示）

- **Git**（已安装）

### 1.2 验证 Docker 安装

打开 PowerShell 或 Git Bash，执行：

```bash
docker --version
# 预期输出: Docker version 2x.x.x, build xxxxxxx

docker compose version
# 预期输出: Docker Compose version v2.x.x
```

### 1.3 准备项目

```bash
# 进入项目目录
cd D:\project\oasis

# 确保在正确的分支
git checkout dev-0.0.1
```

### 1.4 配置环境变量

项目已生成好测试用的 `.env.production`，如需重新生成：

```bash
# 从模板复制
cp .env.production.example .env.production

# 编辑填写密钥（本地测试可以用任意值）
```

`.env.production` 测试参考值：

```env
HOST_PORT=80
DATABASE_TYPE=sqlite
DATABASE_URL=file:./data/oasis.db
JWT_SECRET=test-jwt-secret-at-least-32chars
ENCRYPTION_KEY=aabbccdd11223344aabbccdd11223344aabbccdd11223344aabbccdd11223344
INTERNAL_API_KEY=test-internal-key-12345
SMS_ACCESS_KEY=
SMS_ACCESS_SECRET=
ADMIN_USERNAME=admin
ADMIN_PASSWORD=oasis-admin-2026
TEST_PHONE=13800000000
TEST_SMS_CODE=888888
MAX_CONCURRENT_TASKS=2
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=your-deepseek-key-here
```

> 如果要测试模拟功能，至少填写一个 LLM API Key（如 DEEPSEEK_API_KEY）。
> 不填 API Key 也能启动平台，只是提交模拟任务时 Engine 会报错。

### 1.5 创建数据目录

```bash
mkdir -p data/sqlite data/reports
```

### 1.6 构建并启动

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

首次构建需要下载基础镜像和安装依赖，大约需要 5-15 分钟（取决于网络速度）。

### 1.7 查看构建/运行日志

```bash
# 查看所有服务日志（实时跟踪）
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f

# 只看 web 容器
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f web

# 只看 engine 容器
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f engine
```

### 1.8 验证服务

```bash
# 查看容器状态
docker compose -f docker-compose.prod.yml --env-file .env.production ps

# 预期输出:
# NAME           STATUS          PORTS
# oasis-web      Up (healthy)    0.0.0.0:80->3000/tcp
# oasis-engine   Up (healthy)
```

打开浏览器访问：

- **首页**: http://localhost
- **健康检查**: http://localhost/api/health
- **管理员登录**: http://localhost/admin/login （账号密码见 `.env.production` 中的 `ADMIN_USERNAME` / `ADMIN_PASSWORD`）

#### 测试账号使用方式

平台提供两种登录方式：

**方式一：管理员登录（无需手机验证码）**

1. 访问 http://localhost/admin/login
2. 输入用户名 `admin`，密码 `oasis-admin-2026`（或 `.env.production` 中配置的值）
3. 登录后直接进入 Dashboard

**方式二：手机号登录（使用测试号，无需真实短信）**

1. 首次使用需要先注册：访问 http://localhost/register
2. 填写企业名称、用户名，手机号输入 `13800000000`，验证码输入 `888888`
3. 注册成功后自动登录
4. 后续登录：访问 http://localhost/login，手机号 `13800000000`，验证码 `888888`

> 测试手机号和验证码由 `TEST_PHONE` / `TEST_SMS_CODE` 环境变量控制。
> 生产环境上线时，将这两个变量留空即可禁用测试号，所有用户走真实短信验证。

### 1.9 测试完成后停止

```bash
# 停止并移除容器
docker compose -f docker-compose.prod.yml --env-file .env.production down

# 如果要同时清除构建缓存
docker compose -f docker-compose.prod.yml --env-file .env.production down --rmi local
```

### 1.10 常见问题

**端口 80 被占用：**

修改 `.env.production` 中 `HOST_PORT=3080`，然后访问 http://localhost:3080

**构建失败 "npm ci" 报错：**

确保 `web/package-lock.json` 存在。如果不存在：
```bash
cd web && npm install && cd ..
```

**better-sqlite3 编译失败：**

这是因为 Alpine 缺少编译工具，Dockerfile 中已包含 `apk add python3 make g++`。如果仍有问题，检查 Docker Desktop 的 WSL 2 引擎是否正常运行。

---

## 二、CentOS 服务器生产部署

### 2.1 服务器要求

- 操作系统：CentOS 7/8/Stream
- 配置：至少 2 核 2GB 内存
- 磁盘：至少 20GB 可用空间
- 网络：可访问外网（下载 Docker 镜像、调用 LLM API）

### 2.2 安装 Docker

```bash
# 安装依赖
sudo yum install -y yum-utils

# 添加 Docker 仓库
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker 并设置开机自启
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
docker compose version
```

> 如果是 CentOS 8，且 yum 提示包冲突，可以先执行 `sudo yum remove podman buildah`

### 2.3 （可选）配置 Docker 镜像加速

国内服务器建议配置镜像加速，加快拉取速度：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 2.4 部署项目

```bash
# 克隆代码到服务器
cd /opt
sudo git clone <你的仓库地址> oasis
cd oasis

# 切换到部署分支
git checkout dev-0.0.1
```

### 2.5 配置环境变量

```bash
# 从模板创建配置文件
cp .env.production.example .env.production

# 编辑配置
vim .env.production
```

**必须修改的配置项：**

```env
# 生成安全的随机密钥（在服务器上执行以下命令生成）：
#   openssl rand -hex 16     → 用于 JWT_SECRET
#   openssl rand -hex 32     → 用于 ENCRYPTION_KEY
#   openssl rand -hex 16     → 用于 INTERNAL_API_KEY

JWT_SECRET=<替换为 openssl rand -hex 16 的输出>
ENCRYPTION_KEY=<替换为 openssl rand -hex 32 的输出>
INTERNAL_API_KEY=<替换为 openssl rand -hex 16 的输出>

# 管理员账号（设置安全的密码）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<替换为安全的密码>

# 测试手机号（生产环境建议留空以禁用）
TEST_PHONE=
TEST_SMS_CODE=

# 至少填写一个 LLM API Key
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

**设置文件权限（重要）：**

```bash
chmod 600 .env.production
```

### 2.6 启动服务

```bash
# 赋予部署脚本执行权限
chmod +x deploy.sh

# 启动（首次会构建镜像，约 10-20 分钟）
./deploy.sh start
```

### 2.7 验证部署

```bash
# 查看服务状态
./deploy.sh status

# 预期输出:
# NAME           STATUS          PORTS
# oasis-web      Up (healthy)    0.0.0.0:80->3000/tcp
# oasis-engine   Up (healthy)
#
# [OASIS] Health checks:
#   web:    OK
#   engine: OK
```

### 2.8 配置域名（阿里云 DNS）

1. 登录阿里云控制台 → 云解析 DNS
2. 找到你的域名 → 解析设置
3. 添加记录：
   - 记录类型：**A**
   - 主机记录：`@`（直接用主域名）或 `oasis`（用子域名 oasis.yourdomain.com）
   - 记录值：你的服务器公网 IP
   - TTL：10 分钟
4. 等待 DNS 生效（通常几分钟）
5. 访问 http://你的域名

### 2.9 配置防火墙

确保服务器的 80 端口对外开放：

```bash
# CentOS firewalld
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --reload

# 或者如果使用 iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
```

同时在阿里云安全组中放行 80 端口（入方向）。

---

## 三、日常运维操作

所有操作在项目根目录下执行。

### 3.1 使用 deploy.sh（Linux 服务器）

```bash
./deploy.sh start     # 构建并启动
./deploy.sh stop      # 停止所有服务
./deploy.sh restart   # 重启所有服务
./deploy.sh update    # 拉取最新代码 + 重新构建 + 重启
./deploy.sh logs      # 查看所有服务日志
./deploy.sh logs web  # 只看 web 日志
./deploy.sh logs engine  # 只看 engine 日志
./deploy.sh status    # 查看服务状态和健康检查
```

### 3.2 代码更新部署

```bash
# 方式一：使用部署脚本（推荐）
./deploy.sh update

# 方式二：手动操作
git pull origin dev-0.0.1
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

### 3.3 仅重启单个服务

```bash
# 只重启 web
docker compose -f docker-compose.prod.yml --env-file .env.production restart web

# 只重启 engine
docker compose -f docker-compose.prod.yml --env-file .env.production restart engine
```

### 3.4 进入容器调试

```bash
# 进入 web 容器
docker exec -it oasis-web sh

# 进入 engine 容器
docker exec -it oasis-engine bash
```

### 3.5 数据备份

```bash
# 备份 SQLite 数据库
cp data/sqlite/oasis.db data/sqlite/oasis.db.backup.$(date +%Y%m%d)

# 备份报告
tar czf reports-backup-$(date +%Y%m%d).tar.gz data/reports/
```

### 3.6 查看资源占用

```bash
docker stats --no-stream
```

---

## 四、故障排查

### 4.1 容器启动失败

```bash
# 查看详细日志
docker compose -f docker-compose.prod.yml --env-file .env.production logs web
docker compose -f docker-compose.prod.yml --env-file .env.production logs engine

# 查看容器状态
docker ps -a
```

### 4.2 健康检查失败

```bash
# 手动测试 web 健康检查
curl http://localhost/api/health

# 手动测试 engine 健康检查（从 web 容器内部）
docker exec oasis-web curl http://engine:8000/engine/health
```

### 4.3 内存不足 (OOM)

```bash
# 查看内存使用
docker stats --no-stream

# 查看是否有 OOM 记录
dmesg | grep -i "out of memory"
```

解决方案：
- 减少 `MAX_CONCURRENT_TASKS`（在 `.env.production` 中改为 1）
- 减少单次模拟的 Agent 数量

### 4.4 端口冲突

```bash
# 查看 80 端口占用
sudo lsof -i :80
# 或
sudo ss -tlnp | grep :80
```

解决方案：修改 `.env.production` 中 `HOST_PORT` 为其他端口。

### 4.5 完全重置

```bash
# 停止并删除容器、网络、镜像
docker compose -f docker-compose.prod.yml --env-file .env.production down --rmi local --volumes

# 清除构建缓存
docker builder prune -f

# 重新构建
./deploy.sh start
```

> 注意：`--volumes` 会删除 Docker 管理的卷，但 `./data/` 目录是宿主机挂载，不会被删除。

---

## 五、配置参数说明

### Web 服务配置

| 参数 | 说明 | 默认值 | 是否必填 |
|------|------|--------|---------|
| HOST_PORT | 对外暴露的端口 | 80 | 否 |
| DATABASE_TYPE | 数据库类型 (sqlite / pg) | sqlite | 否 |
| DATABASE_URL | 数据库连接字符串 | file:./data/oasis.db | 否 |
| JWT_SECRET | JWT 签名密钥（至少 32 位） | - | **是** |
| ENCRYPTION_KEY | AES 加密密钥（64 位 hex） | - | **是** |
| INTERNAL_API_KEY | Web ↔ Engine 内部通信密钥 | - | **是** |
| SMS_ACCESS_KEY | 阿里云短信 AccessKey | - | 否（不用短信可留空） |
| SMS_ACCESS_SECRET | 阿里云短信 AccessSecret | - | 否 |
| ADMIN_USERNAME | 管理员登录用户名 | - | 否（不设置则禁用管理员登录） |
| ADMIN_PASSWORD | 管理员登录密码 | - | 否 |
| TEST_PHONE | 测试手机号（跳过真实短信） | - | 否（留空则禁用测试号） |
| TEST_SMS_CODE | 测试手机号的固定验证码 | - | 否 |

### Engine 服务配置

| 参数 | 说明 | 默认值 | 是否必填 |
|------|------|--------|---------|
| MAX_CONCURRENT_TASKS | 最大并发模拟任务数 | 2 | 否 |
| DEFAULT_LLM_PROVIDER | 默认 LLM 提供商 | deepseek | 否 |
| DEFAULT_LLM_MODEL | 默认 LLM 模型 | deepseek-chat | 否 |
| DEEPSEEK_API_KEY | DeepSeek API Key | - | 至少填一个 |
| QWEN_API_KEY | 通义千问 API Key | - | 否 |
| DOUBAO_API_KEY | 豆包 API Key | - | 否 |
| MINIMAX_API_KEY | MiniMax API Key | - | 否 |
| ZHIPU_API_KEY | 智谱 API Key | - | 否 |
| KIMI_API_KEY | Kimi API Key | - | 否 |
| OPENAI_API_KEY | OpenAI API Key | - | 否 |

### 密钥生成方法

```bash
# JWT_SECRET（32 位 hex）
openssl rand -hex 16

# ENCRYPTION_KEY（64 位 hex）
openssl rand -hex 32

# INTERNAL_API_KEY（32 位 hex）
openssl rand -hex 16
```

---

## 六、PostgreSQL 迁移

当数据量增长或需要多实例部署时，可从 SQLite 迁移到 PostgreSQL。

### 6.1 修改 docker-compose.prod.yml

在 `services:` 下添加 postgres 服务：

```yaml
  postgres:
    image: postgres:16-alpine
    container_name: oasis-postgres
    restart: unless-stopped
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=oasis
      - POSTGRES_USER=oasis
      - POSTGRES_PASSWORD=${PG_PASSWORD}
    networks:
      - oasis-net
    deploy:
      resources:
        limits:
          memory: 256M
```

修改 web 服务的 `depends_on` 添加 postgres。

### 6.2 修改 .env.production

```env
DATABASE_TYPE=pg
DATABASE_URL=postgresql://oasis:your-pg-password@postgres:5432/oasis
PG_PASSWORD=your-pg-password
```

### 6.3 运行数据库迁移

```bash
# 重新构建并启动
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# 进入 web 容器运行迁移
docker exec -it oasis-web sh
npx drizzle-kit push
```

> 注意：迁移到 PostgreSQL 后，服务器至少需要 2.5GB 内存。代码无需修改，Drizzle ORM 已支持 SQLite 和 PostgreSQL 双 schema。
