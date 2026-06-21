# 压测报告 - 业务核心5接口混合（20 RPS稳态）

**生成时间**：2026-06-15 09:21:49
**原始数据**：`scenario-2-summary.json`
**k6 状态**：✅ 通过

## 1. 总体指标

| 指标 | 值 |
|---|---|
| HTTP 总请求数 | 1441 |
| VU 迭代次数 | 1201 |
| 错误率 | 0.00% |
| 平均响应时间 | 11.3 ms |
| P50 | - ms |
| P90 | 13.2 ms |
| P95 | 14.1 ms |
| P99 | - ms |
| 最大响应时间 | 267.8 ms |

## 2. 阈值检查

_无阈值配置_

## 3. 自定义指标

| 指标 | 平均 | P95 | 最大 |
|---|---|---|---|
| `http_req_sending` | 0.0 ms | 0.0 ms | 1.1 ms |
| `http_req_connecting` | 0.0 ms | 0.0 ms | 0.3 ms |
| `iteration_duration` | 13.6 ms | 20.4 ms | 74.8 ms |
| `http_req_tls_handshaking` | 0.0 ms | 0.0 ms | 0.0 ms |
| `http_req_duration{scenario:business_core}` | 11.1 ms | 14.1 ms | 74.5 ms |
| `http_req_waiting` | 11.2 ms | 14.0 ms | 267.6 ms |
| `list_duration` | 11.8 ms | 14.4 ms | 74.5 ms |
| `http_req_duration{expected_response:true}` | 11.3 ms | 14.1 ms | 267.8 ms |
| `detail_duration` | 8.8 ms | 11.0 ms | 18.4 ms |
| `http_req_blocked` | 0.0 ms | 0.0 ms | 0.8 ms |
| `http_req_receiving` | 0.1 ms | 0.1 ms | 1.0 ms |

## 4. Check 结果

| 检查项 | 通过/总次数 | 成功率 |
|---|---|---|
| projects/list 200 | 234/234 | 100.0% |
| expenses/list 200 | 260/260 | 100.0% |
| contracts/list 200 | 235/235 | 100.0% |
| receivables/detail 200 | 61/61 | 100.0% |
| receivables/list 200 | 233/233 | 100.0% |
| projects/detail 200 | 56/56 | 100.0% |
| contracts/detail 200 | 67/67 | 100.0% |
| expenses/detail 200 | 55/55 | 100.0% |

---

_本报告由 `perf/scripts/gen_report.py` 自动生成_
