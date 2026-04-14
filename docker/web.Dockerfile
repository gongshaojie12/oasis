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
