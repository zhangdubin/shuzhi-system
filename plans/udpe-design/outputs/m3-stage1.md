# M3 阶段 1 — JSON 编辑器 + 实时预览

> 阶段：M3 阶段 1  
> 完成日期：2026-06-28  
> 设计文档：plans/udpe-design/design.md §十三 阶段 4（设计器 4 周 → 阶段 1 仅取 JSON 编辑 + 实时预览）

## 范围说明

设计文档把 M3 设计器定为 4 周投入（三栏布局 2w + 属性面板 1w + 数据绑定 UI 1w）。
本次只做**第一阶段**：让 JSON 编辑器真的能用 —— 实时看到渲染结果，方便业务方试错。

| 设计文档 | M3 阶段 1 | 说明 |
|---------|-----------|------|
| 三栏布局（组件库 / 画布 / 属性面板） | ❌ 不上 | 阶段 2+ |
| 拖拽 + 坐标定位 | ❌ 不上 | 阶段 2+ |
| 属性面板（字体 / 字号 / 对齐 / ...） | ❌ 不上 | 阶段 2+ |
| 数据绑定 UI（点选字段） | ❌ 不上 | 阶段 2+ |
| **JSON 编辑器（独立路由）** | ✅ 上 | 独立页 + 深色代码风格 |
| **实时预览** | ✅ 上 | 防抖 600ms 自动调 /print/preview-schema |
| **加载预置模板** | ✅ 上 | 4 套预置一键复制到编辑器 |

## 实现概览

### 1. 后端新端点 `POST /print/preview-schema`

**位置**：`backend/app/modules/print_runtime/router.py:127`

请求：
```json
{
  "docType": "contract",
  "schemaJson": { "body": [...] },
  "data": {},
  "options": { "sourceModule": "contract" }
}
```

响应：
```json
{
  "code": 0,
  "data": {
    "html": "<!DOCTYPE html>...",
    "elapsedMs": 10
  }
}
```

权限：`print:template:write`（与编辑模板一致）

**关键设计**：**不写 print_logs**（预览而已，不污染实际日志），返回 `logId: 0`。

### 2. Service `render_by_schema`

**位置**：`backend/app/modules/print_runtime/service.py:261`

与 `service.render` 流程相同（VariableProvider → Resolver → Renderer），但：
- 跳过 `get_active_template_by_code` 数据库加载
- 直接用传入的 `schemaJson`
- 不写 `print_logs`

代码复用率高（90% 沿用 render 的逻辑），未来 M3 阶段 2+ 上设计器时继续复用。

### 3. 前端 SDK `printApi.previewSchema`

**位置**：`frontend/src/api/print.ts:115`

```ts
async previewSchema(args: {
  docType: string
  schemaJson: any
  data?: any
  options?: PrintOptions
}): Promise<{ html: string; elapsedMs: number }>
```

### 4. 独立路由 `/admin/print-template/editor/:id?`

**位置**：`frontend/src/router/index.ts:97`

- 无 `id` = 新建模式（空 schemaJson + 默认 code 提示）
- 有 `id` = 编辑模式（自动加载模板 + 默认选第一条业务数据）
- 权限 `print:template:write`

### 5. AdminPrintTemplateEditor.vue（核心页面）

**位置**：`frontend/src/views/admin/AdminPrintTemplateEditor.vue`（526 行）

**三栏布局**：

```
┌──────────────────────────────────────────────────────────┐
│ ← 返回列表 | 编辑模板 · 合同摘要 | 已发布 v1 | 撤销 保存  │  ← 顶部工具栏
├──────────┬────────────────────────┬─────────────────────┤
│ 基础信息 │ 模板 JSON (schemaJson) │ 实时预览            │
│  code    │  ✓ 10ms  格式化 加载预置 │   <iframe>         │
│  name    │  ┌──────────────────┐  │  ┌──────────────┐   │
│  业务类型 │  │ { "body": [...] }│  │  │  渲染结果    │   │
│  纸型    │  │                  │  │  │              │   │
│  方向    │  │                  │  │  │              │   │
│  描述    │  └──────────────────┘  │  └──────────────┘   │
│ ────── │                        │  刷新                │
│ 数据绑定 │                        │                     │
│  预览数据│                        │                     │
│  提示词  │                        │                     │
└──────────┴────────────────────────┴─────────────────────┘
```

**核心特性**：

- **左侧**：基础信息（el-form）+ 数据绑定（业务数据下拉 + 可用变量提示）
- **中间**：深色主题 JSON 编辑器（`#1E293B` 背景 + `#E2E8F0` 文字 + SF Mono 字体）
- **右侧**：iframe srcdoc 实时渲染（`sandbox="allow-same-origin"`）
- **顶部工具栏**：返回 / 状态 tag / 版本号 / 撤销 / 保存 / 发布
- **实时预览**：JSON 输入 → 600ms 防抖 → 调 `/print/preview-schema` → 渲染到右侧 iframe
- **错误显示**：JSON 错显示红条（不预览），渲染错显示 ElAlert
- **加载预置**：4 套预置（contract / invoice / expense / reimbursement）一键复制
- **保存**：新建（POST）→ 跳到编辑模式；编辑（POST /update）
- **发布**：draft 状态显示"发布"按钮 → 调 publishTemplate
- **离开保护**：isDirty 时点返回会弹 ElMessageBox 确认

