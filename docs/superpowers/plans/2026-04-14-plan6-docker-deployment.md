# Docker Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create Docker Compose production deployment for the OASIS platform (2-container: Nuxt web + FastAPI engine) targeting a CentOS 2C2G server with domain access.

**Architecture:** Two containers on a shared Docker network. Web container (Nuxt 3 SSR) listens on port 80 via host mapping, serves both frontend and API. Engine container (FastAPI) only accessible on internal Docker network. SQLite data persisted via host volume mounts. All config via `.env.production`.

**Tech Stack:** Docker, Docker Compose, Node.js 20 Alpine, Python 3.10 Slim, Uvicorn.

---

## File Structure

```
project-root/
  docker/
    web.Dockerfile          # CREATE: Nuxt 3 multi-stage build
    engine.Dockerfile       # CREATE: FastAPI multi-stage build
  docker-compose.prod.yml   # CREATE: production orchestration
  .dockerignore             # CREATE: exclude unnecessary files
  .env.production.example   # CREATE: production env template
  deploy.sh                 # CREATE: one-click deployment script
```

---

## Task 1: .dockerignore

**Goal:** Prevent unnecessary files from being sent to Docker build context (speeds up builds, reduces image size).

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1.1: Create .dockerignore**

**File:** `.dockerignore`

```
# Git
.git
.gitignore

# IDE
.vscode
.idea
*.swp
*.swo

# Environment files (secrets)
.env
.env.*
!.env.production.example

# Node
web/node_modules
web/.nuxt
web/.output
web/data

# Python
__pycache__
*.pyc
*.pyo
.pytest_cache
*.egg-info
dist
build

# Docker
docker-compose*.yml
.dockerignore

# Dev tools
.container
.claude
docs
tests
*.md
!README.md
.pre-commit-config.yaml

# Data
data
*.db
*.sqlite
```

- [ ] **Step 1.2: Commit**

```bash
git add .dockerignore
git commit -m "chore: add .dockerignore for production builds"
```

---

## Task 2: Web Dockerfile (Nuxt 3)

**Goal:** Multi-stage Dockerfile for Nuxt 3. Build stage compiles the app, runtime stage runs the minimal Nitro server.

**Files:**
- Create: `docker/web.Dockerfile`

- [ ] **Step 2.1: Create web.Dockerfile**

**File:** `docker/web.Dockerfile`

```dockerfile
# ============================================
# Stage 1: Build
# ============================================
FROM node:20-alpine AS build

WORKDIR /app

# Install build tools for native modules (better-sqlite3)
RUN apk add --no-cache python3 make g++

# Install dependencies (lockfile ensures reproducibility)
COPY web/package.json web/package-lock.json ./
RUN npm ci

# Copy source and build
COPY web/ ./
RUN npm run build

# ============================================
# Stage 2: Runtime
# ============================================
FROM node:20-alpine

WORKDIR /app

# curl for health checks
RUN apk add --no-cache curl

# Copy built output (includes bundled deps + externalized native modules)
COPY --from=build /app/.output .output/

# Create data directory for SQLite
RUN mkdir -p /app/data

# Nitro listens on 0.0.0.0:3000 by default
ENV HOST=0.0.0.0
ENV PORT=3000

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

CMD ["node", ".output/server/index.mjs"]
```

**Key design decisions:**
- Both stages use `node:20-alpine` so native modules compiled in build stage are compatible with runtime
- `better-sqlite3` needs `python3 make g++` to compile, these are only in the build stage
- `.output/` is self-contained — Nitro bundles all JS deps, externalizes native modules to `.output/server/node_modules/`
- `HOST=0.0.0.0` is required so Nitro accepts connections from outside the container

- [ ] **Step 2.2: Commit**

```bash
git add docker/web.Dockerfile
git commit -m "feat(docker): add Nuxt web Dockerfile with multi-stage build"
```

---

## Task 3: Engine Dockerfile (FastAPI)

