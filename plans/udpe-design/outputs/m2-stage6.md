# M2 阶段 6 交付报告：通用 PreviewDialog 组件化

> 对应 ChatGPT 流程 / UDPE 设计文档 §十 SDK
> 完成时间：0.5 个工作日
> 状态：✅ 完成

## 交付物

### 1. 通用组件 2 个

| 组件 | 路径 | 作用 |
|---|---|---|
| `PrintByTemplateButton` | `frontend/src/components/common/PrintByTemplateButton.vue` | 统一按钮 + 权限检查 + emit click |
| `PrintPreviewDialog` | `frontend/src/components/common/PrintPreviewDialog.vue` | 统一预览弹窗：调 preview → iframe srcdoc → 下载 / 浏览器打印 / 重新生成 |
| `print/index.ts` | `frontend/src/components/common/print/index.ts` | 统一出口 |

### 2. 4 个详情页重构为新组件

| 详情页 | 之前（独立函数 + window.open） | 现在（共用组件） |
|---|---|---|
| `InvoiceDetail.vue` | 38 行 printByTemplate + window.open | 1 个 PrintByTemplateButton + 1 个 PrintPreviewDialog |
| `ContractDetail.vue` | 49 行 printByTemplate + window.open | 同上 |
| `ReimburseDetail.vue` | 50 行 printByTemplate + window.open | 同上 |
| `ExpenseDetail.vue` | 44 行 printByTemplate + window.open | 同上 |

**减少样板代码约 180 行 → 0 行**（每个页面只需 6-7 行配置项）

### 3. 组件 API 设计

#### `PrintByTemplateButton.vue`

```ts
interface Props {
  templateCode: string            // 必填，UDPE 模板 code
  businessId: string | number     // 必填，业务单据 ID
  sourceModule: string            // 必填，模块名
  label?: string                  // 默认 '按模板打印'
  icon?: string                   // 默认 '🧾'
  tag?: 'button' | 'el-button'    // 默认 'el-button'
  elType?: 'primary' | ...        // 默认 'primary'
  size?: 'small' | 'default' | 'large'
  buttonClass?: string            // 自定义 CSS class
  bypassPermission?: boolean      // 跳过权限检查
}
emit('click', { templateCode, businessId, sourceModule })
```

#### `PrintPreviewDialog.vue`

```ts
interface Props {
  modelValue: boolean             // v-model 控制显隐
  templateCode: string
  data?: Record<string, any>
  options?: Record<string, any>
  sourceModule?: string           // 透传到 options
  sourceId?: string | number
  title?: string
}
emit('update:modelValue', boolean)
emit('success', { logId, elapsedMs, pdfSize? })
emit('error', Error)
```

**自动行为**：
- `modelValue` 由 false → true 时**自动**调 `/print/preview` 拉 HTML
- 用 `iframe srcdoc` 渲染 HTML（沙箱 `allow-same-origin allow-scripts`）
- 头部工具栏：📥 下载 PDF / 🖨 浏览器打印 / 提示文案 / 🔄 重新生成
- 失败时显示 el-alert + 重新生成按钮
- `@media print` 时只输出 iframe 内容（隐藏工具栏 + 弹窗 chrome）

## 4. 端到端验证

```
=== preview 4 模板 ===
  invoice_v1:        html=1694B, logId=16, elapsed=5ms
  contract_v1:       html=2244B, logId=17, elapsed=3ms
  expense_v1:        html=1840B, logId=18, elapsed=3ms
  reimbursement_v1:  html=5750B, logId=19, elapsed=3ms

=== PDF 4 模板（看 X-Print-Log-Id 头）===
  HTTP/1.1 200 OK  x-print-log-id: 20   (invoice_v1)
  HTTP/1.1 200 OK  x-print-log-id: 21   (contract_v1)
  HTTP/1.1 200 OK  x-print-log-id: 22   (expense_v1)
  HTTP/1.1 200 OK  x-print-log-id: 23   (reimbursement_v1)
```

- ✅ Build 0 错误（`vite build` 5.3s）
- ✅ 4 模板 preview 端点全过
- ✅ 4 模板 pdf 端点全过
- ✅ log_id 16-23 全部写入

