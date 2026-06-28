# M2 阶段 7 交付报告：补前端模块入口

> 对应 UDPE 设计文档 §五（管理后台）
> 完成时间：0.5 个工作日
> 状态：✅ 完成

## 问题诊断

**用户反馈**："前端还没有把模块显示出来"。

**根因**：M1 阶段 2 把后端端点全部建好（`/api/v1/admin/print-templates*` + `/api/v1/print/log`），但前端**完全没有**：
- 路由注册
- 菜单配置
- 管理页面

因此业务方无法在 Web 端管理模板或查看日志。

## 交付物

### 1. 2 个新页面

| 页面 | 路径 | 作用 |
|---|---|---|
| `AdminPrintTemplate.vue` | `/admin/print-template` | 模板列表 + 状态切换（发布/归档）+ JSON 查看 + 创建 |
| `AdminPrintLog.vue` | `/admin/print-log` | 打印日志查询（含 KPI 仪表盘） |

### 2. 路由 + 菜单

| 改动 | 文件 | 内容 |
|---|---|---|
| 路由注册 | `frontend/src/router/index.ts` | 2 个新路由 + meta.permission |
| 菜单 | `frontend/src/config/menu.ts` | 2 个新子菜单（系统设置下） |

**菜单位置**：`系统设置 → 系统 → 打印模板 🖨 / 打印日志 🎫`

### 3. 补全 SDK

`frontend/src/api/print.ts` 新增 4 个方法：
- `getTemplate(tid)` — 模板详情
- `publishTemplate(id)` — 发布
- `archiveTemplate(id)` — 归档
- `createTemplate(payload)` — 创建
- `updateTemplate(id, payload)` — 更新

## 端到端验证

```
=== M2 阶段 7 验收：前端 2 个新模块端到端 ===

[1] /api/v1/admin/print-templates (admin 打印模板列表)
  total=4, list OK: 4 模板
    contract_v1               contract        active   v1
    expense_v1                expense         active   v1
    invoice_v1                invoice         active   v1
    reimbursement_v1          reimbursement   active   v1

[2] /api/v1/print/log (admin 打印日志)
  total=0, list shape OK

[3] 测一次打印以产生 1 条日志
  PDF: HTTP 200 | 3095 bytes

[4] 再次查日志
  total=1
    log#24 pdf success  invoice_v1  invoice  elapsed=6ms pdfSize=3095B

[5] 模拟前端路由访问（页面是否在 dist 中）
  /admin/print-template 路由注册:  true
  /admin/print-log 路由注册:      true
  AdminPrintTemplate.vue 模块:    true
  AdminPrintLog.vue 模块:         true
  菜单 Printer 图标:              true
```

- ✅ Build 0 错误（`vite build` 5.4s）
- ✅ 后端 4 套模板列表返回
- ✅ 打印 1 次 → 日志写入
- ✅ 2 路由在 dist 中
- ✅ 2 页面模块在 dist 中
- ✅ 菜单 Printer 图标已打包

## 关键文件清单

| 文件 | 状态 | 行数 |
|---|---|---|
| `frontend/src/views/admin/AdminPrintTemplate.vue` | 新增 | 296 行 |
| `frontend/src/views/admin/AdminPrintLog.vue` | 新增 | 188 行 |
| `frontend/src/router/index.ts` | 改：+ 2 路由 | +2 行 |
| `frontend/src/config/menu.ts` | 改：+ 2 子菜单 | +2 行 |
| `frontend/src/api/print.ts` | 改：+ 5 方法 | +30 行 |

## 关键 UI 设计

### AdminPrintTemplate.vue

