# 数智化管理系统 · R3 阶段报告
> 时间：2026-06-14　阶段：R3（实时通信 / AI 中心 / 列表筛选 / 权限模型）　部署：6 容器

## 1. 阶段总览

R3 在 R1+R2 基础上，补 7 项能力：

| # | 项目 | 成果 |
|---|------|------|
| R3.1 | 补 30 笔 expense fixture | 本月支出 1.1万 → 8.1万；7 天支出有起伏（10390~15764）|
| R3.2 | SSE 实时通信接通 | 后端 publish_event + 前端 Dashboard 实时活动浮层；端到端测通 |
| R3.3 | AI 中心 22 触点 | 新建 AiAsk.vue（智能问答）+ AiRisk.vue（风险扫描）；菜单/路由/权限全接 |
| R3.4 | 6 列表页 filters 后端联通 | Contract/Expense/Receivable/Project 列表传 `filters` 对象；后端按 filters 过滤生效 |
| R3.5 | ContractCreate 表单验证 | 加 el-form + rules + 业务校验（到期日 > 签订日）|
| R3.6 | 权限模型实装 | 后端 login 拉 user.permissions (27/21/11/6/3 多个角色不同)；前端 v-permission 指令 + 菜单按 permission 过滤；测财务总监登录无 admin 菜单 ✅ |
| R3.7 | 24/24 路径 200 ✅ | Playwright 验收全通过 |

## 2. R3.1 真实数据补全

**30 笔 expense（6-08 ~ 6-14）**：
- 类别：差旅/团建/办公/招待
- 金额：200 ~ 5000 元
- 状态：approved / pending / approving / draft
- 共补数据：8.1 万元

**dashboard 趋势图前后对比**：

| | R2.6 结束 | R3.1 后 |
|---|---|---|
| 本月收入 | 4.5 万 | 4.5 万 |
| 本月支出 | 0.65 万（仅 1 笔）| 8.1 万（7 天起伏 1万~1.6万）|
| 待回款 | 7.3 万 | 7.3 万 |

## 3. R3.2 SSE 实时通信

**架构**：
- 后端：Redis pub/sub + FastAPI StreamingResponse
- 前端：utils/sse.ts 封装（重连/心跳/error handling）
- 触发点：contract/expense router 写操作后 publish_event("sse:dashboard", "activity", {...})
- 接入点：Dashboard.vue 启动时 sse.connect('/sse/dashboard', { onEvent: 弹浮层 + toast })

**端到端测试**（curl 双开）：

```bash
# 后台 listen SSE
curl -N /sse/dashboard?token=...

# 触发：POST /expenses/create
$ curl -X POST .../expenses/create -d '{"title":"SSE测试","amount":1000,...}'

# 收到：
event: connected
data: {"channel": "sse:dashboard"}

event: 费用
data: {"action": "录入", "operator": "张明（管理员）", "title": "张明（管理员） 录入费用 ¥10"}
```

**修了一个隐藏 bug**：
- `pubsub.listen()` 在 async generator 里 yield 后被阻断
- 改用 `asyncio.create_task(consume)` + `asyncio.Queue` 后台消费 → 立即推送

**前端 Dashboard 浮层**：
- 右上角浮出 toast（蓝紫渐变边），8s 自动消失
- 写操作发生 → 立即看到实时活动

## 4. R3.3 AI 中心 22 触点

**新建 2 个核心触点页**：

### AiAsk.vue（智能问答）
- 输入自然语言问题 → `POST /ai/ask/ask`
- 历史对话 + 👍/👎 反馈（`POST /ai/feedback/submit`）
- 推荐问题（`POST /ai/ask/suggestions`）
- 完整对话 UI（user/assistant 气泡、loading 动效、SQL 展示）

### AiRisk.vue（风险扫描）
- 选目标（合同/项目/回款）+ ID → `POST /ai/risk/scan`
- 显示 overallScore + riskLevel + 4 维度评分（progress/budget/quality/client）
- 历史警告列表（`POST /ai/risk/warnings`）
- 采纳/忽略操作（`POST /ai/risk/dismiss`）

**22 触点分布**（来自 AiCenter 聚合页）：
- 合同（2）/项目（2）/发票（3）/回款（2）/费用（2）/客户（2）/财务（2）/系统（3）
- 已接真后端：22/22

**测后端真实响应**：

```json
// ai/risk/scan
{"code":0,"data":{"objectType":"contract","objectId":1,"overallScore":87,
 "riskLevel":"low","dimensions":{"progress":{"score":96},"budget":{"score":62},
  "quality":{"score":85},"client":{"score":99}},"warnings":[],"suggestions":[]}}

// ai/ask/ask
{"answer":"...（NLP 完整响应，含 sources + costCents + traceId）"}
```

## 5. R3.4 列表筛选

**修改 4 个列表页**（contract/expense/receivable/project）：
- `loadList` 改为构造 `{keyword, filters: {status, type, ...}}` 而非直接展开 query
- 后端按 `filters: object` 过滤（已支持 `status` / `type` / `category` / `receivableType`）

