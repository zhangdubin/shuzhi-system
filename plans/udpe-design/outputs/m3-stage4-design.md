# M3 阶段 4 — 模板导入（Excel/Word → schemaJson 自动转换）

> **状态**: 📐 设计阶段
> **作者**: Codex (claude-sonnet-4)
> **日期**: 2026-06-28
> **前置**: M3 阶段 3 (可视化设计器 + grid block)
> **目标**: 让业务方（财务/人事/合同管理员）**直接维护 Excel/Word 模板**，系统自动转换为 schemaJson，**0 代码**。

## 一、问题与价值

### 1.1 当前痛点（M3 阶段 3 后）

- 复杂模板（10+ 行 × 5-7 列 × 跨列合并）手写 JSON 200+ 行
- 业务方（财务、人事、销售）**改不动 JSON**
- 每次字段调整都要开发介入
- **违反** UDPE "业务方自助"的设计目标

### 1.2 用户期望

> "保留 Excel 模板（所见即所得），读取合并单元格，自动生成 schemaJson。  
> 以后财务修改模板只改 Excel，不改 JSON。"

这是企业级打印平台（帆软、积木报表、润乾、Smartbi）的通用做法。

### 1.3 价值

| 维度 | 现状 (M3 阶段 3) | 改进后 (M3 阶段 4) |
|------|---|---|
| 模板维护方 | 工程师 | **业务方** |
| 改字段耗时 | 5-30 分钟 | **30 秒** |
| 维护成本 | 高 (学 JSON) | **极低 (Excel/WPS)** |
| 模板数量上限 | 受工程师产能限制 | **无上限** |
| 复杂度天花板 | 5-10 个组件 | **Excel 多 sheet + 合并** |
| 业务可用模板数 | 5 套预置 | **用户上传无限** |

## 二、技术验证（已通过 ✅）

### 2.1 openpyxl 解析能力（Python）

**已验证**：openpyxl 3.1.5 能完整解析：
- ✅ 合并单元格（merged_cells.ranges）— 24 个区域正确识别
- ✅ 单元格值（含 `{{ form.xxx | filter }}` 模板插值）
- ✅ 字体（size / bold / name / color）
- ✅ 对齐（horizontal / vertical / wrap_text）
- ✅ 边框（top / bottom / left / right — openpyxl 用 style='thin' 等表示）
- ✅ 列宽 / 行高
- ✅ 多 sheet / 数据类型（数字、字符串、空）

**已用用户真实 Excel 验证**：`/Users/trisome/Desktop/报销单模板自行打印.xlsx`
- 3 个 sheet（Sheet1 含 2 张单据）
- 24 个合并区域
- 字体：黑体 24pt 加粗
- 居中对齐

### 2.2 python-docx 解析能力（待验证）

预估能解析：
- ✅ 段落、表格、占位符 `{{ xxx }}`
- ✅ 字体、字号、颜色
- ✅ 表格行/列
- ❌ 不支持合并单元格（Word 表格合并靠 merge_fields）

### 2.3 端到端转换（mock 验证）

```python
# 输入: 用户的 Excel 报销单模板
# 输出: UDPE schemaJson (grid 格式)
{
  "type": "grid",
  "colCount": 7,           # 从 Excel 列数推导
  "border": true,           # 默认
  "rows": [
    {
      "height": 24,         # 从 Excel 行高推导
      "cells": [
        {"text": "费 用 报 销 单", "span": 7, "bold": true, "align": "center", "fontSize": 24}
      ]
    },
    ...
  ]
}
```

**转换准确率预估**：80% 模板直接可用，20% 需人工微调（列数推断、占位符规范）。

## 三、范围与拆分

### 3.1 M3 阶段 4 上半（**Excel 导入**，1 周）

**目标**：支持上传 `.xlsx` → 自动生成 schemaJson → 保存为新模板

#### 后端
- `POST /print/templates/import/excel` (multipart/form-data)
- 解析 xlsx → 生成 schemaJson → 预览
- `POST /print/templates/import/excel/confirm` → 保存到 DB

