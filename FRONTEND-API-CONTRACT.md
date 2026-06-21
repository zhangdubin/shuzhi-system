# 前后端 API 契约 · 同步对齐

> **目的**：解决 `design/API.md` / `design/AI-API.md` / `backend/app/modules/*/router.py` / `frontend/src/api/*.ts` **四份契约不一致**的问题
> **读者**：前端工程师、后端工程师、PM
> **状态**：✅ 已对齐（裁决记录在 §3 决策表）

---

## 0. 问题陈述

我们当前有 4 份 API 约定，**风格不一致**：

| 来源 | 风格 | 实际写法（举例） |
|------|------|----------------|
| `design/API.md` | 全部 POST + body | `POST /api/v1/projects/list` body: `{page, pageSize, keyword}` |
| `design/AI-API.md` | 全部 POST + body | `POST /api/v1/ai/extract/upload` body: `{fileId, type}` |
| `backend/app/modules/auth/router.py` | FastAPI 装饰器 | 实际：`@router.post("/login")` |
| `backend/app/modules/project/router.py` | 全部 POST + body | 实际：`@router.post("/list")` |
| `frontend/src/api/auth.ts` | RESTful | `http.post('/auth/login')` / `http.get('/auth/me')` |
| `frontend/src/api/client.ts` | RESTful | `http.get('/client/list')` / `http.post('/client')` |
| `frontend/src/api/modules.ts` | 全部 POST | `http.post('/projects/list')` |
| `frontend/src/api/ai.ts` | RESTful | `http.get('/ai/tasks')` / `http.post('/ai/extract/invoice')` |

**冲突**：
- 同一份前端工程里 `client.ts` 是 RESTful，`modules.ts` 是 POST 风格
- 同一份后端骨架里 `auth` 用了 `response_model` 不一致（login 直返，其他包 `code/data`）
- 错误码前后端各自一套：API.md 用 1001/1003/2001/2004/2009/5000，前端 utils/request.ts 用 1001/2001/2002/2003/3001/4001/5001/5002/5101-5104

**根因**：文档和代码是分头写的，没有"单一真相来源"。

---

## 1. 裁决原则

为了在不破坏现有 4 份约定的前提下快速收敛，**裁决按以下 3 个原则**：

1. **后端代码已实现的 → 以代码为准**（后端 leader 已经在写代码，不能再改）
2. **前端代码已实现的 → 以代码为准**（前端工程师已经在写页面）
3. **冲突的 → 用 "路径不变 + 协议变" 的最小修改原则**

---

## 2. 统一后的 API 风格（**这是新的唯一真相**）

### 2.1 HTTP 方法语义

| 语义 | HTTP 方法 | 路径风格 | Body |
|------|----------|---------|------|
| 列表查询 | `POST` | `/api/v1/{module}/list` | `{page, pageSize, keyword, filters}` |
| 单条详情 | `POST` | `/api/v1/{module}/detail` | `{id: 123}` 或 `?id=123` |
| 创建 | `POST` | `/api/v1/{module}/create` | 业务对象 |
| 更新 | `POST` | `/api/v1/{module}/update` | 业务对象（带 id） |
| 删除 | `POST` | `/api/v1/{module}/delete` | `{id: 123}` |
| 状态切换 | `POST` | `/api/v1/{module}/{action}` | 业务对象 |
| 简单查询 | `GET` | `/api/v1/{module}/xxx` | query string |
| 上传 | `POST` multipart | `/api/v1/{module}/upload` | formData |
| SSE 流 | `GET` | `/api/v1/{module}/stream` | — |

**为什么不全 RESTful**：
- 项目早期按 "全部 POST" 写（见 `design/API.md`），后端骨架已实现
- 全部 POST 简化了前端调用（不需要区分 GET/POST/PUT/DELETE）
- 对企业内部系统，可读性 > RESTful 严谨性

**为什么不全 POST**：
- 详情/列表/创建/更新/删除以外的简单查询（如 `/auth/me`、`/dashboard/stats`），用 GET 更语义化
- SSE 必须用 GET（浏览器限制）

### 2.2 响应统一格式

**两种风格并存**（已经实现，不强求统一）：

