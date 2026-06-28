# M3 阶段 5 — 数据绑定 UI（设计文档）

> **状态**: 📐 设计阶段
> **作者**: Codex (claude-sonnet-4)
> **日期**: 2026-06-28
> **前置**: M3 阶段 3 (可视化设计器), M3 阶段 4 (Excel/Word 导入)
> **任务**: 在属性面板中增加数据绑定 UI，让业务方点选字段即可绑定到组件

## 一、目标与边界

### 1.1 目标
让业务方能够通过点选字段的方式将数据绑定到组件，**不需要手写 `{{ path }}` 表达式**。

### 1.2 范围（V1）
- ✅ 属性面板增加"数据绑定"区域
- ✅ 支持点选字段树（form.* / contract.* / invoice.* 等）
- ✅ 支持直接键入 `{{ path }}` 表达式
- ✅ 支持常用 filter 下拉选择（money / date / chinese_money 等）
- ✅ 绑定后自动更新组件的 `text` 字段
- ✅ 实时预览联动

### 1.3 范围外（V2+）
- ❌ 条件表达式（IF / ELSE）
- ❌ 循环表达式（FOR）
- ❌ 聚合函数（SUM / AVG / COUNT）
- ❌ 跨表关联（form.customer.name）
- ❌ 自定义 filter

## 二、UI 设计

### 2.1 属性面板布局（增加数据绑定区域）

```
┌─────────────────────────────────────┐
│ ⚞ 属性                    text     │
├─────────────────────────────────────┤
│ 文本内容                            │
│ ┌─────────────────────────────────┐ │
│ │ 合同编号：{{ contract.contractNo }} │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 数据绑定                            │
│ ┌─────────────────────────────────┐ │
│ │ 字段路径: [contract.contractNo ▾] │ │
│ │          ┌───────────────────┐  │ │
│ │          │ 📁 form           │  │ │
│ │          │   ├─ title        │  │ │
│ │          │   ├─ totalAmount  │  │ │
│ │          │   └─ remark       │  │ │
│ │          │ 📁 contract       │  │ │
│ │          │   ├─ contractNo   │  │ │
│ │          │   ├─ customerName │  │ │
│ │          │   └─ amount       │  │ │
│ │          └───────────────────┘  │ │
│ │ Filter:  [无 ▾] [money] [date]  │ │
│ │ 插入: [插入绑定] [插入静态文本]   │ │
│ └─────────────────────────────────┘ │
│                                     │
│ 字号: [12]                          │
│ 对齐: [左] [中] [右]                │
│ 文字色: [#1F2937]                   │
│ 加粗: [开关]                        │
└─────────────────────────────────────┘
```

### 2.2 字段树数据结构

```ts
interface FieldNode {
  key: string          // 字段名 (如 "title")
  path: string         // 完整路径 (如 "form.title")
  label: string        // 显示标签 (如 "标题")
  type: string         // 数据类型 (string / number / date / boolean)
  children?: FieldNode[]  // 子字段
}
```

### 2.3 预置字段树（按业务类型）

| 业务类型 | 字段树 |
|---------|--------|
| contract | form.title, form.contractNo, form.customerName, form.amount, form.startDate, form.endDate, ... |
| invoice | form.invoiceNo, form.amount, form.taxAmount, form.buyerName, form.sellerName, ... |
| reimbursement | form.title, form.totalAmount, form.applicantName, form.remark, form.detailCount, ... |
| expense | form.expenseNo, form.amount, form.category, form.applicantName, ... |

### 2.4 Filter 列表

| Filter | 说明 | 示例 |
|--------|------|------|
| (无) | 原始值 | `{{ form.title }}` |
| money | 分→元，保留2位 | `{{ form.amount \| money }}` |
| chinese_money | 分→大写元 | `{{ form.amount \| chinese_money }}` |
| date | 日期格式化 | `{{ form.startDate \| date }}` |
| datetime | 日期时间格式化 | `{{ printTime \| datetime }}` |
| default | 默认值 | `{{ form.remark \| default('无') }}` |

## 三、数据流

```
┌──────────────────────────────────────────────────────────────┐
│                  schemaJson (body: Component[])              │
│           ↑ 写                    ↑ 读                      │
│  PropertyPanel              VisualCanvas                    │
│  (数据绑定 UI)              (渲染绑定后的文本)               │
│           ↓                    ↓                            │
│     editorStore (reactive)                                 │
│           ↓                                                │
│     防抖 600ms → /print/preview-schema                     │
└──────────────────────────────────────────────────────────────┘
```

**绑定流程**：
1. 用户点选字段树中的字段 → 获取 `path`（如 `contract.contractNo`）
2. 选择 filter（可选）→ 生成表达式（如 `contract.contractNo | money`）
3. 点击"插入绑定" → 在光标位置插入 `{{ contract.contractNo | money }}`
4. 或点击"插入静态文本" → 插入纯文本