**Goal:** Multi-stage Dockerfile for the Python simulation engine. Build stage installs the oasis library and engine dependencies, runtime stage copies the virtual environment.

**Files:**
- Create: `docker/engine.Dockerfile`

- [ ] **Step 3.1: Create engine.Dockerfile**

**File:** `docker/engine.Dockerfile`

```dockerfile
# ============================================
# Stage 1: Build (install dependencies)
# ============================================
FROM python:3.10-slim AS build

WORKDIR /build

# Install build tools for native extensions (igraph, cairocffi, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libcairo2-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install oasis library (from project root pyproject.toml)
# poetry-core is the build backend, pip will download it automatically
COPY pyproject.toml poetry.lock README.md ./
COPY oasis/ oasis/
RUN pip install --no-cache-dir .

# Install engine dependencies
COPY engine/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.10-slim

WORKDIR /app

# Runtime system libraries (cairo for cairocffi) + curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from build stage
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy engine source code (not oasis — it's installed in the venv)
COPY engine/ engine/

# Create reports directory
RUN mkdir -p /app/reports

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/engine/health || exit 1

CMD ["uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Key design decisions:**
- `pip install .` installs the oasis package into the venv from pyproject.toml (poetry-core as build backend)
- Build tools (gcc, g++, libffi-dev, libcairo2-dev) only in build stage, not in runtime
- Runtime only has `libcairo2` (shared library needed by cairocffi at runtime) + `curl`
- oasis is installed as a Python package in the venv, so no need to COPY oasis/ to runtime
- engine/ is copied to /app/engine/, uvicorn runs from /app so `engine.main` is importable

- [ ] **Step 3.2: Commit**

```bash
git add docker/engine.Dockerfile
git commit -m "feat(docker): add FastAPI engine Dockerfile with multi-stage build"
```

---

## Task 4: Docker Compose + Environment Template

**Goal:** Create the production docker-compose file and environment variable template.

**Files:**
- Create: `docker-compose.prod.yml`
- Create: `.env.production.example`

- [ ] **Step 4.1: Create docker-compose.prod.yml**

**File:** `docker-compose.prod.yml`

```yaml
version: "3.8"

