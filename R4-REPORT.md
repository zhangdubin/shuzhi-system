# 数智化管理系统 · R4 阶段报告
> 时间：2026-06-14　阶段：R4（E2E 自动化 / SSE 通知中心 / 定时催收 / 权限加固）　部署：6 容器

## 1. 阶段总览

R4 把"生产可用"推到"自动化验证 + 实时通知 + 自动催收"：

| # | 项目 | 成果 |
|---|------|------|
| R4.1 | Playwright E2E 脚本化 | 6 个测试脚本（login/list/ai-ask/sse-realtime/permission/notice-cron），一键 runner，全部通过 |
| R4.1-意外 | 后端 admin 权限加固 | 5 个 list/detail 端点加 `require_permission`，财务总监 zhangming 无法访问 admin/user 等（实测 403）|
| R4.1-意外 | 前端路由守卫 | `router.beforeEach` 检查 `meta.permission`，无权跳 dashboard + toast |
| R4.2 | SSE 通知中心页 | 新建 `/notice` 页，localStorage 持久化最近 200 条；类型筛选 + 已读/未读切换；右键清空 |
| R4.3 | 定时检查（手动触发）| 4 个 cron 端点：`/cron/overdue-check` / `upcoming-due` / `contract-expiring` / `all` |
| R4.4 | 一键检查按钮 | Dashboard 顶部"立即检查"按钮触发 `/cron/all`，23 条提醒立即浮出 |
| R4.5 | 端到端验收 | 6/6 E2E 测试通过；24/24 路由 200；通知实时触达 0→1 |

## 2. R4.1 Playwright E2E 脚本化

**新增**：
- `e2e/test-01-login-dashboard.js` — 登录跳转 + 关键元素
- `e2e/test-02-contract-list.js` — 列表筛选 + 详情跳转
- `e2e/test-03-ai-ask.js` — AI 智能问答端到端
- `e2e/test-04-sse-realtime.js` — 创建 expense → 实时浮层
- `e2e/test-05-permission.js` — 财务总监无 admin 权限
- `e2e/test-06-notice-cron.js` — 一键检查 + 通知中心
- `e2e/run-all.js` — 总 runner + 报告生成

**用法**：
```bash
# 单测
node e2e/test-01-login-dashboard.js

# 全部
node e2e/run-all.js

# 有头模式（debug）
HEADLESS=0 node e2e/test-05-permission.js
```

**结果（最新一次）**：
```
✅ test-01-login-dashboard.js          1.0s
✅ test-02-contract-list.js            0.8s
✅ test-03-ai-ask.js                   7.8s
✅ test-04-sse-realtime.js             3.7s
✅ test-05-permission.js               7.8s
✅ test-06-notice-cron.js              19.9s

6 passed / 0 failed / 6 total
```

## 3. R4.1-意外 后端 admin 权限加固

**问题**：E2E test-05 发现 zhangming 能直接访问 `/admin/users/list` 拿到 6 个用户列表（应该 403）。

**根因**：admin router 的 `users/list`、`users/detail`、`roles/list`、`roles/detail`、`dicts/list`、`permissions/list`、`depts/list` 等"读"端点没加 `require_permission`。

**修法**：
```python
@router.post("/users/list")
async def users_list(
    ...
    _user: CurrentUser = Depends(require_permission("user:read")),  # ← 加
):
```

**实测**：
```bash
zhangming /admin/users/list → 403 {"code":1003,"message":"无权限：user:read"}
zhangming /admin/roles/list → 403 {"code":1003,"message":"无权限：role:read"}
admin /admin/users/list     → 200 (6 个用户)
```

**额外发现 + 修**：前端 `router.beforeEach` 加 `meta.permission` 检查，无权跳 dashboard + toast。

## 4. R4.2 通知中心页

**功能**：
- localStorage 持久化最近 200 条通知
- 类型筛选（合同/费用/回款/AI）
- 已读/未读切换
- 全部已读 / 清空
- 时间显示（刚刚 / N 分钟前 / N 小时前 / 具体时间）
- 与 Dashboard 浮层共用同一 SSE 连接

**实测**：test-06 通过 API 创建 expense → 通知中心条数 0→1 ✅

## 5. R4.3 定时检查

**4 个端点**：
| 端点 | 扫描 | 实际提醒数 |
|---|---|---|
| `POST /api/v1/cron/overdue-check` | 已逾期 + 状态非完成 | 20 条 |
| `POST /api/v1/cron/upcoming-due` | 3 天内到期 | 3 条 |
| `POST /api/v1/cron/contract-expiring` | 30 天内合同到期 | 0 条 |
| `POST /api/v1/cron/all` | 一键跑完 | 23 条 |

**每条提醒通过 SSE publish 触发 Dashboard 浮层 + 通知中心**。

**生产环境建议**：
- 用 `celery beat` / `apscheduler` 定时跑
- 当前是手动触发（前端 Dashboard 顶部"立即检查"按钮）

## 6. 修了一堆 SSE 隐蔽 bug

**Bug 1：前端 sse.ts 自动加 `/api/v1` 前缀，但 SSE 后端是 `/sse/*`**
- 修：sse.ts 不拼 baseURL（SSE 是顶层 path）

