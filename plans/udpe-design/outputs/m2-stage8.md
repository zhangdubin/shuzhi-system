# M2 阶段 8 — AdminPrintTemplate 模板预览按钮

> 阶段：M2 阶段 8  
> 完成日期：2026-06-28  
> 设计文档：plans/udpe-design/design.md §三 §四 §十

## 目标

在 `AdminPrintTemplate` 管理页（`/admin/print-template`）给每个模板行加「👁 预览」按钮，
让管理员**不用写代码、不用切业务页面**也能验证模板渲染效果。

业务流：选模板 → 选一条业务记录 → 看 HTML 预览 → 改模板 → 重新生成。

## 实现概览

### 1. 模板中心预览入口（AdminPrintTemplate.vue）

**位置**：`frontend/src/views/admin/AdminPrintTemplate.vue:321`

```vue
<el-button size="small" type="primary" link @click="openPreview(row)">👁 预览</el-button>
```

### 2. 业务流程

`openPreview(row)` → 弹出浮条 picker → 拉业务列表 → 默认选第一条 → 触发 `PrintPreviewDialog`

```ts
async function openPreview(t: any) {
  previewTemplate.value = t
  previewVisible.value = true
  previewBusinessId.value = null
  previewLoading.value = true
  try {
    const list = await fetchBusinessList(t.docType)
    previewBusinessOptions.value = list
    if (list.length > 0) previewBusinessId.value = list[0].value
  } catch (e: any) {
    ElMessage.error('加载业务记录失败：' + (e?.message || ''))
  } finally {
    previewLoading.value = false
  }
}
```

### 3. 业务选择器（4 套对应 4 个 API）

```ts
async function fetchBusinessList(docType: string) {
  // contract    → contractApi.list   → r.contractId
  // invoice     → invoiceOcrApi.records → r.invoiceId
  // expense     → expenseApi.list    → r.expenseId
  // reimbursement → reimburseApi.list → r.formId
}
```

### 4. UI 设计：浮条 + 弹窗组合

去除外层 `el-dialog`（避免嵌套 dialog），改用 `position: fixed` 浮条 picker + `PrintPreviewDialog` 自身 dialog。

```vue
<div v-if="previewVisible && previewTemplate" class="preview-picker">
  <span>选一条 {{ previewTemplate.docType }} 记录预览：</span>
  <el-select v-model="previewBusinessId" :loading="previewLoading" placeholder="请选择">
    <el-option v-for="opt in previewBusinessOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
  </el-select>
</div>

<PrintPreviewDialog
  v-if="previewVisible && previewTemplate && previewBusinessId !== null"
  v-model="previewVisible"
  :template-code="previewTemplate.code"
  :data="{ _resolver: String(previewBusinessId) }"
  :source-module="previewTemplate.docType"
  :source-id="String(previewBusinessId)"
  :title="`${previewTemplate.name} 预览`"
/>
```

样式（fixed 浮条，z-index: 2000）：

```scss
.preview-picker {
  position: fixed;
  top: 80px; right: 24px;
  z-index: 2000;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.10);
  padding: 12px 16px;
}
```

## 修复的 4 个 ID 字段 bug

每个业务表的 ID 字段名不同，前期用了 `r.id` 全部走不通：

| 业务类型 | 列表 API | 实际 ID 字段 | 备注 |
|---------|---------|------------|------|
| contract | `contractApi.list` | `contractId` | `r.contractId \|\| r.id` |
| invoice | `invoiceOcrApi.records` | `invoiceId` | 之前 `invoiceOcrApi.list` 不存在 → 改为 `records` |
| expense | `expenseApi.list` | `expenseId` | `r.expenseId \|\| r.id` |
| reimbursement | `reimburseApi.list` | `formId` | `r.formId \|\| r.id` |

## 修复的 2 个 PrintPreviewDialog bug

### Bug A: 组件挂载时 watch 不触发

`PrintPreviewDialog` 用 `v-if` 挂载时 `modelValue` 已经是 `true`，普通 watch 默认 `immediate: false` 不会触发 `loadPreview()`。

**修复**（`frontend/src/components/common/PrintPreviewDialog.vue:181`）：

```ts
watch(() => props.modelValue, (v) => {
  if (v) {
    html.value = ''
    errorMsg.value = null
    nextTick(loadPreview)
  }
}, { immediate: true })  // ← 加 immediate: true
```

**影响范围**：所有使用 `v-if` 挂载的调用方（管理后台、批量预览场景）。

业务详情页（`ContractDetail` 等）不受影响 — 它们用 `v-model="printDialogVisible"` 走 false→true 流程，watch 原本就触发。

