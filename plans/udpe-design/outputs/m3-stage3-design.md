# M3 阶段 3 — V1 模板设计器（拖拽式画布编辑器）

> **状态**: 📐 设计阶段
> **作者**: Codex (claude-sonnet-4)
> **日期**: 2026-06-28
> **前置**: M3 阶段 1 (JSON 编辑器 + 实时预览), M3 阶段 2.1 (grid block)
> **任务**: 在 M3 阶段 1 的基础上增加可视化设计器 V1，让业务方不需要手写 JSON

## 一、目标与边界

### 1.1 目标
让 80% 的常见模板（title / text / spacer / line / 简单 grid）能通过拖拽式画布创建，**不要求手写 JSON**。

### 1.2 范围（V1）
- ✅ 7 种组件可拖拽插入：title / text / spacer / line / table / grid / pagebreak
- ✅ 画布上点击组件进入编辑态
- ✅ 右侧属性面板改基础属性（text/fontSize/align/color/bold/colspan 等）
- ✅ 组件上下重排（↑/↓ 按钮，不上完整拖拽）
- ✅ 删除组件
- ✅ 画布 ↔ JSON 双向同步
- ✅ 保留 JSON 编辑模式（tab 切换）

### 1.3 范围外（V2+）
- ❌ 自由坐标定位 / 像素级拖拽（M4+）
- ❌ 撤销/重做（M4+）
- ❌ 嵌套 grid（M4+）
- ❌ 数据绑定 UI 点选字段（M4+）
- ❌ 组件库扩展（M4+）

## 二、UI 布局

```
┌────────────────────────────────────────────────────────────────────┐
│  ← 返回列表 | 编辑模板 · 合同摘要 | 已发布 v1 | ↺撤销 保存  │ tab 切换：
│                                                  │ [📝JSON] [🎨可视化] │
├──────────┬─────────────────────────────┬───────────────────────────┤
│ 基础信息 │ 顶部 tab:  [📝 JSON] [🎨 可视化]            │ 实时预览  │
│  code    │ ─────────────────────────────  │ (iframe)        │
│  name    │ 📝 JSON 模式：                 │                 │
│  业务类型 │   <textarea 深色主题>          │                 │
│  纸型    │                                 │                 │
│  方向    │ 🎨 可视化模式：                 │                 │
│  描述    │   ┌──────────────┐              │                 │
│ ────── │   │ ①组件库 │ ②画布 │ ③属性│  │                 │
│ 数据绑定 │   │  ┌──────┐┌──────┐        │  │                 │
│  预览数据│   │  │Title││ Text │        │  │                 │
│  提示词  │   │  └──────┘└──────┘        │  │                 │
│         │   │  ┌──────┐┌──────┐        │  │                 │
│         │   │  │ Grid││Table │        │  │                 │
│         │   │  └──────┘└──────┘        │  │                 │
│         │   │  画布（垂直堆叠）          │  │                 │
│         │   │  ┌─────────────────┐      │  │                 │
│         │   │  │ 标题  ↑↓ ✕      │      │  │                 │
│         │   │  ├─────────────────┤      │  │                 │
│         │   │  │ 文本  ↑↓ ✕      │      │  │                 │
│         │   │  └─────────────────┘      │  │                 │
│         │   └──────────────┘              │                 │
│         │   属性面板（点选后）             │                 │
│         │   ┌──────────────┐              │                 │
│         │   │ 字号: [ 14 ] │              │                 │
│         │   │ 颜色: [#000] │              │                 │
│         │   │ 对齐: ◯左中右 │              │                 │
│         │   └──────────────┘              │                 │
└──────────┴─────────────────────────────┴───────────────────────────┘
```

## 三、数据流

```
┌──────────────────────────────────────────────────────────────┐
│                  schemaJson (body: Component[])              │
│           ↑ 写                    ↑ 读                      │
│  JSON textarea          VisualCanvas + PropertyPanel        │
│  (onJsonChange)         (onVisualChange)                    │
│           ↓                    ↓                            │
│     editorStore (reactive)                                 │
│           ↓                                                │
│     防抖 600ms → /print/preview-schema                     │
└──────────────────────────────────────────────────────────────┘
```

