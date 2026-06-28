"""
UDPE 打印引擎 — 并发压测脚本

目标：验证 50+ 并发请求下各端点的稳定性和性能。
运行方式：
  cd backend
  python -m pytest tests/test_print_load.py -v -s --tb=short

测试端点：
  1. GET  /admin/print-templates       — 模板列表
  2. POST /print/preview               — HTML 预览
  3. POST /print/pdf                   — PDF 导出
  4. GET  /admin/print-templates/{id}  — 模板详情
  5. GET  /admin/print-logs            — 打印日志

指标：
  - 总请求数 / 成功数 / 失败数
  - 平均响应时间 / P50 / P95 / P99
  - 吞吐量 (req/s)
"""
import asyncio
import os
import statistics
import time
from dataclasses import dataclass, field

import httpx
import pytest

# 压测配置
CONCURRENCY = 60          # 并发数
REQUESTS_PER_ENDPOINT = 120  # 每端点总请求数
TIMEOUT = 30.0            # 单请求超时(秒)

BASE_URL = os.environ.get("LOAD_TEST_BASE_URL", "http://localhost:8000")
ADMIN_USER = os.environ.get("LOAD_TEST_USER", "admin")
ADMIN_PASS = os.environ.get("LOAD_TEST_PASS", "admin123")


@dataclass
class RequestResult:
    endpoint: str
    status: int
    elapsed_ms: float
    error: str = ""


@dataclass
class EndpointStats:
    name: str
    results: list = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def success(self) -> int:
        return sum(1 for r in self.results if 200 <= r.status < 400)

    @property
    def failed(self) -> int:
        return self.total - self.success

    @property
    def times(self) -> list:
        return [r.elapsed_ms for r in self.results if 200 <= r.status < 400]

    def report(self) -> str:
        times = self.times
        if not times:
            return f"  {self.name}: ALL FAILED ({self.total} requests)"
        avg = statistics.mean(times)
        p50 = statistics.median(times)
        sorted_t = sorted(times)
        p95_idx = int(len(sorted_t) * 0.95)
        p99_idx = int(len(sorted_t) * 0.99)
        p95 = sorted_t[min(p95_idx, len(sorted_t) - 1)]
        p99 = sorted_t[min(p99_idx, len(sorted_t) - 1)]
        return (
            f"  {self.name}:\n"
            f"    total={self.total}  success={self.success}  failed={self.failed}\n"
            f"    avg={avg:.0f}ms  p50={p50:.0f}ms  p95={p95:.0f}ms  p99={p99:.0f}ms"
        )


async def _login(client: httpx.AsyncClient) -> str:
    """登录获取 token"""
    resp = await client.post(f"{BASE_URL}/api/v1/auth/login", json={
        "account": ADMIN_USER, "password": ADMIN_PASS,
    }, timeout=TIMEOUT)
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    return resp.json()["token"]


async def _send_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict,
    json_body: dict = None,
    endpoint_name: str = "",
) -> RequestResult:
    """发送单个请求并记录结果"""
    start = time.monotonic()
    try:
        if method == "GET":
            resp = await client.get(url, headers=headers, timeout=TIMEOUT)
        else:
            resp = await client.post(url, headers=headers, json=json_body, timeout=TIMEOUT)
        elapsed = (time.monotonic() - start) * 1000
        return RequestResult(endpoint_name, resp.status_code, elapsed)
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        return RequestResult(endpoint_name, 0, elapsed, str(e))


async def _run_concurrent(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict,
    json_body: dict = None,
    total: int = REQUESTS_PER_ENDPOINT,
    concurrency: int = CONCURRENCY,
    endpoint_name: str = "",
) -> list:
    """并发执行 N 个相同请求"""
    sem = asyncio.Semaphore(concurrency)
    results = []

    async def _worker():
        async with sem:
            r = await _send_request(client, method, url, headers, json_body, endpoint_name)
            results.append(r)

    tasks = [asyncio.create_task(_worker()) for _ in range(total)]
    await asyncio.gather(*tasks)
    return results