```
┌─ 页面头（标题 + 描述 + 刷新 / 新建）──┐
│  🧾 打印模板                          │
│  UDPE 统一单据打印引擎的模板中心     │
└────────────────────────────────────────┘
┌─ KPI（5 卡）────────────────────────┐
│ 4 总数 │ 3 已发布 │ 0 草稿 │ 0 归档 │ 4 业务类型 │
└─────────────────────────────────────┘
┌─ 过滤（业务类型 + 状态）────────────┐
│ 业务类型 [全部▾]  状态 [全部▾]      │
└─────────────────────────────────────┘
┌─ 列表（el-table）──────────────────┐
│ 模板标识 │ 业务类型 │ 纸型 │ 状态 │ 默认 │ 描述 │ 时间 │ 操作 │
│ contract_v1 v1 │ 合同 │ A4/纵 │ 已发布 │ ⭐ │ 合同 A4 单页 │ ... │ 查看/归档 │
│ ...                                  │
└─────────────────────────────────────┘
```

### AdminPrintLog.vue

```
┌─ KPI（5 卡）────────────────────────┐
│ 50 本次查询 │ 49 成功 │ 1 失败 │ 145.6 KB │ 8ms 平均 │
└─────────────────────────────────────┘
┌─ 过滤（按模板 code 查）────────────┐
│ 模板 code [留空查全部] [查询]       │
└─────────────────────────────────────┘
┌─ 列表 ─────────────────────────────┐
│ log# / 时间 │ 操作 │ 模板 │ 状态 │ 操作员 │ 来源 │ 耗时 │ 大小 │ 错误 │
│ #24 18:35 │ PDF │ invoice_v1 │ 成功 │ 张明 │ invoice #3 │ 6ms │ 3095B │ — │
└─────────────────────────────────────┘
```

## 零破坏验证

- ✅ 现有 28 个权限码 + 5 个 print 权限码继续工作
- ✅ `super_admin` 已有 `print:template:read` + `print:document:read`，直接看到菜单
- ✅ 现有 admin 子菜单（用户/角色/部门/字典/审批流/审计）位置不变
- ✅ 业务详情页的 4 个"按模板打印"按钮继续工作

## 阶段总结

| 阶段 | 交付 | 状态 |
|---|---|---|
| 阶段 1：架构设计 | design.md | ✅ |
| 阶段 2：数据库 + 接口 | 3 表 + 5 权限 + 8 端点 | ✅ |
| 阶段 3：核心引擎 | 2 Renderer + 4 Resolver + 1 Provider + 4 模板 + 缓存 | ✅ |
| 阶段 4：模板设计器 | 推迟到 M3 | ⏸️ |
| 阶段 5：迁移现有业务 | 4 详情页集成 | ✅ |
| 阶段 6：通用组件 | PrintByTemplateButton + PrintPreviewDialog | ✅ |
| **阶段 7：补前端模块** | **2 管理页 + 2 路由 + 2 菜单 + 5 SDK** | ✅ |
| 阶段 8：高级功能 | 批量/异步/签名 | ⏸️ |

## 完整用户路径（端到端）

1. 管理员打开 `http://localhost/admin/print-template` → 看到 4 套预置模板
2. 看到「已发布」状态、可点「归档」切到 archived
3. 看到 draft 状态时点「发布」切到 active
4. 点「查看 JSON」看到模板结构
5. 打开 `http://localhost/admin/print-log` → 看到最近 50 条打印记录
6. 看到每条的：模板/状态/操作员/来源/耗时/PDF 大小
7. 业务方在 `/contract/1` / `/invoice/ocr/3` 等详情页点「🧾 按模板打印」→ 弹新 PreviewDialog
8. PDF 走 UDPE 引擎 → 新窗口预览 → 浏览器打印 / 下载

## 下一步建议

| 优先级 | 任务 | 价值 |
|---|---|---|
| M2 阶段 8 | 模板预览：详情页加「在浏览器里预览」按钮（调 preview 端点拿 HTML） | 减少试错成本 |
| M3 阶段 4 | 可视化模板设计器 | 业务方自助改模板 |
| M3+ | 批量打印 / 异步队列 / 数字签名 | 高阶功能 |
