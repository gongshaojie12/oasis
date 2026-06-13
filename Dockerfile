# WANXIANG API 镜像 (spec §M7/M3-5)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 系统依赖：git 用于装某些 pip 包；libgomp1 是 sentence-transformers/torch 运行期需要
RUN apt-get update && apt-get install -y --no-install-recommends \
    git libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 先拷贝最小依赖清单装包，提高 Docker 层缓存命中率
COPY pyproject.toml ./
# 直接装 wanxiang 运行期必需依赖（不走 poetry，简化）
RUN pip install --upgrade pip && \
    pip install \
        "camel-ai==0.2.78" \
        fastapi==0.136.3 \
        "uvicorn[standard]==0.49.0" \
        pydantic==2.13.4 \
        pydantic-settings==2.14.1 \
        pyyaml==6.0.3 \
        numpy pandas igraph neo4j scikit-learn sentence-transformers tqdm

# 拷贝源码
COPY oasis ./oasis
COPY engine ./engine
COPY wanxiang ./wanxiang

# 非 root 用户跑
RUN useradd -ms /bin/bash wanxiang && chown -R wanxiang:wanxiang /app
USER wanxiang

ENV WANXIANG_HOST=0.0.0.0 \
    WANXIANG_PORT=8000 \
    WANXIANG_LOG_LEVEL=info

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request as r; r.urlopen('http://localhost:8000/healthz').read()" || exit 1

CMD ["python", "-m", "wanxiang.api.server"]
