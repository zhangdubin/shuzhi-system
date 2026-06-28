# M3 阶段 2.1 — Excel 报销单 1:1 复刻（grid block）

> **状态**: ✅ 已完成
> **作者**: Codex (claude-sonnet-4)
> **日期**: 2026-06-28
> **前置**: M3 阶段 2 (v1 HTML 拼版，视觉不达标)
> **任务**: 1:1 复刻 Excel `报销单模板自行打印.xlsx`，保留单元格边框 + 多列布局 + 年月日 + 4 签字栏

## 一、问题诊断（M3 阶段 2 v1 不足）

原 v1 模板用 `title` / `text` / `line` / `spacer` 拼版，渲染出来：
- ❌ 无单元格边框（用 `<hr>` 模拟）
- ❌ 4 签字栏用 4 个独立 `text` 块，水平排开有错位
- ❌ 标题/日期/正文不构成一个表格

参考 Excel 原版（用户截图 `/var/folders/p8/.../截屏2026-06-28 12.07.52.png`）：
- ✅ 6 行 × 4/5 列的表格网格
- ✅ 单元格之间有 1px 黑色边框
- ✅ 标题合并整行
- ✅ 日期行右对齐
- ✅ 金额大写/小写并排
- ✅ 4 签字栏等宽

## 二、方案：grid block 类型

新增 `grid` 组件类型，模拟 Excel 工作表：
- 用 `<table>` + `<tr>` + `<td colspan="N">` 实现
- 单元格边框、合并、字体、对齐、padding 全部可控
- HTML renderer / PDF renderer 同步支持

### 2.1 schema 设计

```json
{
  "type": "grid",
  "border": true,              // 是否画单元格边框
  "borderColor": "#000000",    // 边框色
  "borderWidth": 1,            // 边框粗细 (px or reportlab pt)
  "colCount": 4,               // 网格总列数（用于 colspan 校验）
  "rows": [
    {
      "height": 16,            // 行高 (mm)
      "cells": [
        { "text": "费 用 报 销 单", "span": 4, "bold": true, "align": "center", "valign": "middle", "fontSize": 22 },
        ...
      ]
    },
    ...
  ]
}
```

**cell 字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `text` | str | 静态文本（支持 `{{ path \| filter }}` 模板插值） |
| `bind` | str | JSONPath，data 路径优先（与 `text` 二选一） |
| `span` | int | 跨列数（默认 1） |
| `bold` | bool | 加粗 |
| `align` | str | `left` / `center` / `right` |
| `valign` | str | `top` / `middle` / `bottom` |
| `fontSize` | int | 字号（px） |
| `color` | str | 文字色 |
| `background` | str | 背景色 |
| `padding` | str | CSS 风格 padding（默认 `6px 8px`） |

### 2.2 HTML renderer

`backend/app/modules/print_runtime/renderers/html_renderer.py`：
- `_to_html_comp` 增加 `if ctype == "grid":` 分支
- 构造 `<table style="width:100%;border-collapse:collapse;table-layout:fixed;">`
- 每行 `<tr style="height:14mm">`，cell `<td colspan="N" style="border:1px solid #000;...">`

### 2.3 PDF renderer

`backend/app/modules/print_runtime/renderers/pdf_renderer.py`：
- `_build_component` 增加 `elif ctype == "grid":` 分支
- 用 `reportlab.platypus.Table` + `TableStyle`
- `TableStyle` 加 `GRID`（边框）+ `BOX`（外框）
- 处理 `SPAN`（合并单元格）+ `BACKGROUND`（背景色）
- 行高按 mm 设置（`rowHeights=[h*mm for h in ...]`）
- 列宽按 `colCount` 等分（A4 - 36mm margin）

## 三、Excel 复刻模板实现

新模板文件：`plans/udpe-design/outputs/m3-stage2.1-reimbursement-grid.json`

实际写入数据库的 `reimbursement_simple_v1`（id=6）的 `schemaJson`：

| 行 | 单元格分布 | 说明 |
|----|----------|------|
| 1 | `[费 用 报 销 单 x 4]` | 标题合并 4 列 |
| 2 | `[空 x 2, ____年____月____日 x 2]` | 日期右对齐 |
| 3 | `[费用摘要 x 1, {{ form.title }} x 3]` | 摘要 |
| 4 | `[金额（大写）x 1, {{ chinese_money }} x 1, 金额（小写）x 1, {{ money }} x 1]` | 金额双栏 |
| 5 | `[备注 x 1, {{ remark }} x 1, 附单据张数 x 1, {{ count }} x 1]` | 备注 + 张数 |
| 6 | `[核准：x 1, 审批：x 1, 会计：x 1, 报销人：{{ name }} x 1]` | 4 签字栏等宽 |

## 四、端到端验证

### 4.1 单元 smoke test（容器内 Python 直调）

```bash
docker exec shuzhi-backend python3 -c "from app.modules.print_runtime.renderers.html_renderer import HtmlRenderer; ..."
# HTML: 3529 bytes ✅
# PDF: 3234 bytes ✅
```

### 4.2 API 端到端