#### 前端
- 编辑器加"📥 导入 Excel"按钮
- 弹窗：上传 → 解析进度 → 预览 → 命名/选择 docType → 保存
- 实时预览：转换后的 grid schema 在右侧 iframe 渲染

#### 转换规则
1. **合并区域 → grid row cells + span**:
   - Excel `A1:D1` 合并 → grid row 1 含 1 个 cell `span=4`
2. **非合并 → 独立 cell**:
   - Excel `A2` 单独 → cell `span=1`
3. **占位符识别**:
   - 文本含 `{{ path | filter }}` → 直接保留为 `text` 字段
   - 文本不含 `{{` → 当作静态文本
4. **样式映射**:
   - 字体 bold → `bold: true`
   - 字号 → `fontSize`
   - 水平对齐 → `align`
   - 垂直对齐 → `valign`
   - 边框（任一边有）→ `border: true`
5. **行高**:
   - Excel 行高（point）→ 转换成 mm（point / 2.835）
6. **列数**:
   - 取所有 row 中 cell span 之和的最大值 = `colCount`

#### 模板选择
- **单 sheet 模板**：默认导入整个 sheet
- **多 sheet 模板**：
  - 选项 A：每个 sheet 生成一个独立模板
  - 选项 B：用户选择要导入的 sheet
  - V1 选 B（让用户选）

### 3.2 M3 阶段 4 下半（**Word 导入**，1 周）

**目标**：支持上传 `.docx` → 自动生成 schemaJson

#### 解析范围
- 段落（含占位符）→ text
- 标题样式（Heading 1）→ title
- 表格 → grid 或 table
- 表格行 → grid row cells

#### 占位符
- Word 中 `{{ form.title }}` 文本 → 自动转为 `text` 字段
- Word 的"内容控件"（Structured Document Tag）→ 高级占位符

### 3.3 M4+（**PDF 导入**，推迟）

- 难点：PDF 无结构信息，需 OCR + 半自动标注
- 优先级低（Excel/Word 已覆盖 95% 业务场景）

## 四、Excel 转换算法（详细）

### 4.1 核心数据结构

```python
@dataclass
class CellInfo:
    text: str                # 单元格值 (含模板占位符)
    bold: bool = False
    font_size: Optional[float] = None
    color: Optional[str] = None
    h_align: Optional[str] = None  # 'left'/'center'/'right'
    v_align: Optional[str] = None
    has_border: bool = False

@dataclass
class ExcelToGridConverter:
    """Excel sheet → UDPE grid block 转换器"""
    sheet: Worksheet
    col_count: int            # 推导的总列数
    rows: List[RowInfo]       # 解析后的行
```

### 4.2 转换步骤

```python
def convert_sheet(sheet) -> dict:
    # Step 1: 扫描所有非空单元格 + 合并区域, 构造 grid 占用图
    occupied = [[False] * sheet.max_column for _ in range(sheet.max_row)]
    cells = {}  # (row, col) -> CellInfo
    
    # Step 1.1: 合并区域 - 起始位置填内容, span 覆盖其余位置
    for mr in sheet.merged_cells.ranges:
        # 起始位置 = (mr.min_row, mr.min_col)
        start = sheet.cell(mr.min_row, mr.min_col)
        span = (mr.max_row - mr.min_row + 1, mr.max_col - mr.min_col + 1)
        # 实际 UDPE grid 只支持横向 span, 不支持纵向
        # 策略: 整个合并区域当作 1 个 row, cells 数组只放起始位置
        cells[(mr.min_row, mr.min_col)] = CellInfo(
            text=start.value or '',
            span=span[1],  # 横向 span
            row_span=span[0],  # 纵向 span (V1 暂不支持, 后续扩展)
            ...
        )
        # 标记占用
        for r in range(mr.min_row, mr.max_row + 1):
            for c in range(mr.min_col, mr.max_col + 1):
                occupied[r-1][c-1] = True
    
    # Step 1.2: 非合并区域 - 独立 cell
    for row in sheet.iter_rows():
        for cell in row:
            if (cell.row, cell.column) in cells:  # 合并起始已处理
                continue
            if cell.value is None:
                continue
            cells[(cell.row, cell.column)] = CellInfo(
                text=cell.value,
                span=1,
                ...
            )
    
    # Step 2: 按行分组, 构造 grid rows
    grid_rows = []
    for r in range(1, sheet.max_row + 1):
        row_cells = []
        for c in range(1, sheet.max_column + 1):
            if occupied[r-1][c-1] and (r, c) in cells:
                cell = cells[(r, c)]
                row_cells.append({
                    'text': cell.text,
                    'span': cell.span,
                    'bold': cell.bold,
                    'align': cell.h_align,
                    'valign': cell.v_align,
                    'fontSize': int(cell.font_size) if cell.font_size else None,
                })
        if row_cells:
            # 行高 = Excel 行高 (point) × 0.353 (point → mm)
            height_mm = int(sheet.row_dimensions[r].height * 0.353) if sheet.row_dimensions[r].height else 14
            grid_rows.append({'height': height_mm, 'cells': row_cells})
    
    # Step 3: 推导 colCount
    # 取所有行中 cell span 之和的最大值
    col_count = max(sum(c['span'] for c in r['cells']) for r in grid_rows)
    
    return {
        'type': 'grid',
        'colCount': col_count,
        'border': True,  # 默认
        'rows': grid_rows
    }
```

