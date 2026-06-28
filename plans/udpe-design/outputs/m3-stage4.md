# UDPE M3 阶段 4 — Excel 导入（实施报告）

> 目标：让用户上传一个真实 Excel 模板（合并单元格 + 边框 + 字体样式），
> 引擎自动解析成 schemaJson，并保存为可编辑的打印模板，
> 实现"以后财务只改 Excel，不改 JSON"。

---

## 一、产出清单

### 新增文件

| 路径 | 行数 | 说明 |
|---|---|---|
| `backend/app/modules/print_runtime/importers/__init__.py` | 5 | 包入口 |
| `backend/app/modules/print_runtime/importers/excel_importer.py` | 250 | openpyxl 解析 + 合并单元格 + 样式映射 |
| `frontend/src/components/admin/print/ExcelImportDialog.vue` | 298 | 三步式对话框（上传 → 预览 → 命名） |
| `plans/udpe-design/outputs/m3-stage4-design.md` | 439 | 阶段 4 设计文档 |

### 修改文件

| 路径 | 变更 |
|---|---|
| `backend/requirements.txt` | 追加 `openpyxl>=3.1.0` |
| `backend/app/modules/print_runtime/router.py` | 追加 2 个 admin endpoint + File/UploadFile 导入 |
| `frontend/src/api/print.ts` | 追加 `excelImportApi` (preview/confirm) |
| `frontend/src/views/admin/AdminPrintTemplateEditor.vue` | 顶部新增"📥 导入 Excel"按钮 + 弹窗 + 保存后跳编辑模式 |

---

## 二、核心设计

### 2.1 Excel → schemaJson 数据结构

`parse_excel(file_bytes) -> {sheets: [...], totalSheets: N}`：

```
sheets[i] = {
  name:    "Sheet1",
  rowCount: 24,
  colCount: 9,
  mergedRegions: 24,
  warnings: ["[UDPE] Excel 合并区域 X 纵向跨 N 行, V1 降级为单行 + 占位"],
  cells: {
    "0,0": { text, span, row_span, _origin_row, bold, fontSize, align, valign, color, has_border },
    ...
  }
}
```

关键约束：
- 横向合并 → `span` (col span)，直接保留为 grid block 的 `colSpan`
- 纵向合并 → 折叠到首行 + `_origin_row` 标记，V1 引擎不渲染
- 边框、字体颜色、对齐方式粗略映射到 schemaJson 样式
- `auto_border = (任意单元格有 border) OR (行数 ≥ 2)`，默认开

### 2.2 API 形态

```
POST /api/v1/admin/print-templates/import/excel/preview
  Body: multipart/form-data, file=<xlsx>
  Returns: { sheets: [...], totalSheets, totalWarnings }
  Side effect: 无（幂等解析，不写库）

POST /api/v1/admin/print-templates/import/excel/confirm
  Body: {
    name, code, category?, paper?, orientation?,
    sheetIndex: 0,
    cells: {...},  // 预览阶段返回的 cells
    warnings: [...]
  }
  Returns: { id, code, name, status: "draft" }
  Side effect: 写入 PrintTemplate 表，status=draft
```

### 2.3 前端三步式流程

```
[1. 上传]      拖拽 / 点击选 .xlsx → 调 preview
       ↓
[2. 预览]      显示解析摘要 + 单元格网格预览 + warnings 列表
       ↓
[3. 命名]      自动填 code/name，可改
       ↓
[确认] → 调 confirm → 跳 /admin/print-template/editor/{id}
```

### 2.4 关键决策

1. 导入按钮仅在 `isNew` 模式显示（id=undefined 时），已存在的模板用"另存为"语义
2. Auto border 默认开：用户从 Excel 导入时希望看到表线
3. 纵向合并降级：V1 grid block 不支持行合并，自动折叠 + warnings
4. 零新前端依赖：沿用现有 Element Plus + 自定义 `c{n}_{rand}` ID 规则
5. 不破坏现有模板：原有 6 个手工 JSON 模板继续可用

---

## 三、验证

### 3.1 后端单元验证

```bash
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account":"admin","password":"admin123"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -X POST "http://localhost/api/v1/admin/print-templates/import/excel/preview" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/Users/trisome/Desktop/开发/数智化系统new/user_reimbursement.xlsx"
```

实际返回：3 个 sheet，Sheet1 有 36×9 单元格，24 个合并区域，无报错。

### 3.2 端到端验证（Playwright）

脚本 `e2e_import.js`：
1. 登录 `admin / admin123`
2. 进入 `/admin/print-template/editor`（新建模式）
3. 点击"📥 导入 Excel"
4. 上传 `user_reimbursement.xlsx`
5. 点击"下一步"
6. 点击"确认导入"
7. 断言跳转到 `/admin/print-template/editor/8`
8. 截图保存

结果：全部通过，最终截图保存为 `/tmp/m3s4_after_save.png`，
新模板 id=8 出现在列表中。

### 3.3 数据库核对

导入后 `print_template` 表新增 1 条记录：
| id | code | name | category | status |
|---|---|---|---|---|
| 8 | sheet1_excel_xxxx | Sheet1 (Excel 导入) | 自定义 | draft |

`schema_json` 字段保存了 `cells` 字典，可被 VisualCanvas 加载渲染。

---

## 四、当前限制（M3 阶段 4 已知边界）

| 限制 | 原因 | 后续方案 |
|---|---|---|
| 纵向合并降级为单行 | V1 grid block 只支持 colSpan | M3 阶段 5+ 引入 nested grid |
| 公式（`=SUM()`）不求值 | openpyxl 默认拿到的是公式串 | 用户预计算或后续接 xlcalculator |
| 条件格式 / 图案 / 渐变 丢失 | 解析器只保留字体/边框/对齐/颜色 | 后续按需扩展 |
| Excel 内嵌图 / 图表不导入 | V1 不支持图片块 | M4 引入图片块 |
| `{{ }}` 占位符检测已实现但本文件无 | 用户 Excel 内数据是写死的 | 用户在 Excel 中加 `{{ form.title }}` 等占位符后即可生效 |

---

## 五、下一阶段候选

按用户表达优先级：

1. **M3 阶段 4 下半 — Word (.docx) 导入**（用户已提"Word → schemaJson 自动转换"）
   - 用 `python-docx`，结构比 Excel 简单（段落 + 表格两套）
   - 复用同一 confirm endpoint，加 `format=docx` 分支

2. **M3 阶段 5 — 数据绑定 UI**
   - 右侧属性面板加"绑定到字段"下拉
   - 支持 `{{ form.title }}` 表达式直接键入

3. **M3 阶段 6 — 撤销/重做 + 嵌套 grid + 拖拽**
   - editor 内操作历史栈
   - cell 内嵌子 cell（解决纵向合并问题）

4. **M4 — PDF 模板解析（OCR + 标注）**
   - 上传扫描件 → tesseract → 用户标注文字块 → 自动生成 schemaJson

---

## 六、本阶段交付

- 后端 importer + 2 endpoints
- 前端三步式对话框
- 编辑器集成入口
- 端到端验证通过
- 真实 Excel 文件成功导入
- 零破坏（原有 6 个模板继续可用）
- 零新前端依赖
- 实施报告（本文件）
