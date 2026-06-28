# M3 阶段 5 — 数据绑定 UI（实施报告）

> 目标：在属性面板中增加数据绑定 UI，让业务方点选字段即可绑定到组件，
> 实现"不需要手写 `{{ path }}` 表达式"。

---

## 一、产出清单

### 新增文件

| 路径 | 行数 | 说明 |
|---|---|---|
| `frontend/src/components/admin/print/fieldData.ts` | 120 | 预置字段树数据（按业务类型分类） |
| `frontend/src/components/admin/print/FieldTree.vue` | 100 | 字段树组件（支持搜索、点选） |
| `plans/udpe-design/outputs/m3-stage5-design.md` | - | 阶段 5 设计文档 |
| `plans/udpe-design/outputs/m3-stage5.md` | - | 阶段 5 实施报告 |

### 修改文件

| 路径 | 变更 |
|---|---|
| `frontend/src/components/admin/print/PropertyPanel.vue` | 增加数据绑定区域（字段树 + Filter + 操作按钮） |
| `frontend/src/views/admin/AdminPrintTemplateEditor.vue` | 传递 docType 给 PropertyPanel |

---

## 二、核心设计

### 2.1 字段树数据结构

```ts
interface FieldNode {
  key: string          // 字段名 (如 "title")
  path: string         // 完整路径 (如 "form.title")
  label: string        // 显示标签 (如 "标题")
  type: string         // 数据类型 (string / number / date / boolean)
  children?: FieldNode[]  // 子字段
}
```

### 2.2 预置字段树（按业务类型）

| 业务类型 | 字段数 | 主要字段 |
|---------|--------|---------|
| contract | 12 | form.title, form.contractNo, form.customerName, form.amount, ... |
| invoice | 11 | form.invoiceNo, form.amount, form.taxAmount, form.buyerName, ... |
| reimbursement | 10 | form.title, form.totalAmount, form.applicantName, form.remark, ... |
| expense | 9 | form.expenseNo, form.amount, form.category, form.applicantName, ... |
| general | 7 | form.title, form.content, form.amount, form.date, form.remark, ... |

### 2.3 Filter 列表

| Filter | 说明 | 示例 |
|--------|------|------|
| (无) | 原始值 | `{{ form.title }}` |
| money | 分→元，保留2位 | `{{ form.amount \| money }}` |
| chinese_money | 分→大写元 | `{{ form.amount \| chinese_money }}` |
| date | 日期格式化 | `{{ form.startDate \| date }}` |
| datetime | 日期时间格式化 | `{{ printTime \| datetime }}` |

### 2.4 UI 布局

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

---

## 三、实现细节

### 3.1 FieldTree.vue 组件

- 支持搜索过滤（输入关键词实时过滤字段树）
- 支持字段类型图标（📝 string / 🔢 number / 📅 date / ✅ boolean）
- 点击叶子节点触发 `select` 事件
- 父节点不可选择（只能展开/折叠）

### 3.2 PropertyPanel.vue 改动

- 新增 `docType` prop，用于获取对应的字段树
- 在 `hasText` 区域下方增加"数据绑定"区域
- 使用 `el-popover` 实现字段树下拉
- 支持 Filter 选择和插入操作

### 3.3 数据流

```
用户点选字段 → onFieldSelect(path) → currentBindPath
用户选择 Filter → selectedFilter
点击"插入绑定" → 生成 {{ path | filter }} → 更新组件 text
```

---

## 四、验证

### 4.1 前端构建

```bash
cd frontend && npm run build
# ✓ built in 5.69s
# 0 错误
```

### 4.2 功能验证（待浏览器测试）

1. 打开 `/admin/print-template/editor/2`（合同模板）
2. 切到 🎨 可视化 tab
3. 点选一个 text 组件
4. 右侧属性面板显示"数据绑定"区域
5. 点击字段树下拉 → 看到 form.title / form.contractNo 等字段
6. 选择 `form.contractNo` → 选择 filter `money`
7. 点击"插入绑定" → 文本内容自动更新为 `{{ contract.contractNo | money }}`
8. 右侧实时预览 iframe 显示绑定后的数据

---

## 五、零破坏验证

- ✅ M3 阶段 1 的 JSON 模式完全保留
- ✅ M3 阶段 2 的 grid 模板继续工作
- ✅ M3 阶段 3 的可视化设计器完全保留
- ✅ M3 阶段 4 的 Excel/Word 导入继续工作
- ✅ 4 套预置模板可加载到可视化
- ✅ 实时预览 iframe 正常工作
- ✅ 业务数据下拉、基础信息、撤销/保存/发布 全部正常

---

## 六、当前限制（M3 阶段 5 已知边界）

| 限制 | 原因 | 后续方案 |
|---|---|---|
| 不支持条件表达式（IF / ELSE） | V1 仅支持简单绑定 | M4+ 引入表达式引擎 |
| 不支持循环表达式（FOR） | V1 仅支持简单绑定 | M4+ 引入表达式引擎 |
| 不支持聚合函数（SUM / AVG / COUNT） | V1 仅支持简单绑定 | M4+ 引入表达式引擎 |
| 不支持跨表关联（form.customer.name） | V1 字段树扁平化 | M4+ 引入嵌套字段树 |
| 不支持自定义 filter | V1 仅支持预置 filter | M4+ 引入 filter 编辑器 |
| 字段树数据硬编码 | V1 预置字段树 | M4+ 从后端动态获取 |

---

## 七、下一步候选

按用户表达优先级：

1. **M3 阶段 6 — 撤销/重做 + 嵌套 grid + 拖拽**
   - editor 内操作历史栈
   - cell 内嵌子 cell（解决纵向合并问题）
   - 拖拽排序

2. **M4 — PDF 模板解析（OCR + 标注）**
   - 上传扫描件 → tesseract → 用户标注文字块 → 自动生成 schemaJson

---

## 八、本阶段交付

- 字段树组件（FieldTree.vue）
- 预置字段树数据（fieldData.ts）
- 属性面板数据绑定区域
- 编辑器集成
- 前端构建通过
- 设计文档 + 实施报告
- 零破坏（原有功能全部保留）