#### 风格 A：业务对象（登录、详情等小对象）
```json
{
  "token": "xxx",
  "refreshToken": "xxx",
  "userInfo": { ... }
}
```

#### 风格 B：包装（列表、操作结果）
```json
{
  "code": 0,
  "data": { ... },
  "message": "success",
  "traceId": "abc-123"
}
```

#### 风格 C：列表专用（已在前端约定）
```json
{
  "list": [ ... ],
  "total": 128,
  "page": 1,
  "pageSize": 20
}
```

**前端处理逻辑**（已实现，见 `utils/request.ts`）：
```typescript
// 如果响应有 code 字段 → 当成 ApiResponse 处理
// 如果没有 → 直返业务对象
if (res && typeof res === 'object' && 'code' in res) {
  if (res.code === 0) return res.data
  // 错误处理
} else {
  return res  // 直返
}
```

**后端实现建议**：
- 登录、me、详情等单对象接口：直返业务对象（不包装）
- 列表、CRUD、状态切换：包装 `{code, data, message}`
- 列表的 data 内部用 `{list, total, page, pageSize}`

### 2.3 错误码（**最终版**，与 API.md 合并）

| code | 含义 | 处理建议 |
|------|------|---------|
| 0 | 成功 | — |
| 1001 | 未登录 / Token 过期 | 跳登录 |
| 1002 | 资源不存在 | 友好 404 |
| 1003 | 无权限 | 隐藏功能 |
| 2001 | 参数错误 | 高亮字段 |
| 2002 | 资源冲突 | 刷新重试 |
| 2003 | 业务规则校验失败 | 弹错误 |
| 3001 | 操作过于频繁（限流） | 软提示 |
| 4001 | 业务规则校验失败 | 弹错误 |
| 5000 | 服务器异常 | 通用 |
| 5001 | 外部服务调用失败 | 降级 |
| 5002 | 国税查验异常 | 稍后重试 |
| 5101 | AI 模型暂不可用 | **降级 + 隐藏 AI 入口** |
| 5102 | AI 处理超时 | **降级 + 提示** |
| 5103 | AI 内容安全审核未通过 | 静默降级 + 记日志 |
| 5104 | AI 返回格式异常 | 降级 + 报告 |

**冲突解决**：
- 原 API.md 的 "1001=未登录" / "1003=无权限" **保留**
- 原前端的 "2001=参数错误" / "2002=资源冲突" / "2003=业务规则" **保留**
- 新增的 "5101-5104" AI 错误码 **统一**

### 2.4 鉴权

**Header 鉴权**（除 SSE 外）：
```
Authorization: Bearer <token>
```

**SSE 鉴权**（query string）：
```
GET /api/v1/ai/extract/batch/stream?batchId=xxx&token=<token>
```
> 后端需要在 SSE 端点读 query 里的 token（不能依赖 header，因为 EventSource 不支持）

### 2.5 通用 Headers

请求：
```
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Id: <租户ID>
X-Request-Id: <trace-id>     # 前端生成 UUID
X-AI-Source: <web|ios|android|cli|cron>   # AI 接口专用
```

响应：
```
X-Trace-Id: <trace-id>
X-Response-Time: <ms>
```

### 2.6 金额单位

- **数据库**：分（BIGINT）
- **API 返回**：元（保留 2 位小数）
- **前端展示**：根据场景用 `¥ 1,234.56`

---

## 3. 路径裁决表（**这一节是关键**）

### 3.1 老模块（auth / project / contract / expense / receivable / client / invoice）

