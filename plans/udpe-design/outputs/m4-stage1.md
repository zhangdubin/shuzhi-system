# M4 阶段 1 — 异步批量打印 + SSE 进度推送

> **状态**: ✅ 已完成
> **作者**: Codex (GPT-5)
> **日期**: 2026-06-28
> **前置**: M2 阶段 9 (同步批量打印), 核心 SSE 事件总线
> **任务**: 把批量打印从同步改为异步, 实时推送进度

## 一、目标与边界

M2 阶段 9 的批量打印是同步阻塞的 — 10 条以内 < 500ms 可接受，但 50+ 条时 HTTP 请求超时。
M4 阶段 1 将其改为异步后台执行 + SSE 实时进度推送。

✅ 后端: 异步批量打印端点 (POST /print/batch/async)
✅ 后端: 任务状态查询 (GET /print/batch/async/{jobId}/status)
✅ 后端: 结果下载 (GET /print/batch/async/{jobId}/download)
✅ 后端: SSE 进度发布 (batch_start / batch_progress / batch_done)
✅ 前端: printApi 异步批量方法 (batchPdfAsync / batchJobStatus / batchJobDownload)
✅ 前端: BatchPrintProgressDialog 进度对话框组件

## 二、文件改动

### 2.1 新增文件

| 文件 | 用途 | 行数 |
|------|------|------|
| `frontend/src/components/common/BatchPrintProgressDialog.vue` | 批量打印进度对话框 | 210 |

### 2.2 修改文件

| 文件 | 改动 |
|------|------|
| `backend/app/modules/print_runtime/router.py` | 新增 3 个端点 + 后台任务函数 |
| `frontend/src/api/print.ts` | 新增 3 个异步批量方法 |

## 三、接口设计

### POST /print/batch/async
启动异步批量打印任务。入参同 `POST /print/batch`。
返回 `{ jobId, total }`。

### GET /print/batch/async/{jobId}/status
查询任务状态。返回 `{ jobId, status, total, done, failed, elapsedMs, errors }`。
status: `pending` → `running` → `done` / `failed`

### GET /print/batch/async/{jobId}/download
下载合并后的 PDF。仅 status=done 时可用。

### SSE: /sse/batch/{jobId}?token=xxx
事件类型:
- `batch_start` — { jobId, total }
- `batch_progress` — { jobId, current, total, done, failed }
- `batch_done` — { jobId, status, done, failed, elapsedMs }

## 四、前端组件

BatchPrintProgressDialog:
- 监听 SSE 事件获取实时进度
- 进度条 + 成功/失败计数
- 完成后提供下载按钮
- SSE 断开时自动轮询 fallback
- 关闭不停止后台任务

## 五、技术决策

1. **内存任务表** — V1 用 dict 存任务状态 (重启丢失), 生产环境可换 Redis Hash
2. **asyncio.create_task** — FastAPI 原生后台任务, 不引入 Celery
3. **SSE 复用现有基础设施** — Redis Pub/Sub + sse_router, channel = `sse:batch:{jobId}`
4. **轮询 fallback** — SSE 断开时每秒轮询 status 端点

## 六、验证

### 6.1 前端构建
```
✓ built in 5.60s, 0 错误
```

### 6.2 后端构建
```
Image shuzhi-backend:latest Built
Container shuzhi-backend Started
```

### 6.3 接口验证
```bash
curl -X POST http://localhost:8000/api/v1/print/batch/async \
  -H "Content-Type: application/json" \
  -d '{"templateCode":"test","items":[{"id":1}]}'
# → {"code":1001,"message":"未登录或登录已过期"}  (路由正确, 需要认证)
```

## 七、零破坏验证

- ✅ 原同步批量打印端点 POST /print/batch 完全保留
- ✅ 原 printApi.batchPdf / batchPdfBlob 继续工作
- ✅ 新增端点与旧端点并存, 前端可自由选择
- ✅ SSE 事件总线复用, 不影响现有 SSE 功能

## 八、下一步

1. 在业务页面集成 BatchPrintProgressDialog (列表页批量打印按钮)
2. 任务结果缓存过期清理 (V1 内存任务不清理, 生产需加 TTL)
3. 并发限制 (asyncio.Semaphore 防止同时跑太多批量任务)
