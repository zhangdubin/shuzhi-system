# ============================================================
# 报销中心 - 独立 FastAPI 子服务（端口 8002）
# ============================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# 共享主后端 requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install 'bcrypt==3.2.2' && \
    pip install 'SQLAlchemy==2.0.50' && \
    pip install 'greenlet>=3.0.0' && \
    pip install 'openpyxl>=3.1.0'

# 共享代码
COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8002
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8002/health || exit 1

# 启动报销中心独立服务
CMD ["uvicorn", "app.modules.reimbursement.standalone:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "2", "--proxy-headers"]