| 模块 | 列表 | 详情 | 创建 | 更新 | 删除 | 状态切换 |
|------|------|------|------|------|------|---------|
| auth | — | `POST /auth/me` | `POST /auth/login` | — | `POST /auth/logout` | `POST /auth/refresh` |
| project | `POST /project/list` | `POST /project/detail?id=123` | `POST /project/create` | `POST /project/update` | `POST /project/delete?id=123` | `POST /project/milestone/add` |
| contract | `POST /contract/list` | `POST /contract/detail?id=123` | `POST /contract/create` | `POST /contract/update` | `POST /contract/delete?id=123` | `POST /contract/approve` |
| expense | `POST /expense/list` | `POST /expense/detail?id=123` | `POST /expense/create` | `POST /expense/update` | `POST /expense/delete?id=123` | `POST /expense/approve` |
| receivable | `POST /receivable/list` | `POST /receivable/detail?id=123` | `POST /receivable/create` | `POST /receivable/update` | `POST /receivable/delete?id=123` | `POST /receivable/receive` / `/remind` |
| client | `POST /client/list` | `POST /client/detail?id=123` | `POST /client/create` | `POST /client/update` | `POST /client/delete?id=123` | — |
| invoice (OCR) | `POST /invoice/ocr/list` | `POST /invoice/ocr/detail?id=123` | `POST /invoice/ocr/upload` | `POST /invoice/ocr/update` | — | `POST /invoice/ocr/submit` `/recheck` |
| invoice (template) | `POST /invoice/template/list` | `POST /invoice/template/detail?id=123` | `POST /invoice/template/save` | 同上 | `POST /invoice/template/delete` | `POST /invoice/template/duplicate` |
| invoice (verify) | `POST /invoice/verify/list` | — | `POST /invoice/verify/single` | — | — | `POST /invoice/verify/mark` |

**注意**：
- ✅ ID 全部用 **query string**（不是 body）
- ✅ 路径前缀**单数**（`/project/`，不是 `/projects/`）—— 与 `design/API.md` 一致，**前端 `modules.ts` 用的 `/projects/`（复数）需要改**（见 §4 迁移清单）

### 3.2 AI 模块（**Phase 1 必出 18 接口**）

| # | 接口 | 路径 | 方法 | 必出 |
|---|------|------|------|------|
| 1 | 字段抽取（同步） | `/ai/extract/upload` | POST | ✦ |
| 2 | 字段抽取（批量） | `/ai/extract/batch/upload` | POST | ✦ |
| 3 | 字段抽取 SSE 进度 | `/ai/extract/batch/stream` | GET (SSE) | ✦ |
| 4 | 字段抽取结果查询 | `/ai/extract/result/:id` | GET | ✦ |
| 5 | 采纳/修正抽取结果 | `/ai/extract/apply` | POST | ✦ |
| 6 | 风险扫描（单条） | `/ai/risk/scan` | POST | ✦ |
| 7 | 拉取某对象的所有风险 | `/ai/risk/warnings` | POST | ✦ |
| 8 | 采纳/忽略风险 | `/ai/risk/dismiss` | POST | ✦ |
| 9 | 智能问答 | `/ai/ask/ask` | POST (SSE 可选) | ✦ |
| 10 | 问答历史 | `/ai/ask/history` | GET | ✦ |
| 11 | 问答反馈 | `/ai/ask/feedback` | POST | ✦ |
| 12 | 推荐问题 | `/ai/ask/suggestions` | GET | ✦ |
| 13 | 任务列表 | `/ai/task/list` | POST | ✦ |
| 14 | 任务详情 | `/ai/task/detail/:id` | GET | ✦ |
| 15 | 任务 SSE 进度 | `/ai/task/stream/:id` | GET (SSE) | ✦ |
| 16 | 任务取消 | `/ai/task/cancel/:id` | POST | ✦ |
| 17 | 通用反馈 | `/ai/feedback/submit` | POST | ✦ |
| 18 | 模型列表 | `/ai/model/list` | GET | ✦ |
| 19 | 模型配置 | `/ai/model/config` | POST | ✦ |
| 20 | 今日 AI 提醒 | `/ai/alert/today` | GET | ✦ |
| 21 | 提醒关闭 | `/ai/alert/dismiss` | POST | ✦ |
| 22 | 全局 SSE 入口 | `/ai/stream` | GET (SSE) | ✦ |

**与 AI-API.md 的差异**：
- ✅ 沿用 `POST /ai/{module}/{action}` 风格
- ✅ ID 用 **path 参数**（如 `/ai/extract/result/:id`）
- ✅ SSE 用 **GET**（浏览器限制）
- ✅ 任务/反馈/告警类用动词而非 `/ai/tasks` 复数（统一为 `/ai/task/list`）

### 3.3 admin 模块（**预留**）