# ============== 压测用 fixture ==============

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def load_test_client():
    """创建一个真实的 HTTP 客户端（连接本地服务）"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        # 预先创建一个模板供后续测试使用
        create_resp = await client.post("/api/v1/admin/print-templates", headers=headers, json={
            "code": "load_test_tpl",
            "name": "压测模板",
            "docType": "contract",
            "paper": "A4",
            "schemaJson": {
                "body": [
                    {"type": "title", "text": "压测模板标题", "fontSize": 20, "align": "center"},
                    {"type": "spacer", "height": 6},
                    {"type": "text", "text": "合同编号：{{ contract.code }}", "fontSize": 12},
                    {"type": "text", "text": "合同名称：{{ contract.name }}", "fontSize": 12},
                    {"type": "text", "text": "合同金额：{{ contract.amount }}", "fontSize": 12, "color": "#DC2626"},
                    {"type": "spacer", "height": 4},
                    {"type": "line"},
                    {"type": "spacer", "height": 4},
                    {"type": "text", "text": "打印时间：{{ printTime }}", "fontSize": 10, "color": "#9CA3AF"},
                ]
            },
        })
        assert create_resp.status_code == 200, f"创建压测模板失败: {create_resp.text}"
        template_id = create_resp.json()["data"]["id"]

        # 发布模板
        await client.post("/api/v1/admin/print-templates/publish",
                          headers=headers, json={"id": template_id})

        yield client, headers, template_id

        # 清理：归档后删除
        try:
            await client.post("/api/v1/admin/print-templates/archive",
                              headers=headers, json={"id": template_id})
            await client.post("/api/v1/admin/print-templates/delete",
                              headers=headers, json={"id": template_id})
        except Exception:
            pass


# ============== 压测用例 ==============

class TestLoadPrintEndpoints:
    """UDPE 打印端点 50+ 并发压测"""

    @pytest.mark.asyncio
    async def test_01_list_templates(self, load_test_client):
        """压测：模板列表（GET /admin/print-templates）"""
        client, headers, _ = load_test_client
        stats = EndpointStats("GET /admin/print-templates")
        stats.results = await _run_concurrent(
            client, "GET", "/api/v1/admin/print-templates",
            headers=headers, endpoint_name="list_templates",
        )
        print(f"\n{'='*60}")
        print(stats.report())
        print(f"{'='*60}")
        assert stats.failed == 0, f"模板列表压测有 {stats.failed} 个失败"

    @pytest.mark.asyncio
    async def test_02_preview_html(self, load_test_client):
        """压测：HTML 预览（POST /print/preview）"""
        client, headers, _ = load_test_client
        stats = EndpointStats("POST /print/preview")
        stats.results = await _run_concurrent(
            client, "POST", "/api/v1/print/preview",
            headers=headers,
            json_body={
                "templateCode": "load_test_tpl",
                "data": {
                    "contract": {
                        "code": "HT-2026-0001",
                        "name": "压测合同",
                        "amount": 1000000,
                    }
                },
                "options": {"renderMode": "html"},
            },
            endpoint_name="preview_html",
        )
        print(f"\n{'='*60}")
        print(stats.report())
        print(f"{'='*60}")
        # 允许少量超时失败
        assert stats.success >= stats.total * 0.9, (
            f"HTML 预览成功率过低: {stats.success}/{stats.total}"
        )

    @pytest.mark.asyncio
    async def test_03_export_pdf(self, load_test_client):
        """压测：PDF 导出（POST /print/pdf）"""
        client, headers, _ = load_test_client
        stats = EndpointStats("POST /print/pdf")
        stats.results = await _run_concurrent(
            client, "POST", "/api/v1/print/pdf",
            headers=headers,
            json_body={
                "templateCode": "load_test_tpl",
                "data": {
                    "contract": {
                        "code": "HT-2026-0001",
                        "name": "压测合同",
                        "amount": 1000000,
                    }
                },
                "options": {"renderMode": "weasyprint"},
            },
            endpoint_name="export_pdf",
            total=60,  # PDF 生成较重，减少总请求
            concurrency=30,
        )
        print(f"\n{'='*60}")
        print(stats.report())
        print(f"{'='*60}")
        assert stats.success >= stats.total * 0.8, (
            f"PDF 导出成功率过低: {stats.success}/{stats.total}"
        )

    @pytest.mark.asyncio
    async def test_04_get_template_detail(self, load_test_client):
        """压测：模板详情（GET /admin/print-templates/{id}）"""
        client, headers, template_id = load_test_client
        stats = EndpointStats(f"GET /admin/print-templates/{template_id}")
        stats.results = await _run_concurrent(
            client, "GET", f"/api/v1/admin/print-templates/{template_id}",
            headers=headers, endpoint_name="get_template",
        )
        print(f"\n{'='*60}")
        print(stats.report())
        print(f"{'='*60}")
        assert stats.failed == 0, f"模板详情压测有 {stats.failed} 个失败"

    @pytest.mark.asyncio
    async def test_05_list_logs(self, load_test_client):
        """压测：打印日志（GET /admin/print-logs）"""
        client, headers, _ = load_test_client
        stats = EndpointStats("GET /admin/print-logs")
        stats.results = await _run_concurrent(
            client, "GET", "/api/v1/admin/print-logs",
            headers=headers, endpoint_name="list_logs",
        )
        print(f"\n{'='*60}")
        print(stats.report())
        print(f"{'='*60}")
        assert stats.failed == 0, f"打印日志压测有 {stats.failed} 个失败"

    @pytest.mark.asyncio
    async def test_06_mixed_concurrent(self, load_test_client):
        """压测：混合端点并发（模拟真实场景）"""
        client, headers, template_id = load_test_client
        all_results = []

        # 同时发起不同端点的请求
        tasks = [
            _run_concurrent(client, "GET", "/api/v1/admin/print-templates",
                            headers=headers, total=30, concurrency=30,
                            endpoint_name="list_templates"),
            _run_concurrent(client, "GET", f"/api/v1/admin/print-templates/{template_id}",
                            headers=headers, total=30, concurrency=30,
                            endpoint_name="get_template"),
            _run_concurrent(client, "POST", "/api/v1/print/preview",
                            headers=headers, total=30, concurrency=20,
                            json_body={
                                "templateCode": "load_test_tpl",
                                "data": {"contract": {"code": "X", "name": "Y", "amount": 100}},
                                "options": {"renderMode": "html"},
                            },
                            endpoint_name="preview_html"),
            _run_concurrent(client, "GET", "/api/v1/admin/print-logs",
                            headers=headers, total=30, concurrency=30,
                            endpoint_name="list_logs"),
        ]

        nested = await asyncio.gather(*tasks)
        for batch in nested:
            all_results.extend(batch)

        total = len(all_results)
        success = sum(1 for r in all_results if 200 <= r.status < 400)
        failed = total - success

        print(f"\n{'='*60}")
        print(f"  混合并发压测:")
        print(f"    total={total}  success={success}  failed={failed}")
        # 按端点分组
        by_endpoint = {}
        for r in all_results:
            by_endpoint.setdefault(r.endpoint, []).append(r)
        for ep, rs in by_endpoint.items():
            s = EndpointStats(ep)
            s.results = rs
            print(s.report())
        print(f"{'='*60}")

        assert success >= total * 0.9, (
            f"混合并发成功率过低: {success}/{total}"
        )


# ============== 独立运行入口 ==============

if __name__ == "__main__":
    """直接运行（不通过 pytest）"""
    import sys

    async def main():
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
            token = await _login(client)
            headers = {"Authorization": f"Bearer {token}"}

            print(f"\nUDPE 打印引擎压测")
            print(f"目标: {BASE_URL}")
            print(f"并发: {CONCURRENCY}  每端点请求数: {REQUESTS_PER_ENDPOINT}")
            print(f"{'='*60}")

            # 模板列表
            stats = EndpointStats("GET /admin/print-templates")
            stats.results = await _run_concurrent(
                client, "GET", "/api/v1/admin/print-templates",
                headers=headers, endpoint_name="list_templates",
            )
            print(stats.report())

            # 模板详情
            stats = EndpointStats("GET /admin/print-templates/1")
            stats.results = await _run_concurrent(
                client, "GET", "/api/v1/admin/print-templates/1",
                headers=headers, endpoint_name="get_template",
            )
            print(stats.report())

            print(f"\n{'='*60}")
            print("压测完成")

    asyncio.run(main())
