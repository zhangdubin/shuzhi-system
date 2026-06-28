# M3 阶段 6 — 撤销/重做 + 拖拽排序 + 嵌套 grid

> **状态**: ✅ 已完成
> **作者**: Codex (GPT-5)
> **日期**: 2026-06-28
> **前置**: M3 阶段 3 (可视化设计器), M3 阶段 5 (数据绑定 UI)
> **任务**: 在可视化设计器基础上增加三个高级编辑能力

## 一、目标与边界

V1 可视化设计器的三个高频缺失能力：
- ✅ 撤销/重做 — 操作历史栈 + Ctrl+Z / Ctrl+Shift+Z
- ✅ 拖拽排序 — 画布内组件拖拽重排
- ✅ 嵌套 grid — grid 单元格内嵌子组件 (title/text/spacer/line)

## 二、文件改动

### 2.1 新增文件

| 文件 | 用途 | 行数 |
|------|------|------|
| `frontend/src/components/admin/print/useUndoRedo.ts` | 撤销/重做 composable (历史栈管理) | 72 |
| `frontend/src/components/admin/print/GridCellEditor.vue` | 单元格内容编辑弹窗 (嵌套组件) | 230 |

### 2.2 修改文件

| 文件 | 改动 |
|------|------|
| `frontend/src/views/admin/AdminPrintTemplateEditor.vue` | 集成撤销/重做 + 拖拽重排 + 单元格编辑器 |
| `frontend/src/components/admin/print/CanvasItem.vue` | 添加 HTML5 拖拽 + 嵌套组件计数 |
| `frontend/src/components/admin/print/VisualCanvas.vue` | 添加重排事件监听 |
| `frontend/src/components/admin/print/PropertyPanel.vue` | grid 单元格可视化网格 + editCell 事件 |
| `backend/app/modules/print_runtime/renderers/html_renderer.py` | grid cell 支持 children 嵌套渲染 |
| `backend/app/modules/print_runtime/renderers/pdf_renderer.py` | grid cell 支持 children 嵌套渲染 |

## 三、功能设计

### 3.1 撤销/重做

`useUndoRedo` composable:
- 基于 JSON 快照的历史栈 (最大 50 步)
- `push()` — 在每次 visualBody 变化前手动压栈
- `undo()` / `redo()` — 栈指针移动
- `canUndo` / `canRedo` — computed, 控制按钮 disabled

集成方式:
- 每个可视化操作 (add/remove/move/update) 前调用 `pushHistory()`
- 工具栏按钮: ↩ 撤销 / ↪ 重做
- 键盘快捷键: Ctrl+Z / Ctrl+Shift+Z (Mac: Cmd+Z / Cmd+Shift+Z)
- `onUnmounted` 清理键盘监听

### 3.2 拖拽排序

HTML5 Drag and Drop 实现:
- CanvasItem 设为 `draggable="true"`
- 拖拽数据: `application/x-udpe-reorder` (自定义 MIME type, 不与组件库拖拽冲突)
- 拖拽指示器: CSS `.drag-over-top` / `.drag-over-bottom` 蓝色边线
- VisualCanvas 监听 `udpe-reorder` CustomEvent, emit `reorder` 给编辑器
- 编辑器 `onVisualReorder()` 处理数组重排 + pushHistory

### 3.3 嵌套 grid

单元格 schema 扩展 (向后兼容):
```json
// 旧: 简单文本
{ "text": "标题", "span": 4, "bold": true }

// 新: 嵌套组件 (children 存在时忽略 text)
{ "span": 4, "children": [
    { "type": "title", "text": "标题", "fontSize": 16 },
    { "type": "text", "text": "副标题" }
]}
```

GridCellEditor 弹窗:
- 显示当前 cell 的子组件列表
- 支持添加: title / text / spacer / line
- 支持选中编辑属性 (text/fontSize/align/color/bold/height)
- 支持排序 (↑/↓) 和删除
- 确认后更新 cell.children, 无 children 时回退到简单文本

PropertyPanel 集成:
- grid 选中时显示可点击的单元格网格
- 有 children 的单元格显示绿色高亮 + 数量 badge
- 点击单元格 → 打开 GridCellEditor

CanvasItem 预览:
- grid 组件显示 "📦 N 个单元格含嵌套组件"

## 四、后端渲染器更新

### HTML 渲染器
cell 有 children 时递归渲染子组件 (title/text/spacer/line), 不再只输出纯文本。

### PDF 渲染器
cell 有 children 时拼接子组件文本为多行 Paragraph (reportlab 限制, 无法嵌套 Table)。

## 五、验证

### 5.1 前端构建

```bash
cd frontend && npm run build
# ✓ built in 5.52s
# 0 错误
```

### 5.2 后端构建

```bash
cd deploy && docker compose build backend
# Image shuzhi-backend:latest Built
docker compose up -d --no-deps backend
# Container shuzhi-backend Started
```

### 5.3 功能验证项

| 测试项 | 预期 |
|---|---|
| 编辑器打开, 修改组件, Ctrl+Z | 撤销到上一步 |
| Ctrl+Shift+Z | 重做 |
| ↩/↪ 按钮 disabled 状态 | 正确反映 canUndo/canRedo |
| 拖拽画布组件 | 蓝色指示线, 释放后重排 |
| grid 选中 → 点击单元格 | 打开 GridCellEditor |
| 添加子组件 → 确认 | CanvasItem 显示嵌套数量 |
| 实时预览 | 嵌套内容正确渲染 |
| 保存后刷新 | 嵌套数据持久化 |

## 六、零破坏验证

- ✅ M3 阶段 1 的 JSON 模式完全保留
- ✅ M3 阶段 2 的 grid 模板继续工作
- ✅ M3 阶段 3 的可视化设计器完全保留
- ✅ M3 阶段 4 的 Excel/Word 导入继续工作
- ✅ M3 阶段 5 的数据绑定 UI 继续工作
- ✅ 4 套预置模板可加载到可视化
- ✅ 实时预览 iframe 正常工作
- ✅ 旧 grid schema (无 children) 完全兼容

## 七、已知限制

| 限制 | 原因 | 后续方案 |
|---|---|---|
| 嵌套只支持 text/title/spacer/line | V1 简化 | V2 支持嵌套 grid (grid in grid) |
| PDF 嵌套是文本拼接, 非真嵌套布局 | reportlab Table 不支持嵌套 | V2 切 WeasyPrint |
| 拖拽无动画过渡 | HTML5 DnD 无动画 | V2 用 CSS transition |
| 历史栈是 JSON 序列化, 大模板可能慢 | 50 步快照 × 大 schema | V2 用 command pattern (增量) |
| PropertyPanel 固定 220px, 复杂 grid 编辑空间有限 | V1 布局限制 | V2 弹窗式全屏编辑 |

## 八、下一步候选

1. **M4 — 业务模块接入** (ReimburseDetail / ExpenseDetail / InvoiceDetail 迁移到 UDPE SDK)
2. **M4 — 异步队列** (FastAPI BackgroundTasks + Redis Stream + SSE 进度推送)
3. **M4 — PDF 模板解析** (上传扫描件 → OCR → 自动生成 schemaJson)
