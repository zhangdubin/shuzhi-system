# 压测报告 - 登录+Dashboard阶梯（5→50 RPS）

**生成时间**：2026-06-15 09:21:49
**原始数据**：`scenario-1-summary.json`
**k6 状态**：✅ 通过

## 1. 总体指标

| 指标 | 值 |
|---|---|
| HTTP 总请求数 | 2145 |
| VU 迭代次数 | 715 |
| 错误率 | 0.00% |
| 平均响应时间 | 838.1 ms |
| P50 | - ms |
| P90 | 2886.0 ms |
| P95 | 4102.1 ms |
| P99 | - ms |
| 最大响应时间 | 20484.9 ms |

## 2. 阈值检查

_无阈值配置_

## 3. 自定义指标

| 指标 | 平均 | P95 | 最大 |
|---|---|---|---|
| `login_duration` | 2385.0 ms | 6592.2 ms | 20484.9 ms |
| `dashboard_duration` | 73.5 ms | 418.0 ms | 1686.7 ms |
| `http_req_duration{expected_response:true}` | 838.1 ms | 4102.1 ms | 20484.9 ms |
| `http_req_tls_handshaking` | 0.0 ms | 0.0 ms | 0.0 ms |
| `iteration_duration` | 2514.8 ms | 6641.6 ms | 20510.6 ms |
| `http_req_receiving` | 1.9 ms | 1.1 ms | 612.0 ms |
| `http_req_sending` | 0.0 ms | 0.0 ms | 0.1 ms |
| `http_req_duration{scenario:login_dashboard}` | 838.1 ms | 4102.1 ms | 20484.9 ms |
| `http_req_waiting` | 836.2 ms | 4101.2 ms | 20484.8 ms |
| `http_req_blocked` | 0.0 ms | 0.0 ms | 0.4 ms |
| `http_req_connecting` | 0.0 ms | 0.0 ms | 0.3 ms |

## 4. Check 结果

| 检查项 | 通过/总次数 | 成功率 |
|---|---|---|
| login status 200 | 715/715 | 100.0% |
| login has token | 715/715 | 100.0% |
| dashboard status 200 | 715/715 | 100.0% |
| dashboard code 0 | 715/715 | 100.0% |
| activities status 200 | 715/715 | 100.0% |

---

_本报告由 `perf/scripts/gen_report.py` 自动生成_
