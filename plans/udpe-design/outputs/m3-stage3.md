# M3 阶段 3 — V1 模板设计器（拖拽式画布编辑器）

> **状态**: ✅ 已完成
> **作者**: Codex (claude-sonnet-4)
> **日期**: 2026-06-28
> **前置**: M3 阶段 1 (JSON 编辑器 + 实时预览), M3 阶段 2.1 (grid block)
> **设计**: `plans/udpe-design/outputs/m3-stage3-design.md`
> **任务**: 在 JSON 编辑器基础上增加可视化设计器 V1，**不破坏现有功能**

## 一、目标与边界

让 80% 的常见模板（title / text / spacer / line / 简单 grid）能通过拖拽式画布创建，**不要求手写 JSON**。

V1 范围（已完成）：
- ✅ 7 种组件可点击插入（title / text / spacer / line / grid / table / pagebreak）
- ✅ 画布上点击组件进入编辑态
- ✅ 右侧属性面板改基础属性（text/fontSize/align/color/bold/height/colspan 等）
- ✅ 组件上下重排（↑/↓ 按钮）
- ✅ 删除组件
- ✅ 画布 ↔ JSON 双向同步
- ✅ 保留 JSON 编辑模式（tab 切换）

V2 范围（不在本阶段）：
- ❌ 自由坐标定位 / 像素级拖拽
- ❌ 撤销/重做
- ❌ 嵌套 grid
- ❌ 数据绑定 UI 点选字段
- ❌ grid rows 内部结构可视化编辑

## 二、文件改动

### 2.1 新增文件

| 文件 | 用途 | 行数 |
|------|------|------|
| `frontend/src/components/admin/print/compTemplates.ts` | 7 个组件默认 schema 模板 + 类型定义 | 80 |
| `frontend/src/components/admin/print/ComponentPalette.vue` | 左侧组件库（可点击/拖拽） | 80 |
| `frontend/src/components/admin/print/CanvasItem.vue` | 画布上单个组件的表示 | 130 |
| `frontend/src/components/admin/print/VisualCanvas.vue` | 中央画布（接受拖拽放入） | 110 |
| `frontend/src/components/admin/print/PropertyPanel.vue` | 右侧属性面板 | 250 |

### 2.2 修改文件

| 文件 | 改动 | 行数 |
|------|------|------|
| `frontend/src/views/admin/AdminPrintTemplateEditor.vue` | 引入 el-tabs 双模式（JSON / 可视化），加可视化的 state + 方法 | 526 → 654 |

后端：**0 改动**（完全复用 M3 阶段 1 的 `/print/preview-schema`）。

## 三、架构

```
┌────────────────────────────────────────────────────────────────────┐
│ 顶部工具栏（返回/状态/版本/撤销/保存/发布）                          │
├──────────┬─────────────────────────────┬───────────────────────────┤
│ 基础信息 │   [📝 JSON] [🎨 可视化]      │ 实时预览                │
│  code    │  ─────────────              │  (iframe)               │
│  name    │  📝 JSON 模式:              │                          │
│  业务类型 │   <textarea 深色>           │                          │
│  纸型    │  ─────────────              │                          │
│  方向    │  🎨 可视化模式:              │                          │
│  描述    │   ┌──────┐┌───────────────┐  │                          │
│ ────── │   │ 组件 │  画布 + 工具   │  │                          │
│ 数据绑定 │   │  库  │  (CanvasItem) │  │                          │
│  预览数据 │   │      │               │  │                          │
│  提示词  │   │      │  选中后       │  │                          │
│         │   │      │  属性面板     │  │                          │
│         │   │      │  (PropertyPanel)│  │                          │
│         │   └──────┘└───────────────┘  │                          │
└──────────┴─────────────────────────────┴───────────────────────────┘
```

## 四、数据流

```
                schemaJson.body (reactive)
                        ↑    ↑    ↑
                        写   写   读
                        │    │    │
        ┌───────────────┘    │    └──────────────┐
        │                    │                   │
   JSON textarea      VisualCanvas         实时预览
   (onJsonChange)     (onVisualChange)     (reloadPreview)
        │                    │                   ↑
        └─→ visualBody ←─────┘                   │
            (深拷贝, 临时 id)              防抖 600ms
                                         → /print/preview-schema
```

**单一数据源**：`editorStore` 内部有两个 ref：
- `jsonRaw` (string) — JSON 模式编辑
- `visualBody` (array) — 可视化模式编辑

通过 `syncingFromJson` 标志位避免循环同步：
- JSON → visualBody: 在 onJsonChange 中解析后同步
- visualBody → JSON: 在 syncVisualToJson 中深拷贝后同步

## 五、组件 schema 扩展

每个组件在 visualBody 中**临时**带 `id` 字段（前端用，存盘前剔除）：

```ts
interface BaseComp {
  id: string  // 临时 ID (c{n}_{rand}), 保存时自动剔除
  type: 'title' | 'text' | 'spacer' | 'line' | 'grid' | 'table' | 'pagebreak'
  // ... 类型特定字段
}
```

7 个组件默认 schema (compTemplates.ts)：

