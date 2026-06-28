# M3 阶段 4 下半 — Word 导入（实施报告）

> 目标：让用户上传一个真实 Word 文档（.docx），
> 引擎自动解析段落和表格为 schemaJson，并保存为可编辑的打印模板，
> 实现"以后业务方只改 Word，不改 JSON"。

---

## 一、产出清单

### 新增文件

| 路径 | 行数 | 说明 |
|---|---|---|
| `backend/app/modules/print_runtime/importers/docx_importer.py` | 280 | python-docx 解析 + 段落/表格映射 |
| `frontend/src/components/admin/print/WordImportDialog.vue` | 298 | 三步式对话框（上传 → 预览 → 命名） |
| `plans/udpe-design/outputs/m3-stage4.5.md` | - | 阶段 4 下半实施报告 |

### 修改文件

| 路径 | 变更 |
|---|---|
| `backend/requirements.txt` | 追加 `python-docx>=1.1.0` |
| `backend/app/modules/print_runtime/router.py` | 追加 2 个 admin endpoint + File/UploadFile 导入 |
| `frontend/src/api/print.ts` | 追加 `docxImportApi` (preview/confirm) |
| `frontend/src/views/admin/AdminPrintTemplateEditor.vue` | 顶部新增"📥 导入 Word"按钮 + 弹窗 + 保存后跳编辑模式 |

---

## 二、核心设计

### 2.1 Word → schemaJson 数据结构

`parse_docx(file_bytes) -> {totalElements, schemaJson, placeholders, warnings}`：

```
schemaJson = {
  "body": [
    { "type": "title", "text": "合同模板", "fontSize": 22, "align": "center" },
    { "type": "text", "text": "合同编号：{{ contract.contractNo }}", "fontSize": 11 },
    { "type": "grid", "colCount": 2, "border": true, "rows": [...] }
  ]
}
```

关键约束：
- 段落 → `text` 类型（支持占位符 `{{ xxx | filter }}`）
- 标题样式（Heading 1/2/3）→ `title` 类型
- 表格 → `grid` 类型（每行对应 grid row，每个单元格对应 cell）
- 样式映射：bold / fontSize / color / align
- 占位符识别：自动提取 `{{ path }}` 格式

### 2.2 API 形态

```
POST /api/v1/admin/print-templates/import/docx/preview
  Body: multipart/form-data, file=<docx>
  Returns: { filename, totalElements, schemaJson, placeholders, warnings, html }
  Side effect: 无（幂等解析，不写库）

POST /api/v1/admin/print-templates/import/docx/confirm
  Body: {
    name, code, category?, paper?, orientation?,
    schemaJson: {...},  // 预览阶段返回的 schemaJson
    warnings: [...]
  }
  Returns: { id, code, name, status: "draft" }
  Side effect: 写入 PrintTemplate 表，status=draft
```

### 2.3 前端三步式流程

```
[1. 上传]      拖拽 / 点击选 .docx → 调 preview
       ↓
[2. 预览]      显示解析摘要 + 元素统计 + 占位符列表 + warnings + HTML 预览
       ↓
[3. 命名]      自动填 code/name，可改
       ↓
[确认] → 调 confirm → 跳 /admin/print-template/editor/{id}
```

### 2.4 关键决策

1. 导入按钮仅在 `isNew` 模式显示（id=undefined 时），已存在的模板用"另存为"语义
2. 标题样式自动识别为 `title` 类型（Heading 1/2/3）
3. 表格合并暂不支持（V1 降级为独立单元格 + warnings 提示）
4. 零新前端依赖：沿用现有 Element Plus + 自定义组件
5. 不破坏现有模板：原有 8 个模板继续可用

---

## 三、验证

### 3.1 后端单元验证

```bash
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account":"admin","password":"admin123"}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -X POST "http://localhost/api/v1/admin/print-templates/import/docx/preview" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_contract.docx"
```

实际返回：
- 5 个元素（4 个段落 + 1 个表格）
- 3 个占位符：contract.amount, contract.contractNo, contract.customerName
- 无警告
- HTML 预览正常渲染

### 3.2 确认保存验证

```bash
curl -X POST "http://localhost/api/v1/admin/print-templates/import/docx/confirm" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "contract_docx_v1",
    "name": "合同模板（Word 导入）",
    "docType": "contract",
    "schemaJson": {...}
  }'
```

结果：全部通过，新模板 id=9 已创建，status=draft。

### 3.3 数据库核对

导入后 `print_template` 表新增 1 条记录：
| id | code | name | category | status |
|---|---|---|---|---|
| 9 | contract_docx_v1 | 合同模板（Word 导入） | 合同 | draft |

`schema_json` 字段保存了 `body` 数组，可被 VisualCanvas 加载渲染。

---

## 四、当前限制（M3 阶段 4 下半已知边界）

| 限制 | 原因 | 后续方案 |
|---|---|---|
| 表格合并降级为独立单元格 | V1 grid block 不支持复杂合并 | M3 阶段 6+ 引入嵌套 grid |
| 图片/图表不导入 | V1 不支持图片块 | M4 引入图片块 |
| 页眉页脚不导入 | python-docx 解析复杂 | 后续按需扩展 |
| 目录/脚注不导入 | 解析器只保留段落/表格 | 后续按需扩展 |
| 样式映射粗略 | 仅保留字体/字号/对齐/颜色 | 后续按需扩展 |

---

## 五、下一步候选

按用户表达优先级：

1. **M3 阶段 5 — 数据绑定 UI**
   - 右侧属性面板加"绑定到字段"下拉
   - 支持 `{{ form.title }}` 表达式直接键入

2. **M3 阶段 6 — 撤销/重做 + 嵌套 grid + 拖拽**
   - editor 内操作历史栈
   - cell 内嵌子 cell（解决纵向合并问题）

3. **M4 — PDF 模板解析（OCR + 标注）**
   - 上传扫描件 → tesseract → 用户标注文字块 → 自动生成 schemaJson

---

## 六、本阶段交付

- 后端 importer + 2 endpoints
- 前端三步式对话框
- 编辑器集成入口
- 端到端验证通过
- 真实 Word 文件成功导入
- 零破坏（原有 8 个模板继续可用）
- 零新前端依赖
- 实施报告（本文件）
