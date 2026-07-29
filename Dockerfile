# Multi-stage build for Medical Match Service (MMS)
# Phase D: 支持 local/shared 两种引擎加载模式

FROM python:3.11-slim as builder

WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖定义（从 match_service 子目录）
COPY match_service/pyproject.toml match_service/poetry.lock* ./

# 安装 poetry 并导出依赖
RUN pip install --no-cache-dir poetry && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes

# 生产镜像
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖并安装
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码（从 match_service/src）
COPY match_service/src/ ./src/

# Phase A 完成：使用内置引擎（local 模式），不再依赖 acrac_backend
# 引擎代码已迁移到 src/match_service/engine/

# 环境变量
ENV PYTHONPATH=/app/src
ENV MATCH_SVC_ENGINE_MODE=local
ENV MATCH_SVC_HOST=0.0.0.0
ENV MATCH_SVC_PORT=9100

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9100/health').read()"

# 暴露端口
EXPOSE 9100

# 启动服务
CMD ["python", "-m", "uvicorn", "match_service.main:app", "--host", "0.0.0.0", "--port", "9100"]