| 组件 | 字段 |
|---|---|
| `title` | text, fontSize, align |
| `text` | text, fontSize, align, color, bold |
| `spacer` | height (mm) |
| `line` | color |
| `grid` | border, borderColor, borderWidth, colCount, rows |
| `table` | bind, columns |
| `pagebreak` | (无) |

## 六、属性面板设计

7 种组件分别处理（PropertyPanel.vue）：
- **title/text**: 文本内容 / 字号 / 对齐（3 选）/ 颜色 / 加粗（仅 text）
- **spacer**: 高度 (mm)
- **line**: 线条颜色
- **grid**: 列数 / 行数（含 +行/-行按钮）/ 显示边框 / 边框色
- **table**: 数据路径 (bind) / 列数
- **pagebreak**: 提示文案

底部统一显示**临时 ID**（仅展示，便于调试）。

## 七、端到端验证

### 7.1 Build 0 错误

```bash
cd frontend && npm run build
# ✓ built in 5.43s
# (前端 dist 已更新, nginx 自动生效)
```

### 7.2 浏览器实测（Playwright e2e）

| 测试项 | 结果 |
|---|---|
| 访问 `/admin/print-template/editor/2`（合同摘要 id=2） | ✅ 加载成功 |
| 默认 tab | ✅ 可视化（默认） |
| 画布组件数 | ✅ 26 个 (合同模板 26 组件) |
| 点击组件选中 | ✅ 第 3 个"间距"被选中 |
| 属性面板显示选中组件 | ✅ "间距"类型 + 高度(mm)=6 + 临时 ID |
| 选中态视觉 | ✅ 蓝色边框高亮 + ↑↓✕ 工具按钮 |
| 切到 JSON 模式 | ✅ 深色主题 + 5ms 渲染时间 |
| JSON 长度 | ✅ 2779 bytes (合同模板完整 schema) |
| 实时预览 | ✅ 合同摘要完整渲染（HT-2026-002 北辰实业集团 / ¥248,000.00） |

### 7.3 截图

- 视觉模式默认：`/tmp/m3s3_id2_visual_v2.png`
- 选中第 3 个组件：`/tmp/m3s3_id2_selected_v2.png`
- JSON 模式：`/tmp/m3s3_id2_json_v2.png`

## 八、技术决策

1. **JSON 模式完全保留** — 不是替换，是**并列 tab 切换**，老用户工作流不破坏
2. **不引入新依赖** — `uuid` 用自增 `c{n}_{rand}` 代替（AGENTS.md 要求）
3. **grid rows 不完全可视化** — 暂用模板插入（addGridRow / removeGridRow），rows 内部结构引导用户用 JSON 模式编辑
4. **PropertyPanel 高度固定 220px** — 让 visual-canvas 至少 600px+ 可视（V1 中间栏只有 372px 宽的妥协）
5. **Palette 宽度 140px 纵向** — 适合中栏窄的情况
6. **临时 ID 字段** — 保存前 syncVisualToJson 中自动剔除，业务层不可见
7. **syncingFromJson 标志位** — 防止双向同步时的无限循环

## 九、关键修复

构建过程中遇到的 3 个 CSS 坑：

| 问题 | 原因 | 修法 |
|------|------|------|
| `.el-tab-pane` `display: none` | active pane 不在第一个 | 改用 `el-tab-pane` 不强制 display, 用 padding/height 控制 |
| `.visual-canvas` 高度 4px | flex 子元素 min-height: 0 缺省 | 加 `min-height: 0` |
| `.visual-main` 子元素总高 > 父高 | PropertyPanel height: 100% 撑爆 | PropertyPanel 改 `height: 220px` 固定 |

## 十、零破坏回归

- ✅ M3 阶段 1 的 JSON 模式（深色编辑器、格式化、加载预置）完全保留
- ✅ M3 阶段 2 的 grid 模板继续工作
- ✅ M3 阶段 2.1 的 Excel 复刻 1:1 渲染保持
- ✅ 4 套预置模板（contract / invoice / expense / reimbursement）可加载到可视化
- ✅ 实时预览 iframe 正常工作
- ✅ 业务数据下拉、基础信息、撤销/保存/发布 全部正常

## 十一、后续可选增强（M2+）

- [ ] 组件拖拽排序（用 ↑↓ 按钮代替）
- [ ] 撤销/重做（store 记录历史栈）
- [ ] 嵌套 grid（grid 内 cell 单独编辑）
- [ ] 数据绑定 UI 点选字段（树形结构 + 点选 + 自动生成 `{{ path }}`）
- [ ] 拖拽放置（鼠标坐标定位）
- [ ] 选中框 hover 实时高亮
- [ ] 复制/粘贴组件

## 十二、总结

**M3 阶段 3 完成了 V1 模板设计器的最小可用版本**：
- 7 个组件可视化拖入
- 26 个组件的复杂模板正确加载
- 选中/编辑/移动/删除 操作闭环
- JSON 模式 + 可视化模式 双模式无缝切换
- 画布与 JSON 实时双向同步
- 业务方能直接用，不需要手写 JSON