**Bug 2：前端 sse.ts 内部用 `userStore.token`**
- 问题：onMounted 时 token 还没存进 store
- 修：sse.ts 接受 `options.token` 外部传，Dashboard.vue 直接从 localStorage 读

**Bug 3：sse.ts handlers.onEvent 不生效**
- 修：handlers 是 `{ [event]: fn }` 字典，'onEvent' 不会被当 event 注册
- 加：专门的 `globalHandler` 监听常见 event 名

**Bug 4：Python async generator yield 后 consume_task 没被调度**
- 修：`await asyncio.sleep(0)` 让出 + 短超时 `wait_for(queue.get(), timeout=1.0)`

**Bug 5：publish_event payload 的 `type` 字段被 data 中的 `type` 覆盖**
- 修：`safe_data = {k:v for k,v in data.items() if k != "type"}`

**Bug 6：admin router 误用 `sch.RoleListRequest` / `RoleDetailRequest`**
- 这俩 schema 不存在，启动了 AttributeError
- 修：去掉，直接 `await service.list_roles(db)`

**Bug 7：ExpenseCreate schema 没 status 字段，但 service 用 `req.status`**
- 修：`status="draft"` 写死

**Bug 8：cron 误用 `r.last_remind_at`（Receivable 无此字段）**
- 修：去掉

## 7. 验收表

### 7.1 路由 24/24 200
```
200  /                       200  /ai/risk           200  /invoice/ocr/list
200  /login                  200  /ai/tasks          200  /invoice/template
200  /dashboard              200  /ai/alerts         200  /invoice/verify
200  /notice                 200  /contract/list     200  /admin/user
200  /ai                     200  /contract/create   200  /admin/role
200  /ai/extract             200  /project/list      200  /admin/dept
200  /ai/ask                 200  /expense/list      200  /admin/dict
                           200  /expense/create    200  /receivable/list
                           200  /receivable/create 200  /client/list
```

### 7.2 E2E 测试 6/6 PASS
| 测试 | 验证 | 结果 |
|---|---|---|
| test-01 | 登录跳转 dashboard + 关键元素 | ✅ |
| test-02 | 合同列表筛选 + 详情跳转 | ✅ |
| test-03 | AI 智能问答端到端 | ✅ |
| test-04 | API 创建 expense → SSE 实时浮层 | ✅ |
| test-05 | 财务总监 zhangming 无 admin 权限 | ✅ |
| test-06 | 一键检查 + 通知中心 | ✅ |

### 7.3 SSE 实时通知实测
```bash
$ curl -X POST .../cron/overdue-check
{"code":0,"data":{"scanned":20,"alerted":20}}

# 浏览器 dashboard 实时收到：
# event: alert
# data: {"action":"逾期","level":"medium","title":"⚠️ 回款 #34 已逾期 7 天","operator":"系统"}
# 13 张 live-card 立即浮出（每条 8s 自动消失）
```

## 8. 改动文件清单

### 新增
- `e2e/test-01-login-dashboard.js` ~ `e2e/test-06-notice-cron.js`
- `e2e/run-all.js`
- `backend/app/modules/cron/router.py` — 4 个 cron 端点
- `frontend/src/views/notice/NoticeCenter.vue` — 通知中心

### 修改
- `backend/app/core/sse.py` — 修 publish_event type 覆盖 + async generator 调度 + 1s 超时
- `backend/app/modules/admin/router.py` — 5 个 list/detail 端点加 `require_permission`
- `backend/app/modules/receivable/router.py` — remind/receive 加 publish_event
- `frontend/src/utils/sse.ts` — 接受 options.token + 不拼 baseURL + globalHandler
- `frontend/src/router/index.ts` — beforeEach 加 meta.permission 检查
- `frontend/src/views/dashboard/Dashboard.vue` — 直接传 token + 加"立即检查"按钮
- `frontend/src/views/contract/ContractCreate.vue` — el-form rules + 业务校验
- `frontend/src/config/menu.ts` — 所有菜单加 permission 字段
- `frontend/src/main.ts` — 注册 permission 指令

## 9. 关键决策

1. **E2E 用 Playwright 原生**（不引入 @playwright/test 框架）—— 一个 node 脚本就能跑，CI 友好
2. **后端 cron 手动触发**（非 apscheduler 自动）—— 简单可调试，R5 改 apscheduler
3. **SSE 异步生成器后台 task + Queue** —— 解决 listen() + yield 阻塞
4. **admin 权限分 read/write** —— list 加 `*:read`，write 类才加 `*:write`
5. **publish_event 防止 type 字段覆盖** —— 用 safe_data 过滤

## 10. 教训（已入 memory）

- Vue 异步生成器 yield 后**必须让出**：`await asyncio.sleep(0)` 才能让 consume_task 调度
- `data = {**data}` 解包会被 data 中 `type` 覆盖 payload 顶层 `type` 字段
- sse.ts handlers 是 `{[event]: fn}` 字典，'onEvent' 不会被当 event 注册
- 后端 require_permission 不加 = 前端菜单隐藏但直链访问会泄露数据（**必须前后端都做**）

---

**Generated by Mavis | 2026-06-14**