- **单一数据源**: `editorStore.schemaJson.body`（reactive）
- **JSON 模式**: 双向绑定 `<textarea>` ↔ store
- **可视化模式**: 
  - 画布渲染 `body.map((c, i) => <CanvasItem component={c} index={i} selected={i===selectedIdx} ...>)`
  - 点选 → `selectedIdx = i`
  - 改属性 → 改 `body[i]` → store reactive → 画布和 JSON tab 同步更新
  - 拖入新组件 → `body.splice(selectedIdx+1, 0, newComponent)`
  - 删除 → `body.splice(i, 1)`
  - 上移/下移 → `body.splice(i, 1); body.splice(i±1, 0, c)`

## 四、组件 schema 扩展

每个组件新增 `id` 字段（前端用，存盘前剔除），用于画布追踪：

```ts
interface BaseComp {
  id: string  // 临时 ID (uuid), 保存前剔除
  type: 'title' | 'text' | 'spacer' | 'line' | 'grid' | 'table' | 'pagebreak'
  // ... 类型特定字段
}
```

**V1 不实现**: 嵌套结构（grid 内 cell 单独编辑），只实现"一维 body 列表"。

## 五、7 个组件的 V1 简化属性面板

| 组件 | 字段 | 属性面板 |
|---|---|---|
| `title` | text, fontSize, align, color | 文本 / 字号 / 对齐 / 颜色 |
| `text` | text, fontSize, align, color, bold | 文本 / 字号 / 对齐 / 颜色 / 加粗 |
| `spacer` | height | 高度(mm) |
| `line` | color | 颜色 |
| `grid` | colCount, rows, border, borderColor | 列数 / 边框开 / 边框色（rows 暂用 grid 模板插入） |
| `table` | bind, columns | 列定义（暂不实现 UI，仅占位） |
| `pagebreak` | - | (无属性) |

**grid 简化**: V1 不让用户可视化编辑 rows 内部结构，仅在选中 grid 时显示"行数: X / 列数: Y / 边框: 开"。新增 row / col 通过属性面板的两个按钮："+ 添加行" / "+ 添加列"（会重置 rows）。

## 六、文件改动

| 文件 | 改动 | 行数预估 |
|---|---|---|
| `frontend/src/views/admin/AdminPrintTemplateEditor.vue` | 重构为 tab 切换 + 引入新子组件 | +200 |
| `frontend/src/components/admin/print/ComponentPalette.vue` (新) | 左侧组件库 | 80 |
| `frontend/src/components/admin/print/VisualCanvas.vue` (新) | 中央画布 | 200 |
| `frontend/src/components/admin/print/PropertyPanel.vue` (新) | 右侧属性面板 | 250 |
| `frontend/src/components/admin/print/CanvasItem.vue` (新) | 单个组件的可视化表示 | 120 |
| `frontend/src/components/admin/print/compTemplates.ts` (新) | 7 个组件的默认 schema 模板 | 50 |

后端：**0 改动**（v1 完全复用 M3 阶段 1 的 `/print/preview-schema`）。

## 七、保留功能

- ✅ JSON 模式（v1 的 textarea 完全保留）
- ✅ 实时预览（v1 的 iframe 完全保留）
- ✅ 加载预置（v1 的 4 套 contract/invoice/expense/reimbursement 预置）
- ✅ 业务数据下拉
- ✅ 保存/发布/撤销
- ✅ 离开保护

## 八、验收

1. 打开 `/admin/print-template/editor/2`（合同模板）
2. 切到 🎨 可视化 tab
3. 看到画布上 6+ 个组件的预览（title/text/spacer/line/table）
4. 点选一个 text 组件，右侧属性面板显示该组件字段
5. 改字号 12→16，画布 + JSON tab 同步更新
6. 拖入新组件，JSON tab 同步增加
7. 删除一个组件，JSON tab 同步删除
8. 保存，刷新页面，看到保存的修改

## 九、不在 M3 阶段 3 范围

- 拖拽排序（用 ↑↓ 按钮代替）
- 撤销/重做
- 复杂 grid rows 可视化（先用模板插入）
- 组件嵌套
- 撤销（用 isDirty + resetForm 兜底）
