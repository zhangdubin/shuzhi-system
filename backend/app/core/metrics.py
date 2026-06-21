"""
Prometheus 指标中间件
- HTTP 请求 QPS / p50 / p95 / p99（自动 histogram）
- HTTP 状态码分布
- 慢请求计数（>500ms）
- 业务指标：OCR 识别数、验真数、AI 调用数、登录数
- /metrics 端点暴露给 prometheus 抓取
"""
import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
)

# ============================================================
# 自定义 registry（避免与默认 registry 冲突）
# ============================================================
REGISTRY = CollectorRegistry(auto_describe=True)


# ============================================================
# HTTP 指标
# ============================================================

# QPS 计数（按 method + path + status 维度）
http_requests_total = Counter(
    "shuzhi_http_requests_total",
    "HTTP 请求总数",
    labelnames=["method", "path", "status"],
    registry=REGISTRY,
)

# 响应时间（按 method + path 维度）
http_request_duration_seconds = Histogram(
    "shuzhi_http_request_duration_seconds",
    "HTTP 请求响应时间（秒）",
    labelnames=["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

# 慢请求计数（>500ms）
http_slow_requests_total = Counter(
    "shuzhi_http_slow_requests_total",
    "慢请求计数（>500ms）",
    labelnames=["method", "path", "status"],
    registry=REGISTRY,
)

# ============================================================
# R11A：DB 慢查询监控（>200ms 记 prometheus counter）
# ============================================================
db_slow_queries_total = Counter(
    "shuzhi_db_slow_queries_total",
    "DB 慢查询总数（>200ms）",
    labelnames=["table", "operation"],  # operation: SELECT/INSERT/UPDATE/DELETE
    registry=REGISTRY,
)
db_query_duration_seconds = Histogram(
    "shuzhi_db_query_duration_seconds",
    "DB 查询响应时间（秒）",
    labelnames=["table", "operation"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY,
)

# 当前活跃请求数
http_in_flight_requests = Gauge(
    "shuzhi_http_in_flight_requests",
    "当前在处理的 HTTP 请求数",
    registry=REGISTRY,
)


# ============================================================
# 业务指标（R7.2 业务可观测性）
# ============================================================

# OCR 识别
business_ocr_total = Counter(
    "shuzhi_business_ocr_total",
    "OCR 识别总数",
    labelnames=["status", "mode"],  # status: success/failed, mode: real/mock
    registry=REGISTRY,
)

# 诺诺验真
business_verify_total = Counter(
    "shuzhi_business_verify_total",
    "诺诺验真总数",
    labelnames=["result", "mode"],  # result: pass/risk/repeat/not_found, mode: real/mock
    registry=REGISTRY,
)

# AI 调用
business_ai_total = Counter(
    "shuzhi_business_ai_total",
    "AI 调用总数",
    labelnames=["type", "cache"],  # type: ask/risk_scan/extract, cache: hit/miss
    registry=REGISTRY,
)

# 登录
business_login_total = Counter(
    "shuzhi_business_login_total",
    "登录总数",
    labelnames=["method", "result"],  # method: password/sso, result: success/failed
    registry=REGISTRY,
)


# ============================================================
# 中间件
# ============================================================

async def prometheus_middleware(request: Request, call_next: Callable):
    """
    Prometheus HTTP 指标中间件
    - 计算每个请求的响应时间
    - 累加 QPS + 状态码分布
    - 慢请求（>500ms）单独计数
    - /metrics 端点不计入指标
    """
    # 跳过 /metrics 自身
    if request.url.path == "/metrics":
        return await call_next(request)

    method = request.method
    # 路径归一化（避免高基数：/api/v1/contracts/123 -> /api/v1/contracts/{id}）
    path = _normalize_path(request.url.path)
    status_code = 500  # 异常时默认 500
    elapsed = 0.0

    http_in_flight_requests.inc()
    try:
        start = time.perf_counter()
        response: Response = await call_next(request)
        status_code = response.status_code
        elapsed = time.perf_counter() - start

        # 累加指标
        http_requests_total.labels(method=method, path=path, status=str(status_code)).inc()
        http_request_duration_seconds.labels(method=method, path=path).observe(elapsed)

        if elapsed > 0.5:  # >500ms
            http_slow_requests_total.labels(method=method, path=path, status=str(status_code)).inc()

        return response
    except Exception as e:
        # 异常也算 500
        status_code = 500
        http_requests_total.labels(method=method, path=path, status="500").inc()
        raise
    finally:
        http_in_flight_requests.dec()


def _normalize_path(path: str) -> str:
    """
    路径归一化（避免高基数）
    /api/v1/contracts/123 -> /api/v1/contracts/{id}
    /api/v1/invoice/ocr/F-2026-ABC123.png -> /api/v1/invoice/ocr/{file_id}
    """
    import re

    # ID 类（数字）
    path = re.sub(r"/(\d+)(?=/|$)", "/{id}", path)
    # 文件 ID 类（F-2026-XXXXX）
    path = re.sub(r"/(F-\d{4}-[A-Z0-9]+)(?=/|$)", "/{file_id}", path)
    # 通用 token（长字符串）
    path = re.sub(r"/([a-f0-9]{20,})(?=/|$)", "/{token}", path)
    return path


# ============================================================
# /metrics 端点
# ============================================================

def metrics_endpoint() -> Response:
    """暴露 /metrics 给 prometheus 抓取"""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