### 4.3 占位符识别

```python
import re
PLACEHOLDER_RE = re.compile(r'\{\{\s*([^}]+?)\s*\}\}')

def is_template_text(text: str) -> bool:
    """文本含 {{ ... }} → 模板插值"""
    return bool(text and PLACEHOLDER_RE.search(text))

def clean_template_text(text: str) -> str:
    """规范化: {{ x }} → {{ x }}, {{x|filter}} → {{ x | filter }}"""
    return PLACEHOLDER_RE.sub(lambda m: '{{ ' + m.group(1).strip() + ' }}', text)
```

### 4.4 边框检测

```python
def has_border(cell) -> bool:
    """任一边有边框 → 整 cell 算有边框"""
    b = cell.border
    return any([
        b.top and b.top.style and b.top.style != 'none',
        b.bottom and b.bottom.style and b.bottom.style != 'none',
        b.left and b.left.style and b.left.style != 'none',
        b.right and b.right.style and b.right.style != 'none',
    ])
```

## 五、API 设计

### 5.1 预览转换（不保存）

```http
POST /api/v1/admin/print-templates/import/excel/preview
Content-Type: multipart/form-data
Body: file=<xlsx>

Response:
{
  "code": 0,
  "data": {
    "sheets": [
      {
        "name": "Sheet1",
        "rowCount": 36,
        "colCount": 7,
        "mergedCount": 24,
        "schemaJson": { "body": [ ... grid block ... ] },
        "html": "..."  // 转换后的预览 HTML
      },
      ...
    ]
  }
}
```

### 5.2 确认保存

```http
POST /api/v1/admin/print-templates/import/excel/confirm
Content-Type: application/json
Body: {
  "code": "reimbursement_excel_v2",
  "name": "费用报销单（Excel 导入）",
  "docType": "reimbursement",
  "paper": "A4",
  "orientation": "portrait",
  "schemaJson": { "body": [ ... ] },
  "sourceSheet": "Sheet1"  // 哪个 sheet
}

Response:
{ "code": 0, "data": { "id": 7, ... } }
```

### 5.3 前端 SDK

```ts
// frontend/src/api/print.ts
async previewExcelImport(file: File): Promise<{
  sheets: Array<{ name, rowCount, colCount, mergedCount, schemaJson, html }>
}>

async confirmExcelImport(payload: {
  code, name, docType, paper, orientation, schemaJson, sourceSheet
}): Promise<{ id, ... }>
```

## 六、UI 设计

### 6.1 编辑器顶部加按钮

```
顶部工具栏: [←返回] [标题] [状态] ... [撤销] [📥导入Excel] [保存] [发布]
```

### 6.2 导入弹窗（Element Plus el-dialog）