## 四、实现细节

### 4.1 字段树组件（新增）

`frontend/src/components/admin/print/FieldTree.vue`

```vue
<template>
  <div class="field-tree">
    <el-input v-model="searchText" placeholder="搜索字段..." clearable />
    <el-tree
      :data="filteredTree"
      :props="{ label: 'label', children: 'children' }"
      node-key="path"
      highlight-current
      @node-click="onNodeClick"
    />
  </div>
</template>
```

### 4.2 PropertyPanel 改动

在 `hasText` 区域下方增加"数据绑定"区域：

```vue
<!-- 数据绑定 -->
<el-form v-if="hasText" label-width="80px" size="default">
  <el-form-item label="数据绑定">
    <div class="bind-section">
      <!-- 字段树下拉 -->
      <el-popover trigger="click" width="300">
        <template #reference>
          <el-input
            :model-value="currentBindPath"
            placeholder="点击选择字段..."
            readonly
          />
        </template>
        <FieldTree
          :fields="fieldTree"
          @select="onFieldSelect"
        />
      </el-popover>
      
      <!-- Filter 选择 -->
      <el-select v-model="selectedFilter" placeholder="Filter" clearable>
        <el-option label="(无)" value="" />
        <el-option label="money" value="money" />
        <el-option label="chinese_money" value="chinese_money" />
        <el-option label="date" value="date" />
        <el-option label="datetime" value="datetime" />
      </el-select>
      
      <!-- 操作按钮 -->
      <el-button size="small" @click="insertBinding">插入绑定</el-button>
      <el-button size="small" @click="insertStatic">插入静态</el-button>
    </div>
  </el-form-item>
</el-form>
```

### 4.3 字段树数据获取

在编辑器初始化时，根据 `docType` 获取对应的字段树：

```ts
const fieldTree = computed(() => {
  const trees: Record<string, FieldNode[]> = {
    contract: [
      { key: 'form', path: 'form', label: '表单数据', children: [
        { key: 'title', path: 'form.title', label: '合同标题', type: 'string' },
        { key: 'contractNo', path: 'form.contractNo', label: '合同编号', type: 'string' },
        { key: 'customerName', path: 'form.customerName', label: '客户名称', type: 'string' },
        { key: 'amount', path: 'form.amount', label: '合同金额', type: 'number' },
        // ...
      ]},
      { key: 'contract', path: 'contract', label: '合同详情', children: [
        // ...
      ]},
    ],
    // ...
  }
  return trees[form.docType] || []
})
```

## 五、文件改动

| 文件 | 改动 | 行数预估 |
|---|---|---|
| `frontend/src/components/admin/print/FieldTree.vue` (新) | 字段树组件 | 80 |
| `frontend/src/components/admin/print/PropertyPanel.vue` | 增加数据绑定区域 | +100 |
| `frontend/src/views/admin/AdminPrintTemplateEditor.vue` | 传递 fieldTree 给 PropertyPanel | +20 |
| `frontend/src/components/admin/print/fieldData.ts` (新) | 预置字段树数据 | 120 |

后端：**0 改动**（完全复用现有的 `/print/preview-schema`）

## 六、验收标准

1. 打开 `/admin/print-template/editor/2`（合同模板）
2. 切到 🎨 可视化 tab
3. 点选一个 text 组件
4. 右侧属性面板显示"数据绑定"区域
5. 点击字段树下拉 → 看到 form.title / form.contractNo 等字段
6. 选择 `form.contractNo` → 选择 filter `money`
7. 点击"插入绑定" → 文本内容自动更新为 `{{ contract.contractNo | money }}`
8. 右侧实时预览 iframe 显示绑定后的数据
9. 保存后刷新页面，绑定关系保持

## 七、零破坏验证

- ✅ M3 阶段 1 的 JSON 模式完全保留
- ✅ M3 阶段 2 的 grid 模板继续工作
- ✅ M3 阶段 3 的可视化设计器完全保留
- ✅ M3 阶段 4 的 Excel/Word 导入继续工作
- ✅ 4 套预置模板可加载到可视化
- ✅ 实时预览 iframe 正常工作
- ✅ 业务数据下拉、基础信息、撤销/保存/发布 全部正常

## 八、后续可选增强（M2+）

- [ ] 条件表达式（IF / ELSE）
- [ ] 循环表达式（FOR）
- [ ] 聚合函数（SUM / AVG / COUNT）
- [ ] 跨表关联（form.customer.name）
- [ ] 自定义 filter
- [ ] 字段树搜索高亮
- [ ] 字段类型图标