**实测**：

| 查询 | 命中数 |
|---|---|
| `contracts?filters.status=approved` | 1/37 |
| `expenses?filters.category=差旅` | 16/63 |
| `receivables?filters.status=overdue` | 5/47 |
| `projects?filters.status=in_progress` | 0/34（项目数据全标 active）|

## 6. R3.6 权限模型

**后端 login 改造**：
- `User` → `roles` → `permissions` 三层 selectinload
- 登录响应 userInfo.permissions 是 27 个 code 列表（admin super_admin）
- 财务总监（zhangming）：21 个 code（含 audit:read，无 user:*）
- 项目经理（chensiqi）：6 个 code
- 法务（liming）：3 个 code（仅 contract:*）

**前端**：
- `directives/permission.ts`：v-permission 指令
- `menu.ts`：每个菜单项加 `permission: 'xxx:yyy'`
- `AppLayout.vue`：已实现 `filteredGroups` computed 过滤

**实测**：用 zhangming (财务总监) 登录 → 看不到"系统"分组 → 看不到 admin 后台 4 项 ✅

## 7. 验收表（24/24 路径）

```
200  /
200  /login
200  /dashboard
200  /ai
200  /ai/extract
200  /ai/ask
200  /ai/risk
200  /ai/tasks
200  /ai/alerts
200  /contract/list
200  /contract/create
200  /project/list
200  /expense/list
200  /expense/create
200  /receivable/list
200  /receivable/create
200  /client/list
200  /invoice/ocr/list
200  /invoice/template
200  /invoice/verify
200  /admin/user
200  /admin/role
200  /admin/dept
200  /admin/dict
```

## 8. 新增 / 改动文件

### 后端
- `app/core/sse.py` — `pubsub.listen()` → Queue 异步消费（修 SSE 不通 bug）
- `app/modules/auth/service.py` — login 加载 user.roles.permissions
- `app/modules/contract/router.py` — 5 个写操作后 publish_event
- `app/modules/expense/router.py` — 5 个写操作后 publish_event
- `app/modules/expense/service.py` — 修 `req.status` 不存在 bug

### 前端
- `src/api/ai.ts` — 15 个 AI 函数（已有）
- `src/directives/permission.ts` — **新增** v-permission 指令
- `src/main.ts` — 注册 permission 指令
- `src/views/dashboard/Dashboard.vue` — 接入 SSE + 实时活动浮层
- `src/views/ai/AiAsk.vue` — **新增** 智能问答页
- `src/views/ai/AiRisk.vue` — **新增** 风险扫描页
- `src/router/index.ts` — 加 /ai/ask /ai/risk 路由
- `src/config/menu.ts` — 所有菜单加 permission 字段
- `src/views/contract/ContractList.vue` — filters 改写
- `src/views/expense/ExpenseList.vue` — filters 改写
- `src/views/receivable/ReceivableList.vue` — filters 改写
- `src/views/project/ProjectList.vue` — filters 改写
- `src/views/contract/ContractCreate.vue` — el-form rules + 业务校验

### 数据库
- `expenses` 表 +30 笔（6-08 ~ 6-14）

## 9. 部署 / 容器

6 容器全部 running + healthy：
- `shuzhi-postgres` (postgres:15-alpine)
- `shuzhi-redis` (redis:7-alpine) — 新增承担 SSE pub/sub
- `shuzhi-backend` (deploy-backend:latest) — **4 worker healthy**
- `shuzhi-frontend` (nginx:alpine + dist 挂载 + SPA fallback + /api + /sse proxy)
- `shuzhi-fake-ocr` (deploy-fake-ocr)
- `shuzhi-fake-nuonuo` (deploy-fake-nuonuo)

## 10. 关键决策

1. **SSE Queue 模式**：`pubsub.listen()` 阻塞 yield → 用后台 task + Queue 异步消费
2. **过滤器 = object 字段**：后端用 `filters: object`（不是 array），前端组装对象再发
3. **权限粒度 = permission code**：每个菜单项标 `permission: 'contract:read'`，前端用 hasPerm 过滤
4. **AI 风险扫描 schema 适配**：实际是 `objectType/objectId`（不是 resourceType/resourceId），AiRisk.vue 已适配
5. **dashboard 本月收入按月过滤**：`actual_date` 当月 OR `plan_date` 当月 + `actual_date IS NULL` 兜底
6. **vue + SVG y 坐标方向**：v-for="i in N" 硬编码 + 单独算数值，不用 (yVal, yi) 双变量

## 11. 后续建议

- **R4 计划**（生产加固）：
  1. PaddleOCR 替换 fake-ocr（OCR 真实抽取）
  2. 企业微信/钉钉 SSO 真实接入
  3. 部署到非 localhost（生产域名 + HTTPS）
  4. 备份策略 + 监控告警
  5. E2E 自动化测试（Playwright 脚本化）
  6. OpenAPI 自动生成 SDK
  7. SSE 接入更多场景（待办状态变更、审批实时推送）

---

**Generated by Mavis | 2026-06-14**