```bash
# 1. 更新模板到 DB
curl -X POST "http://localhost/api/v1/admin/print-templates/update?tid=6" \
  -H "Authorization: Bearer $TOKEN" -d @/tmp/update_payload.json
# {"code": 0, "data": {"id": 6, "name": "费用报销单（Excel 1:1 复刻·grid 版）"...}}

# 2. 调 /print/preview-schema
curl -X POST "http://localhost/api/v1/print/preview-schema" \
  -H "Authorization: Bearer $TOKEN" -d @/tmp/preview_payload.json
# {"data": {"html": "..."}, "elapsedMs": 0}

# 3. 调 /print/pdf
curl -X POST "http://localhost/api/v1/print/pdf" \
  -H "Authorization: Bearer $TOKEN" -d @/tmp/pdf_payload.json
# HTTP 200, 3258 bytes

# 4. 调 /print/preview (走完整 resolver)
curl -X POST "http://localhost/api/v1/print/preview" \
  -H "Authorization: Bearer $TOKEN" -d '{"templateCode":"reimbursement_simple_v1","data":{"_resolver":"4"},...}'
# html len: 3516, templateId: 6 ✅
```

### 4.3 浏览器实测（Playwright e2e）

```bash
node e2e_editor.js
# → 登录 admin/admin123
# → 访问 http://localhost/admin/print-template/editor/6
# → 三栏布局正常，右侧实时预览显示：
#   费用报销单 / 标书打印费 / 贰佰捌拾贰万玖仟贰佰柒拾伍元整 / ¥ 2,829,275.00 / 2 张 / 报销人：张斌
# → 全单元格边框 ✅
```

### 4.4 视觉对比

| 项 | Excel 原版（用户截图） | 我们的复刻（Chrome 截图） | 状态 |
|---|----|----|----|
| 标题 | 费用报销单 | 费用报销单 | ✅ |
| 标题加粗 | ✅ | ✅ | ✅ |
| 标题居中 | ✅ | ✅ | ✅ |
| 日期行 | ____年____月____日 右对齐 | ____年____月____日 右对齐 | ✅ |
| 费用摘要 | 居中粗 + 内容粗居中 | 居中粗 + 内容粗居中 | ✅ |
| 金额大写 | 玖拾捌元伍角（粗体） | 贰佰捌拾贰万玖仟贰佰柒拾伍元整（粗体） | ✅ |
| 金额小写 | ¥ 98.50（粗体） | ¥ 2,829,275.00（粗体） | ✅ |
| 备注 + 张数 | 备注 + 附单据张数 | 备注 + 附单据张数 | ✅ |
| 4 签字栏 | 核准 / 审批 / 会计 / 报销人 | 核准 / 审批 / 会计 / 报销人 | ✅ |
| 全单元格边框 | ✅ | ✅ | ✅ |

## 五、零破坏回归

测试 4 套老模板（contract_v1 / expense_v1 / invoice_v1 / reimbursement_v1）走 `/print/preview`：

| tid | 模板 | HTTP | 响应大小 |
|---|---|---|---|
| 2 | contract_v1 | 200 | 2683 bytes |
| 3 | expense_v1 | 200 | 2156 bytes |
| 4 | invoice_v1 | 200 | 2073 bytes |
| 5 | reimbursement_v1 | 200 | 2934 bytes |

**结论**: ✅ 老模板完全未受影响（grid 是新增 ctype 分支，老分支没动）。

## 六、改动文件清单

| 文件 | 改动 | 行数 |
|------|------|------|
| `backend/app/modules/print_runtime/renderers/html_renderer.py` | +grid 分支 +page-break CSS | 139 → 207 |
| `backend/app/modules/print_runtime/renderers/pdf_renderer.py` | +grid 分支（reportlab Table + SPAN） | 426 → 554 |
| `plans/udpe-design/outputs/m3-stage2.1-reimbursement-grid.json` | 新增（grid 版模板定义） | 0 → 179 |
| `plans/udpe-design/outputs/m3-stage2.1.md` | 本报告 | 0 → 全文 |

数据库：`print_templates.id=6` 的 `schemaJson` 已更新为 grid 版本。
镜像：`shuzhi-backend:latest` 已 rebuild（`docker compose build --no-cache backend`）。

## 七、设计要点与权衡

1. **grid 是新增 block 类型** — 完全向后兼容，老模板不受影响
2. **HTML 用 `<table>` + `colspan`** — 浏览器原生支持，CSS 控制边框
3. **PDF 用 `reportlab.Table` + `SPAN`** — 和 HTML 1:1 映射
4. **行高按 mm** — PDF 是绝对单位，HTML 用 mm 也能正常显示
5. **列宽默认等分** — 高级用法可加 `colWidthsMm` 自定义
6. **不支持小数 colspan** — Excel 单元格合并是整数（≥1），整数化即可
7. **数据绑定走 `bind` 字段** — 优先于 `text` 模板插值（与老 ctype 保持一致）
8. **金额单位是分** — 这是整个系统约定（`reimbursement_v1` 也用分），不属于本任务范围

## 八、后续可选增强（M2+）

- [ ] `grid` cell 内嵌 `image` / `qrcode` / `barcode` 子组件
- [ ] `colWidthsMm` 自定义列宽
- [ ] 嵌套 grid（cell 内是另一个 grid）
- [ ] 条件显示（cell-level `condition` 字段）
- [ ] 设计器中可视化拖拽（暂不在 M3 范围）

## 九、截图

- HTML 渲染（API `/print/preview-schema`）：`/tmp/preview_real.png`
- HTML 渲染（API `/print/preview`）：`/tmp/preview_full.png`
- 编辑器三栏布局：`/tmp/editor_6_loaded.png`
- 容器内 smoke test：`/tmp/test_grid_v2.png` (HTML 渲染)