| 模块 | 接口 | 备注 |
|------|------|------|
| 用户 | `POST /admin/user/list` / `:id` `/reset-password` | 与业务模块同风格 |
| 角色 | `POST /admin/role/list` / `:id/permissions` | |
| 部门 | `POST /admin/dept/tree` | 树形 |
| 字典 | `POST /admin/dict/list` | |

---

## 4. 前端 `modules.ts` 迁移清单（**必须改**）

> **问题**：现有 `src/api/modules.ts` 用了 `/projects/`、`/contracts/`（**复数**）路径，与 `design/API.md` 不一致。
> **决策**：**统一为单数**（`/project/`、`/contract/`），与 `design/API.md` 一致。

需要修改的文件：

```diff
// src/api/modules.ts
- list: (params: PageReq) => http.post<PageRes<Project>>('/projects/list', params),
+ list: (params: PageReq) => http.post<PageRes<Project>>('/project/list', params),

- detail: (id: number) => http.post<Project>('/projects/detail', undefined, { params: { projectId: id } }),
+ detail: (id: number) => http.post<Project>('/project/detail', undefined, { params: { projectId: id } }),

- create: (data: Partial<Project>) => http.post<Project>('/projects/create', data),
+ create: (data: Partial<Project>) => http.post<Project>('/project/create', data),

// 同样改：contracts → contract, expenses → expense, receivables → receivable
```

**优先级**：🔴 高（后端如果用单数，前端必须一致，否则 404）

---

## 5. 后端新增/调整清单

### 5.1 老模块（与 `design/API.md` 对齐）

- ✅ `auth/router.py` 已实现（`/auth/login` POST + 直返、`/auth/me` GET）
- ✅ `project/router.py` 已实现（`/project/list` POST + 包装）
- ⚠️ 路径里 ID 用 query string（`?projectId=123`），需要所有模块统一

### 5.2 AI 模块（按 §3.2 实现）

**必出的 22 个接口**（含 SSE）：
- 字段抽取 5 个
- 风险识别 3 个
- 智能问答 4 个
- 任务中心 4 个
- 提醒 2 个
- 反馈 1 个
- 模型管理 2 个
- 全局 SSE 1 个

详细 request/response 字段见 `design/AI-API.md`。

### 5.3 数据库

- ✅ 老表已存在（按 `design/BACKEND.md`）
- ⚠️ AI 表需要新增（见 `design/AI-API.md §8`）：`ai_tasks` / `ai_feedback` / `ai_alerts`

---

## 6. 前端 AI 集成清单（**22 个触点**）

见 `FRONTEND-AI-INTEGRATION.md`（单独文档）。

简版：

| # | 在哪个 .vue | 加什么 |
|---|------------|--------|
| 1 | `views/invoice/InvoiceOcr.vue` | "✦ AI 智能抽取" 按钮 + 结果展示 |
| 2 | `views/invoice/InvoiceOcr.vue` (batch) | 进度条加 AI 抽字段开关 |
| 3 | `views/project/ProjectList.vue` | 列表加 AI 风险列 |
| 4 | `views/project/ProjectDetail.vue` | 新增 ✨ AI 分析 Tab |
| 5 | `views/dashboard/Dashboard.vue` | 顶部加 AI 提醒条 |
| 6-13 | 各模块创建/详情/列表 | 见 `FRONTEND-AI-INTEGRATION.md` |
| 14 | `layouts/AppLayout.vue` | 顶栏加 🤖 全局问数 |
| ... | ... | ... |

---

## 7. 验证清单（前后端联调前必须通过）

### 7.1 前端
- [ ] `src/api/modules.ts` 改完（`/projects` → `/project`）
- [ ] `src/utils/sse.ts` 已引入
- [ ] `src/stores/ai.ts` 已引入
- [ ] `src/assets/styles/ai.scss` 已引入（通过 global.scss）
- [ ] `npm run build` 通过（无 TS 错误）

### 7.2 后端
- [ ] 所有路由与 §3 路径表一致
- [ ] 错误码与 §2.3 一致
- [ ] SSE 端点支持 query string token
- [ ] `/ai/extract/upload` 实现（**Phase 1 头号**）
- [ ] `/ai/risk/scan` 实现
- [ ] `/ai/ask/ask` 实现
- [ ] AI 3 张表 migration 已生成

