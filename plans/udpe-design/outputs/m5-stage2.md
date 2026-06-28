# M5 阶段 2 — 渲染性能优化

> **状态**: ✅ 已完成
> **日期**: 2026-06-28

## 一、产出

✅ 并发渲染信号量 (限制同时渲染数为 3, 防止 db 连接池耗尽)
✅ 模板缓存预热端点 (POST /admin/print-templates/cache/warmup)
✅ 前端 warmupCache API 方法

## 二、文件改动

| 文件 | 改动 |
|------|------|
| `backend/app/modules/print_runtime/service.py` | +asyncio.Semaphore(3) |
| `backend/app/modules/print_runtime/router.py` | +cache warmup 端点 |
| `frontend/src/api/print.ts` | +warmupCache 方法 |

## 三、性能优化

1. **并发渲染限制**: `asyncio.Semaphore(3)` 确保同时最多 3 个渲染任务, 防止 db 连接池耗尽和内存暴涨
2. **缓存预热**: 一键加载所有 active 模板到 Redis, 避免首次请求冷启动
3. **已有缓存**: 模板列表/详情已有 Redis 缓存 (TTL 1h), 写操作自动失效