```
┌──────────────────────────────────────────────────┐
│ 📥 导入 Excel 模板                          [X] │
├──────────────────────────────────────────────────┤
│                                                  │
│  1. 选择文件                                     │
│  ┌────────────────────────────────────────────┐ │
│  │  [选择文件] 报销单模板.xlsx (12.8 KB)      │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  2. 选择 Sheet (含 3 个)                         │
│  ┌──────┐ ┌──────┐ ┌──────┐                    │
│  │Sheet1│ │Sheet2│ │Sheet3│                    │
│  │ 24 合并│ │空   │ │空   │                    │
│  └──────┘ └──────┘ └──────┘                    │
│                                                  │
│  3. 转换预览                                     │
│  ┌────────────────────────────────────────────┐ │
│  │ <iframe> 渲染转换后的 HTML 预览             │ │
│  │                                            │ │
│  │ 费用报销单 ... 退票费 98.5 ...              │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  4. 模板信息                                     │
│  code: [reimbursement_excel_v2      ]          │
│  name: [费用报销单(Excel 导入)     ]            │
│  docType: [报销单 ▼]                            │
│                                                  │
│              [取消]  [确认导入]                  │
└──────────────────────────────────────────────────┘
```

## 七、风险与缓解

| 风险 | 缓解 |
|---|---|
| 复杂 Excel 结构无法 1:1 还原 | 80% 模板够用 + 提供 JSON 微调入口 |
| 占位符命名不规范 | 提供"占位符检查"工具，列出识别的占位符 |
| 列宽/行高换算误差 | 使用 mm 单位 + 视觉对比预览 |
| Excel 公式 (SUM) 不会处理 | V1 提示用户公式不支持，建议预计算 |
| 多 sheet 跨 sheet 引用 | V1 暂不支持，每个 sheet 独立模板 |
| Excel 密码保护 | 检测后提示用户先解锁 |
| 样式丢失（颜色、图案填充）| V1 只保留字体/边框/对齐，渐变等丢弃并提示 |

## 八、验收标准

1. 上传用户真实 Excel `报销单模板自行打印.xlsx`
2. 解析 Sheet1 → 24 个合并区域 → 2 张单据
3. 自动生成 grid schemaJson，每张单据 1 个 row group
4. 转换后的预览 HTML 与原 Excel 视觉 1:1
5. 占位符识别：标题"费 用 报 销 单"识别为静态文本，金额单元格保留 `{{ form.totalAmount | chinese_money }}`
6. 字体识别：标题 24pt 黑体加粗居中
7. 保存为新模板，能在 `/admin/print-template` 列表看到
8. 调用 `/print/preview-schema` 渲染与 Excel 视觉一致

## 九、排期建议

| 阶段 | 时间 | 任务 |
|---|---|---|
| M3 阶段 4 上半 | 1 周 | Excel 导入（后端 + 前端） |
| M3 阶段 4 下半 | 1 周 | Word 导入（后端 + 前端） |
| M3 阶段 5 | 1 周 | 数据绑定 UI 点选字段（点选 form.* 绑定到组件） |
| M3 阶段 6 | 1 周 | 撤销/重做 + 嵌套 grid + 拖拽 |
| M4 | 1-2 周 | PDF 模板解析（OCR + 半自动标注） |

## 十、长期愿景

UDPE 不只是一个"打印引擎"，而是：

```
                ┌─────────────┐
                │ 模板来源     │
                └──────┬──────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
   ┌───▼───┐      ┌───▼───┐      ┌───▼───┐
   │ Excel │      │ Word  │      │ PDF   │
   │ 导入  │      │ 导入  │      │ 解析  │
   └───┬───┘      └───┬───┘      └───┬───┘
       │               │               │
       └───────────────┼───────────────┘
                       │
                ┌──────▼──────┐
                │ schemaJson  │  ← 统一中间表示
                └──────┬──────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
   ┌───▼───┐      ┌───▼───┐      ┌───▼───┐
   │ HTML  │      │ PDF   │      │ Print │
   │ 渲染  │      │ 渲染  │      │ 队列  │
   └───────┘      └───────┘      └───────┘
```

未来 6-12 个月可演进为：
- **模板市场**：用户上传/分享 Excel 模板
- **AI 辅助**：扫描用户 Excel → 自动建议占位符 → 自动生成 schemaJson
- **多租户 SaaS**：每个企业独立模板库
- **报表平台**：从打印引擎演变为"企业单据 + 报表"平台