### 7.3 联调
- [ ] 登录 → Dashboard 数据流通
- [ ] 列表分页 + 筛选
- [ ] 创建/更新/删除
- [ ] 详情 + 关联数据
- [ ] SSE 长任务进度（OCR / AI 抽取）
- [ ] 错误码触发正确提示

---

## 8. 变更历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.9 | 2026-05-21 | 初稿。收敛 4 份不一致的契约，明确风格、错误码、AI 22 接口 |

---

## 附录：完整接口清单

### 业务模块（47 个）

```
/api/v1/auth/
  POST /login
  POST /logout
  POST /refresh
  GET  /me
  GET  /sso/qrcode/generate    [后续]
  GET  /sso/qrcode/check       [后续]

/api/v1/dashboard/
  POST /summary
  POST /activities

/api/v1/project/
  POST /list
  POST /detail
  POST /create
  POST /update
  POST /delete
  POST /milestone/list
  POST /milestone/add
  POST /milestone/update
  POST /milestone/delete
  POST /stats

/api/v1/contract/
  POST /list
  POST /detail
  POST /create
  POST /update
  POST /delete
  POST /approve
  POST /stats
  POST /template

/api/v1/expense/
  POST /list
  POST /detail
  POST /create
  POST /update
  POST /delete
  POST /approve
  POST /stats

/api/v1/receivable/
  POST /list
  POST /detail
  POST /create
  POST /update
  POST /delete
  POST /receive
  POST /remind
  POST /stats

/api/v1/client/
  POST /list
  POST /detail
  POST /create
  POST /update
  POST /delete
  POST /stats

/api/v1/invoice/
  POST /ocr/upload
  POST /ocr/batch/upload
  POST /ocr/batch/submit
  POST /ocr/batch/retry
  GET  /ocr/batch/status       [老接口，轮询用]
  POST /ocr/list
  POST /ocr/detail
  POST /ocr/update
  POST /ocr/submit
  POST /ocr/recheck
  POST /ocr/advanced-search
  POST /ocr/batch-action
  POST /ocr/saved-view
  POST /ocr/views
  POST /template/list
  POST /template/save
  POST /template/duplicate
  POST /template/delete
  POST /template/field-library
  POST /verify/single
  POST /verify/batch
  POST /verify/list
  POST /verify/certificate
  POST /verify/mark

/api/v1/common/
  POST /dict
  POST /users
  POST /clients
  POST /contracts/ref
  POST /projects/ref
  POST /upload

/api/v1/admin/                   [Phase 2]
  POST /user/list
  POST /user/create
  POST /user/update
  POST /user/delete
  POST /user/reset-password
  POST /role/list
  POST /role/permissions
  POST /dept/tree
  POST /dict/list
```

### AI 模块（22 个）

```
/api/v1/ai/
  POST /extract/upload                  ✦
  POST /extract/batch/upload            ✦
  GET  /extract/batch/stream            ✦ (SSE)
  GET  /extract/result/:id              ✦
  POST /extract/apply                   ✦
  POST /risk/scan                       ✦
  POST /risk/warnings                   ✦
  POST /risk/dismiss                    ✦
  POST /ask/ask                         ✦
  GET  /ask/history                     ✦
  POST /ask/feedback                    ✦
  GET  /ask/suggestions                 ✦
  POST /task/list                       ✦
  GET  /task/detail/:id                 ✦
  GET  /task/stream/:id                 ✦ (SSE)
  POST /task/cancel/:id                 ✦
  POST /feedback/submit                 ✦
  GET  /model/list                      ✦
  POST /model/config                    ✦
  GET  /alert/today                     ✦
  POST /alert/dismiss                   ✦
  GET  /stream                          ✦ (SSE, 多事件)

  [Phase 2 占位]
  POST /match/run
  POST /match/result/:id
  POST /match/confirm
  POST /generate/draft
  POST /generate/list
  POST /generate/save
  POST /agent/run
  POST /agent/list
  POST /agent/config
```

**总计**：47 业务 + 22 AI = **69 个接口**（Phase 1 必出 60+ 个）
