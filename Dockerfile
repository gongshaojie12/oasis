# WANXIANG API 镜像 (spec §M7/M3-5)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_TRUSTED_HOST=mirrors.aliyun.com

WORKDIR /app

# 切换 APT 源到国内阿里云镜像 (sed 不可靠, 直接覆写整个 DEB822 sources 文件)
# 用 HTTP 而非 HTTPS 是为了避免 ca-certificates 未装时的 cert 问题
RUN set -eux; \
    rm -f /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources; \
    printf 'Types: deb\nURIs: http://mirrors.aliyun.com/debian\nSuites: trixie trixie-updates\nComponents: main contrib non-free non-free-firmware\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\n\nTypes: deb\nURIs: http://mirrors.aliyun.com/debian-security\nSuites: trixie-security\nComponents: main contrib non-free non-free-firmware\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\n' > /etc/apt/sources.list.d/debian.sources; \
    cat /etc/apt/sources.list.d/debian.sources; \
    apt-get -o Acquire::Retries=3 update; \
    apt-get install -y --no-install-recommends --fix-missing git libgomp1; \
    rm -rf /var/lib/apt/lists/*

# 先拷贝最小依赖清单装包，提高 Docker 层缓存命中率
COPY pyproject.toml ./
# wanxiang 运行期必需依赖 (精简版: 移除 torch/sentence-transformers/neo4j/igraph
# 等 wanxiang 实际不用的 OASIS 旧依赖, 节省 ~700MB 镜像大小 + 15min 构建时间)
# pip 源已通过 PIP_INDEX_URL 切到阿里云 mirror
RUN pip install --upgrade pip && \
    pip install \
        "camel-ai==0.2.78" \
        fastapi==0.136.3 \
        "uvicorn[standard]==0.49.0" \
        pydantic==2.13.4 \
        pydantic-settings==2.14.1 \
        pyyaml==6.0.3 \
        numpy tqdm \
        "celery[redis]==5.4.0" \
        "redis==5.0.7" \
        "psycopg[binary]==3.3.4" \
        reportlab==4.5.1

# 拷贝源码
COPY oasis ./oasis
COPY engine ./engine
COPY wanxiang ./wanxiang
# 前端原型 (chat.html) - 让 / 主页能渲染对话 UI
COPY docs/prototype ./docs/prototype

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