services:
  web:
    build:
      context: .
      dockerfile: docker/web.Dockerfile
    container_name: oasis-web
    restart: unless-stopped
    ports:
      - "${HOST_PORT:-80}:3000"
    volumes:
      - ./data/sqlite:/app/data
    environment:
      - DATABASE_TYPE=${DATABASE_TYPE:-sqlite}
      - DATABASE_URL=${DATABASE_URL:-file:./data/oasis.db}
      - JWT_SECRET=${JWT_SECRET}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - INTERNAL_API_KEY=${INTERNAL_API_KEY}
      - ENGINE_URL=http://engine:8000
      - SMS_ACCESS_KEY=${SMS_ACCESS_KEY:-}
      - SMS_ACCESS_SECRET=${SMS_ACCESS_SECRET:-}
    depends_on:
      engine:
        condition: service_healthy
    networks:
      - oasis-net
    deploy:
      resources:
        limits:
          memory: 512M

  engine:
    build:
      context: .
      dockerfile: docker/engine.Dockerfile
    container_name: oasis-engine
    restart: unless-stopped
    volumes:
      - ./data/reports:/app/reports
    environment:
      - NUXT_CALLBACK_URL=http://web:3000
      - INTERNAL_API_KEY=${INTERNAL_API_KEY}
      - MAX_CONCURRENT_TASKS=${MAX_CONCURRENT_TASKS:-2}
      - DEFAULT_LLM_PROVIDER=${DEFAULT_LLM_PROVIDER:-deepseek}
      - DEFAULT_LLM_MODEL=${DEFAULT_LLM_MODEL:-deepseek-chat}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
      - QWEN_API_KEY=${QWEN_API_KEY:-}
      - DOUBAO_API_KEY=${DOUBAO_API_KEY:-}
      - MINIMAX_API_KEY=${MINIMAX_API_KEY:-}
      - ZHIPU_API_KEY=${ZHIPU_API_KEY:-}
      - KIMI_API_KEY=${KIMI_API_KEY:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
    networks:
      - oasis-net
    deploy:
      resources:
        limits:
          memory: 768M

networks:
  oasis-net:
    driver: bridge
```

**Key design decisions:**
- Engine has no `ports` mapping — only accessible via Docker internal network
- `depends_on` with `service_healthy` ensures engine is ready before web starts
- `ENGINE_URL=http://engine:8000` uses Docker DNS (not localhost)
- `NUXT_CALLBACK_URL=http://web:3000` same principle for reverse communication
- Memory limits enforce the 2G budget
- `HOST_PORT` configurable, defaults to 80
- `restart: unless-stopped` — auto-restart on crash, but not after manual `docker compose stop`

- [ ] **Step 4.2: Create .env.production.example**

**File:** `.env.production.example`

```env
# ================================================
# OASIS Production Environment Configuration
# ================================================
# Copy this file to .env.production and fill in values:
#   cp .env.production.example .env.production
#
# IMPORTANT: chmod 600 .env.production
# ================================================

# === Host ===
HOST_PORT=80

# === Web (Nuxt) ===
DATABASE_TYPE=sqlite
DATABASE_URL=file:./data/oasis.db
JWT_SECRET=CHANGE_ME_TO_RANDOM_32_CHAR_STRING
ENCRYPTION_KEY=CHANGE_ME_TO_RANDOM_64_HEX_STRING
INTERNAL_API_KEY=CHANGE_ME_TO_RANDOM_SECRET
SMS_ACCESS_KEY=
SMS_ACCESS_SECRET=

# === Engine (FastAPI) ===
MAX_CONCURRENT_TASKS=2
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat

# === LLM API Keys (fill in at least one) ===
DEEPSEEK_API_KEY=
QWEN_API_KEY=
DOUBAO_API_KEY=
MINIMAX_API_KEY=
ZHIPU_API_KEY=
KIMI_API_KEY=
OPENAI_API_KEY=
```

- [ ] **Step 4.3: Commit**

```bash
git add docker-compose.prod.yml .env.production.example
git commit -m "feat(docker): add docker-compose.prod.yml and env template"
```

---

## Task 5: Deployment Script

**Goal:** Create a one-click deployment script that handles common operations: start, stop, restart, update, logs, status.

**Files:**
- Create: `deploy.sh`

- [ ] **Step 5.1: Create deploy.sh**

**File:** `deploy.sh`

```bash
#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

log() { echo -e "${GREEN}[OASIS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check prerequisites
check_deps() {
    command -v docker >/dev/null 2>&1 || err "Docker is not installed. Run: yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin"
    docker compose version >/dev/null 2>&1 || err "Docker Compose plugin is not installed."
    docker info >/dev/null 2>&1 || err "Docker daemon is not running. Run: systemctl start docker"
}

# Check env file
check_env() {
    if [ ! -f "$ENV_FILE" ]; then
        err ".env.production not found. Run:\n  cp .env.production.example .env.production\n  # Edit .env.production and fill in secrets\n  chmod 600 .env.production"
    fi

    # Check for placeholder values
    if grep -q "CHANGE_ME" "$ENV_FILE"; then
        warn "Found CHANGE_ME placeholders in $ENV_FILE. Please update them before production use."
    fi
}

# Create data directories
init_data() {
    mkdir -p data/sqlite data/reports
    log "Data directories ready"
}

case "${1:-help}" in
    start)
        check_deps
        check_env
        init_data
        log "Building and starting OASIS..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
        log "OASIS is starting. Check status: ./deploy.sh status"
        log "View logs: ./deploy.sh logs"
        ;;
    stop)
        check_deps
        log "Stopping OASIS..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
        log "OASIS stopped"
        ;;
    restart)
        check_deps
        check_env
        log "Restarting OASIS..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart
        log "OASIS restarted"
        ;;
    update)
        check_deps
        check_env
        init_data
        log "Pulling latest code..."
        git pull origin "$(git branch --show-current)"
        log "Rebuilding and restarting..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
        log "Update complete"
        ;;
    logs)
        check_deps
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f --tail=100 ${2:-}
        ;;
    status)
        check_deps
        echo ""
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
        echo ""
        log "Health checks:"
        echo -n "  web:    "
        curl -sf http://localhost:${HOST_PORT:-80}/api/health 2>/dev/null && echo "OK" || echo "NOT READY"
        echo -n "  engine: "
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T engine curl -sf http://localhost:8000/engine/health 2>/dev/null && echo "OK" || echo "NOT READY"
        ;;
    help|*)
        echo ""
        echo "OASIS Deployment Script"
        echo ""
        echo "Usage: ./deploy.sh <command>"
        echo ""
        echo "Commands:"
        echo "  start    Build and start all services"
        echo "  stop     Stop all services"
        echo "  restart  Restart all services"
        echo "  update   Pull latest code, rebuild, and restart"
        echo "  logs     View logs (optional: logs web | logs engine)"
        echo "  status   Show service status and health"
        echo ""
        ;;
esac
```

- [ ] **Step 5.2: Make deploy.sh executable and commit**

```bash
git add deploy.sh
git update-index --chmod=+x deploy.sh
git commit -m "feat(docker): add deployment script"
```

---

## Task 6: Build Verification

**Goal:** Verify docker-compose config is valid and document the deployment steps.

- [ ] **Step 6.1: Validate docker-compose config**

```bash
docker compose -f docker-compose.prod.yml config --quiet && echo "Config OK"
```

If docker is not available on the dev machine, at least verify the YAML is valid.

- [ ] **Step 6.2: Final commit**

```bash
git add -A
git commit -m "chore(docker): complete Docker deployment setup"
```

---

## Deployment Quick Start (for reference)

On the CentOS server:

```bash
# 1. Install Docker (if not already)
yum install -y yum-utils
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl start docker && systemctl enable docker

# 2. Clone repo
git clone <repo-url> /opt/oasis && cd /opt/oasis

# 3. Configure environment
cp .env.production.example .env.production
vim .env.production   # Fill in JWT_SECRET, ENCRYPTION_KEY, INTERNAL_API_KEY, LLM keys
chmod 600 .env.production

# 4. Deploy
chmod +x deploy.sh
./deploy.sh start

# 5. Verify
./deploy.sh status
```

---

## PostgreSQL Migration (future)

When ready to switch:

1. Add postgres service to `docker-compose.prod.yml`:
```yaml
  postgres:
    image: postgres:16-alpine
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=oasis
      - POSTGRES_USER=oasis
      - POSTGRES_PASSWORD=${PG_PASSWORD}
    networks:
      - oasis-net
```

2. Update `.env.production`:
```env
DATABASE_TYPE=pg
DATABASE_URL=postgresql://oasis:${PG_PASSWORD}@postgres:5432/oasis
```

3. Run Drizzle migration in the web container.

No code changes needed — Drizzle schema already has both `sqlite.ts` and `pg.ts`.

---

## Self-Review Checklist

1. **Spec coverage:** All items from the design spec are implemented:
   - web.Dockerfile with multi-stage build ✓
   - engine.Dockerfile with multi-stage build ✓
   - docker-compose.prod.yml with memory limits, health checks, internal network ✓
   - .env.production.example with all variables ✓
   - deploy.sh with start/stop/restart/update/logs/status ✓
   - .dockerignore ✓
   - Data persistence via volumes ✓
   - PostgreSQL migration path documented ✓

2. **Placeholder scan:** No TBD/TODO. All code complete.

3. **Type consistency:** Environment variable names match between docker-compose, .env template, engine/.env.example, and web/.env.example. Docker service names (`web`, `engine`) match the internal URLs (`http://web:3000`, `http://engine:8000`).
