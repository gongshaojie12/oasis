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
