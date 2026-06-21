# 压测报告 - AI+业务接口混合（10 RPS）

**生成时间**：2026-06-15 09:21:49
**原始数据**：`scenario-3-summary.json`
**k6 状态**：✅ 通过

## 1. 总体指标

| 指标 | 值 |
|---|---|
| HTTP 总请求数 | 601 |
| VU 迭代次数 | 600 |
| 错误率 | 0.00% |
| 平均响应时间 | 15.4 ms |
| P50 | - ms |
| P90 | 22.3 ms |
| P95 | 23.3 ms |
| P99 | - ms |
| 最大响应时间 | 262.9 ms |

## 2. 阈值检查

_无阈值配置_

## 3. 自定义指标

| 指标 | 平均 | P95 | 最大 |
|---|---|---|---|
| `http_req_blocked` | 0.0 ms | 0.0 ms | 0.7 ms |
| `iteration_duration` | 15.5 ms | 23.8 ms | 80.7 ms |
| `http_req_duration{expected_response:true}` | 20.1 ms | 23.8 ms | 262.9 ms |
| `http_req_connecting` | 0.0 ms | 0.0 ms | 0.6 ms |
| `http_req_sending` | 0.1 ms | 0.1 ms | 0.2 ms |
| `http_req_waiting` | 15.2 ms | 23.2 ms | 262.8 ms |
| `ai_duration` | 14.9 ms | 23.3 ms | 80.4 ms |
| `http_req_tls_handshaking` | 0.0 ms | 0.0 ms | 0.0 ms |
| `http_req_receiving` | 0.1 ms | 0.2 ms | 0.5 ms |
| `http_req_duration{scenario:ai_mixed}` | 14.9 ms | 23.3 ms | 80.4 ms |

## 4. Check 结果

| 检查项 | 通过/总次数 | 成功率 |
|---|---|---|
| /api/v1/expenses/list < 500 | 62/62 | 100.0% |
| /api/v1/ai/model/list < 500 | 54/54 | 100.0% |
| /api/v1/auth/me < 500 | 52/52 | 100.0% |
| /api/v1/contracts/list < 500 | 58/58 | 100.0% |
| /api/v1/ai/alerts/list < 500 | 66/66 | 100.0% |
| /api/v1/projects/list < 500 | 57/57 | 100.0% |
| /api/v1/receivables/list < 500 | 50/50 | 100.0% |
| /api/v1/ai/tasks/list < 500 | 75/75 | 100.0% |
| /api/v1/ai/risk/list < 500 | 59/59 | 100.0% |
| /api/v1/dashboard/summary < 500 | 67/67 | 100.0% |

---

_本报告由 `perf/scripts/gen_report.py` 自动生成_
