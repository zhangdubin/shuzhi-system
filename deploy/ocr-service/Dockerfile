# ============================================================
# OCR 微服务（R19.1：rapidocr-onnxruntime 替代 paddlepaddle）
# ============================================================
FROM python:3.10-slim

ENV PYTHONDONTWRITETYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 换国内源
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/*.list 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list 2>/dev/null || true

WORKDIR /app

# 上传/数据目录
RUN mkdir -p /app/uploads /app/data && chmod 777 /app/uploads /app/data

# 系统依赖（OpenCV headless 需要 libgl）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# pip 国内源
RUN pip install --upgrade pip && \
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 服务代码
COPY ./app.py ./app.py
COPY ./engine.py ./engine.py
COPY ./postprocess.py ./postprocess.py

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
