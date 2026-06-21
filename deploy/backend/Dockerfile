# ============================================================
# 后端 - FastAPI
# ============================================================
FROM python:3.11-slim AS base

# 避免 .pyc 和强制 stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libheif-dev \
    libde265-dev  # HEIC/HEIF 解码依赖 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 依赖（缓存层）
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    # bcrypt 4.x 与 passlib 1.7.4 兼容性问题，固定 3.2.2
    pip install 'bcrypt==3.2.2' && \
    # SQLAlchemy 2.0.27 + asyncpg + greenlet 触发 MissingGreenlet，升 2.0.50 修
    pip install 'SQLAlchemy==2.0.50' && \
    # 关掉连接预检（pool_pre_ping 异步时也有 greenlet 风险）
    pip install 'greenlet>=3.0.0' && \
    # PDF 转码：发票 PDF 识别需要 PyMuPDF（fitz）
    pip install 'PyMuPDF>=1.24.0' && \
    # 对象存储 MinIO S3 兼容客户端
    pip install 'minio>=7.2.0'

# 代码
COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini .
COPY ./scripts ./scripts

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/uploads && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app/uploads
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# 默认启动：alembic 升级 + uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers"]