## 关键文件清单

| 文件 | 改动 |
|---|---|
| `frontend/src/components/common/PrintPreviewDialog.vue` | 新增（160 行） |
| `frontend/src/components/common/PrintByTemplateButton.vue` | 新增（80 行） |
| `frontend/src/components/common/print/index.ts` | 新增（统一出口） |
| `frontend/src/views/invoice/InvoiceDetail.vue` | 重构：删除 38 行 printByTemplate + 改用组件 |
| `frontend/src/views/contract/ContractDetail.vue` | 重构：删除 49 行 printByTemplate + 改用组件 |
| `frontend/src/views/reimbursement/ReimburseDetail.vue` | 重构：删除 50 行 printByTemplate + 改用组件 |
| `frontend/src/views/expense/ExpenseDetail.vue` | 重构：删除 44 行 printByTemplate + 改用组件 |

## 零破坏验证

- ✅ 4 处原打印 hack 全部保留（用户仍可走老路径：iframe / window.open / el-dialog / @media print）
- ✅ 老路径按钮未改、入口未删
- ✅ 新路径（UDPE 弹窗）作为**新入口**提供
- ✅ 4 套模板、Resolver、Provider、缓存全部未动
- ✅ 后端 8 端点 + 3 表 + 5 权限码全部未动

## 阶段 6 价值

| 指标 | 之前（M2 阶段 5 结束） | 现在（M2 阶段 6 完成） |
|---|---|---|
| 重复代码 | 4 处 × ~45 行 = ~180 行 | **0**（共用组件） |
| 新业务接入成本 | 加 1 函数 + 1 按钮 + 1 事件 = ~50 行 | **加 1 组件 + 1 dialog = 7 行** |
| UI 一致性 | 4 处样式各自不同 | **统一弹窗 + 统一工具栏** |
| 权限检查 | 各处手写 v-permission | **组件内自动** |
| 错误处理 | 各处手写 try/catch | **组件内统一** |
| 浏览器打印按钮 | 无 | **统一在 dialog 工具栏** |
| 重新生成 | 无 | **统一在 dialog 工具栏** |

## 接入示例（新业务模块）

```vue
<template>
  <PrintByTemplateButton
    template-code="<my_doc>_v1"
    :business-id="myDocId"
    source-module="<my_module>"
    @click="printDialogVisible = true"
  />
  <PrintPreviewDialog
    v-model="printDialogVisible"
    template-code="<my_doc>_v1"
    :data="{ _resolver: myDocId }"
    source-module="<my_module>"
    :source-id="myDocId"
    title="<业务名称>打印预览"
  />
</template>

<script setup>
import { ref } from 'vue'
import { PrintByTemplateButton, PrintPreviewDialog } from '@/components/common/print'
const myDocId = ref(0)
const printDialogVisible = ref(false)
</script>
```

**接入成本：~10 行**，零样板。

## 阶段总结

| 阶段 | 交付 | 状态 |
|---|---|---|
| 阶段 1：架构设计 | `plans/udpe-design/design.md` | ✅ |
| 阶段 2：数据库 + 接口 | 3 表 + 5 权限 + 8 端点 | ✅ |
| 阶段 3：核心引擎 | 2 Renderer + 4 Resolver + 1 Provider + 4 模板 + 缓存 | ✅ |
| 阶段 4：模板设计器 | 推迟到 M3 | ⏸️ |
| 阶段 5：迁移现有业务 | 4 详情页集成 UDPE | ✅ |
| **阶段 6：通用组件** | **2 组件 + 4 详情页重构，消除 180 行样板** | ✅ |
| 阶段 7：高级功能 | 批量/异步/签名（推迟 M3+） | ⏸️ |

## 下一步建议

| 优先级 | 任务 | 价值 |
|---|---|---|
| M2 阶段 7 | 把 `printApi` SDK 抽到独立 `packages/udpe-sdk`（可复用） | 跨项目复用 |
| M3 阶段 4 | 模板设计器（可视化拖拽 + 预览同步） | 长期价值 |
| M3+ | 批量打印 / 异步队列 / 数字签名 | 高阶功能 |
| 长期 | 沉淀为 SaaS 打印平台 | 商业化 |
