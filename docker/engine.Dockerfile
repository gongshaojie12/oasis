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