### 6. AdminPrintTemplate 列表页加"编辑"入口

**位置**：`frontend/src/views/admin/AdminPrintTemplate.vue:322`

```vue
<el-button size="small" link @click="gotoEditor(row)">✏️ 编辑</el-button>
```

`gotoEditor()` 跳到 `/admin/print-template/editor/${row.id}`，业务方在列表页就能进编辑器。

## 端到端验证

### 1. 加载已有模板（id=2, contract_v1）

- 顶部正确显示：`编辑模板 · 合同摘要` + `已发布` + `v1`
- 左侧基础信息正确填充：code=contract_v1, name=合同摘要, 业务类型=合同
- 中间 JSON 编辑器加载完整 schema（30+ 行 body 配置）
- 右侧 iframe 实时渲染：合同编号 HT-2026-002 / 客户北辰实业集团 / 金额 ¥248,000.00 / 金额大写贰拾肆万捌仟元整
- 预览 elapsedMs: 10ms

### 2. 新建模式 + 加载预置

- 顶部显示：`新建打印模板`
- 点"加载预置"按钮 → ElMessage "已加载 contract 预置模板"
- 中间 JSON 立即填充预置 schema
- 右侧 iframe 实时渲染出模板

### 3. 4 套业务类型切换

- 改 docType 选择器 → 业务数据下拉自动重拉
- 选不同 docType → 重新点"加载预置" → 加载对应预置 schema
- 预览实时跟着 docType 变化

### 4. 回归测试（7 个页面）

| 页面 | 状态 |
|------|------|
| /admin/print-template | ✅ 标题: 🧾 打印模板 |
| /admin/print-log | ✅ 标题: 📜 打印日志 |
| /contract/list | ✅ 标题: 合同管理 |
| /expense/list | ✅ 标题: 销售费用 |
| /reimbursement/list | ✅ 标题: 🧾 报销中心 |
| /contract/2 | ✅ 标题: 万象科技 SaaS 服务合同 2026Q2 |
| /expense/3 | ✅ 标题: （mock） |

- 0 pageerror
- 0 新增 4xx/5xx
- M2 阶段 6/7/8/9 全部回归通过

## 关键设计决策

1. **不走模板库，直接编辑现有模板**：避免"模板版本管理"复杂度，M3 阶段 1 简单粗暴（保存就是新版本）。
2. **深色主题 JSON 编辑器**：参考 VSCode Dark+ 配色，业务方长时间编辑不刺眼。不引入 monaco-editor（避免 2MB+ 依赖）。
3. **防抖 600ms 自动预览**：用户输入完成立即看到效果，但不会每按一个键就发请求。
4. **不写 print_logs**：预览是开发行为，不应影响实际打印统计。`logId=0` 表示"非实际打印"。
5. **Schema 实时校验**：JSON 错就不发预览请求，避免后端 422 报错。错误信息显示在编辑器底部红条。
6. **业务数据下拉复用**：从 AdminPrintTemplate.vue 复制 `fetchBusinessList` 逻辑，4 套 ID 字段适配（contractId / invoiceId / expenseId / formId）。
7. **离开保护**：isDirty 检测防止误关，弹 ElMessageBox 确认。

## 文件清单

新增：
- `frontend/src/views/admin/AdminPrintTemplateEditor.vue` (526 行)
- `backend/app/modules/print_runtime/presets/*.json` (已存在，被前端硬编码引用)

修改：
- `backend/app/modules/print_runtime/schemas.py` (+12 行: `PrintPreviewBySchemaRequest`)
- `backend/app/modules/print_runtime/service.py` (+80 行: `render_by_schema`)
- `backend/app/modules/print_runtime/router.py` (+30 行: `/print/preview-schema` 端点)
- `frontend/src/api/print.ts` (+24 行: `previewSchema` 方法)
- `frontend/src/router/index.ts` (+1 行: editor 路由)
- `frontend/src/views/admin/AdminPrintTemplate.vue` (+6 行: 编辑按钮 + gotoEditor)

## 后续阶段（M3 阶段 2+）

| 任务 | 优先级 | 价值 |
|------|--------|------|
| 拖拽 + 组件库（左侧拖到画布） | P0 | 业务方零代码拼模板 |
| 属性面板（点选元素 → 改字体/字号/对齐） | P0 | 改样式不用动 JSON |
| 实时坐标定位 + 缩放 | P1 | WYSIWYG |
| 数据绑定 UI（点选字段 → 自动生成 {{ ... }}） | P1 | 降低模板写作门槛 |
| 模板版本管理（基于 schema 快照） | P2 | 防止误改 |
| 模板市场（共享模板） | P3 | 多租户价值 |

## 零破坏验证

- 4 处原打印 hack 全部保留
- 5 个 SDK 方法（preview / pdf / pdfBlob / listLogs / getTemplate / publish / archive）继续工作
- 9 个后端端点（除新增 preview-schema 共 10 个）继续工作
- 0 pageerror / 0 新增 4xx/5xx
- 7 个核心页面回归测试通过