### Bug B: sourceId 类型不匹配

后端 Pydantic schema 期望 `sourceId: str`，前端发的是 `number` → 422 错误。

**修复**（`AdminPrintTemplate.vue:427-429`）：

```ts
:data="{ _resolver: String(previewBusinessId) }"
:source-module="previewTemplate.docType"
:source-id="String(previewBusinessId)"
```

### Bug C: catch 分支不解析 Pydantic 422 detail

Pydantic 422 返回 `{detail: [{loc, msg, type}, ...]}`，旧代码只取 `.message`，对 422 显示 "预览生成失败"（信息丢失）。

**修复**（`PrintPreviewDialog.vue:128-141`）：

```ts
} catch (e: any) {
  const detail = e?.response?.data?.detail
  let msg = e?.response?.data?.message || e?.message || '预览生成失败'
  if (Array.isArray(detail) && detail.length > 0) {
    const d = detail[0]
    msg = `${d.loc?.join('.') || ''}: ${d.msg || ''}`.replace(/^: /, '')
  } else if (typeof detail === 'string') {
    msg = detail
  }
  errorMsg.value = msg
  emit('error', e)
}
```

## 端到端验证（4 套模板）

测试账号：admin / admin123（张明）

| 模板 | 业务记录 | 渲染结果 | 截图 |
|------|---------|---------|------|
| contract_v1 | HT-2026-002 北辰集团系统集成合同 | ✅ 合同编号/客户/¥248,000.00/金额大写/签订日期全部渲染 | `/tmp/preview-final-contract_v1.png` |
| invoice_v1 | 26352000001267458331 | ✅ 销方神州山海/购方中科世通/¥753/税额/税率 | `/tmp/preview-final-invoice_v1.png` |
| expense_v1 | EX-2026-003 Q2 部门办公用品采购 | ✅ 费用名称/类型/申请人/¥350/大写叁佰伍拾元整 | `/tmp/preview-final-expense_v1.png` |
| reimbursement_v1 | RB-20260624-59D4 | ✅ 表格 2 项/报销总额 ¥2,829,275/大写贰佰捌拾贰万玖仟贰佰柒拾伍元整 | `/tmp/preview-final-reimbursement_v1.png` |

所有模板 6-53ms 渲染完成，srcdoc 平均 1700-3300 字符，iframe 加载正常。

## 关键设计决策

1. **零破坏**：AdminPrintTemplate 改造只新增了 1 个按钮 + 1 个浮条 + 1 个 dialog 调用，**未触碰任何原有 4 处业务详情页的打印集成**。
2. **浮条 + 弹窗分离**：picker 是轻量浮条，弹窗走 PrintPreviewDialog，避免嵌套 dialog 的 z-index / mask 问题。
3. **即时预览**：watch 加 immediate 后，picker 默认选第一条 → 立刻看到效果，不用再点确认。
4. **422 错误友好化**：catch 分支解析 Pydantic detail 数组，管理员看到的是 `options.sourceId: Input should be a valid string` 而不是模糊的"预览生成失败"。

## 后续优化（不阻塞 M2 收尾）

1. 模板 JSON 可视化编辑器（V2+）
2. 模板版本对比 / 差异高亮
3. 预览记录保存到 print_logs（已自动记录 — `request_data` 含 `_resolver` 和 `sourceId`）
4. 多条记录批量预览对比

## 回归测试（M2 阶段 8.1：修复合同详情 422）

阶段 8 完成后跑了 M2 阶段 6/7 集成回归，**发现并修复了 1 个新引入的回归**：

### 回归描述
原 `PrintPreviewDialog.fullOptions()` 直接透传 `sourceId`。
4 个业务详情页（`ContractDetail` 等）用 `Number(route.params.id)` 传 number，但后端 Pydantic schema 要 string → 422。

### 修复
在 `fullOptions()` 统一转 string（`PrintPreviewDialog.vue:106-114`）：

```ts
const fullOptions = () => {
  const sid = props.sourceId ?? props.options?.sourceId
  return {
    ...(props.options || {}),
    sourceModule: props.sourceModule || props.options?.sourceModule,
    sourceId: sid !== undefined && sid !== null ? String(sid) : sid,
  }
}
```

### 回归测试结果
- 合同详情 `/contract/2` → ✅ 渲染成功（HT-2026-032 云服务采购合同）
- 发票详情 `/invoice/ocr/1` → 422 错误信息友好化（"Resolver 'invoice' 失败: 发票不存在：1"）
- 0 个 pageerror
- 0 个新增 4xx/5xx
