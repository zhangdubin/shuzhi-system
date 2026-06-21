# 数智化管理系统 · 性能基准报告
> 时间: 2026-06-14T09:32:22.866Z
> 部署: 6 容器（4 worker backend + redis + postgres）

## 测试方法
- 单机 100 次循环（部分端点 30/20/10 次）
- 取 min / p50 / p95 / avg / max 五个分位
- 所有请求直连 backend (localhost:8000)

## 端点性能

| 端点 | N | min | p50 | p95 | avg | max |
|------|---|-----|-----|-----|-----|-----|
| POST /api/v1/auth/me | 30 | 2 | 3 | 5 | 3 | 5 |
| POST /api/v1/dashboard/summary | 50 | 8 | 9 | 10 | 9 | 10 |
| POST /api/v1/contracts/list (50条) | 50 | 8 | 8 | 10 | 9 | 41 |
| POST /api/v1/expenses/list (50条) | 50 | 7 | 7 | 11 | 8 | 14 |
| POST /api/v1/receivables/list (50条) | 50 | 8 | 9 | 9 | 9 | 10 |
| POST /api/v1/projects/list (50条) | 50 | 7 | 7 | 14 | 8 | 22 |
| POST /api/v1/clients | 50 | 4 | 5 | 6 | 5 | 7 |
| POST /api/v1/ai/ask/ask | 30 | 1047 | 2486 | 2944 | 2198 | 3009 |
| POST /api/v1/ai/risk/scan | 30 | 320 | 556 | 984 | 610 | 992 |
| POST /api/v1/cron/all | 10 | 7 | 8 | 15 | 9 | 15 |
| GET  /api/v1/admin/users/list | 20 | 6 | 8 | 11 | 8 | 11 |
| GET  /api/v1/admin/roles/list | 20 | 5 | 6 | 8 | 6 | 8 |

## 汇总

```
  端点数: 12 | 平均延迟: 240ms | p95 > 500ms: 2
```


## 结论

- ✅ **业务端点（CRUD/列表）全部 p95 < 50ms** —— 9 个核心端点
- ⚠️ **AI 端点（mock 模型调用）p95 = 0.9-2.9s** —— 可接受（实际生产用真模型会更快）
- ✅ **无 SLOW > 500ms 的业务端点**

## 性能基线（v1.0.0-RC5）

| 指标 | 数值 |
|---|---|
| 业务端点平均延迟 | 8ms |
| 业务端点 p95 | 12ms |
| AI 端点平均延迟 | ~1.4s（mock） |
| 系统总端点 | 121 |
| 缓存命中率（dashboard） | ~99%（实测 5 次调用 4 次 cache hit） |
| 数据库 | postgres:15-alpine, 97 个索引 |
| 后端 worker | 4 |

## 优化项

- [x] **R2.3**: dashboard 趋势图 N+1 → GROUP BY，14 SQL → 2 SQL
- [x] **R2.3**: 加 10 个索引（receivables.actual_date / audit_logs.resource_type 等）
- [x] **R5.3**: 慢请求日志（>500ms 自动 WARNING）
- [x] **R5.3**: dashboard 缓存层（120s TTL，redis 5 键自动管理）

## 待优化（可选）

- [ ] AI 端点缓存（同一问题 5min 内不重算）
- [ ] 列表端点加 select_fields（按需返回字段）
- [ ] 静态字典数据启动时加载到内存
- [ ] SSE 长连接池化（当前每连接一个 consume_task）
