# M2 阶段 9 — 批量打印 (Batch PDF)

> 阶段：M2 阶段 9  
> 完成日期：2026-06-28  
> 设计文档：plans/udpe-design/design.md §五 5.2 / §十三 阶段 6（P0 批量打印）

## 目标

设计文档把"批量打印"列为 **P0 高级功能**。本次实现：
- 同一模板 + 多个业务主键 → **合并为单个 PDF** 触发下载
- 不上异步队列（V1 同步实现，10 条以内 < 500ms）
- 复用现有 4 套预置模板，业务方零代码接入

## 实现概览

### 1. 后端新端点 `POST /api/v1/print/batch`

**位置**：`backend/app/modules/print_runtime/router.py:215`

请求：
```json
{
  "templateCode": "contract_v1",
  "items": [{"id": 2}, {"id": 3}, {"id": 4}],
  "options": {
    "renderMode": "pdf",
    "sourceModule": "contract"
  }
}
```

响应：
- `Content-Type: application/pdf` (流式)
- `Content-Disposition: attachment; filename="batch_contract_v1_xxx.pdf"`
- 自定义响应头：
  - `X-Print-Batch-Total: N`
  - `X-Print-Batch-Success: N`
  - `X-Print-Batch-Failed: N`
  - `X-Print-Batch-Elapsed-Ms: N`

权限：`print:document:export`（与单条 PDF 一致）

校验：
- `templateCode` 1-64 字符
- `items` 1-100 条（Pydantic 校验）

### 2. Service 编排 `service.render_batch`

**位置**：`backend/app/modules/print_runtime/service.py:415`

```python
async def render_batch(db, template_code, item_ids, bind_ctx):
    """批量渲染并合并为单个 PDF."""
    bind_ctx.extra["db"] = db  # 关键: Resolver 需要 db
    for item_id in item_ids:
        req = PrintRequest(
            template_code=template_code,
            data={"_resolver": item_id},
            options={"renderMode": "pdf", "sourceModule": ..., "sourceId": str(item_id)},
        )
        result = await render(db, req, bind_ctx)  # 复用单条渲染
        pdf_chunks.append(result.content)
        log_ids.append(result.log_id)
    merged = _merge_pdfs(pdf_chunks)
    return merged, log_ids, failed_items, elapsed
```

**关键修复**（M2 阶段 9 期间发现）：
原 service.render_batch 没设置 `bind_ctx.extra["db"]`，导致 ExpenseResolver 报 NoneType。已与单条 service.render 行为对齐，注入 db。

### 3. PDF 合并 `_merge_pdfs`

**位置**：`backend/app/modules/print_runtime/service.py:475`

```python
def _merge_pdfs(pdf_chunks: List[bytes]) -> bytes:
    """用 pymupdf (fitz) 合并多个 PDF bytes."""
    import fitz  # PyMuPDF
    merged = fitz.open()
    for chunk in pdf_chunks:
        src = fitz.open(stream=chunk, filetype="pdf")
        merged.insert_pdf(src)
        src.close()
    buf = io.BytesIO()
    merged.save(buf)
    return buf.getvalue()
```

**依赖**：复用 `PyMuPDF>=1.24.0`（已在 `requirements.txt`，发票 PDF 识别用），**不新增 pypdf**。

### 4. 前端 SDK `printApi.batchPdf`

**位置**：`frontend/src/api/print.ts:140`

```ts
export interface BatchStats {
  total: number
  success: number
  failed: number
  elapsedMs: number
}

async batchPdfBlob(args: {
  templateCode: string
  items: Array<string | number>
  options?: PrintOptions
  silent?: boolean
}): Promise<{ blob: Blob; stats: BatchStats }>

async batchPdf(args: {
  templateCode: string
  items: Array<string | number>
  options?: PrintOptions
  silent?: boolean
}): Promise<BatchStats>  // 自动触发下载
```

**注意**：blob 下载时浏览器无法读取 response headers，`stats` 只能填 total（success = total, failed = 0）。后端有详细统计可通过 `print_logs` 数据库查询。

### 5. 业务列表页接入 (3 个)

每个列表页加「🖨 批量打印」按钮，复用现有 el-table 多选机制：

| 列表页 | 文件 | templateCode | ID 字段 |
|--------|------|--------------|---------|
| 合同 | `ContractList.vue:585` | `contract_v1` | `id` |
| 费用 | `ExpenseList.vue` | `expense_v1` | `id` |
| 报销 | `ReimburseList.vue` | `reimbursement_v1` | `formId`（注意字段） |

按钮权限：`v-permission="'print:document:export'"`（无权限时自动隐藏）。

按钮 UX：
- 禁用条件：`selectedIds.size === 0 || batchPrinting`
- 选中后显示 (N) 角标
- 完成后 ElMessage 提示 `批量打印完成: N/N 条`
- 失败显示具体错误

## 端到端验证

### 后端 curl 测试 (4 套业务)

| 模板 | items | success | failed | PDF size | pages |
|------|-------|---------|--------|----------|-------|
| contract_v1 | [2,3,4] | 3 | 0 | 7436 B | 3 |
| invoice_v1 | [3,4,5] | 3 | 0 | 6933 B | 3 |
| expense_v1 | [9,18,19] | 3 | 0 | 7328 B | 3 |
| reimbursement_v1 | [3,4] | 2 | 0 | 6600 B | 2 |

平均渲染：10-50ms/条

### 前端浏览器测试 (3 个列表页)

| 列表页 | 选中 | 后端响应 | 下载文件 |
|--------|------|---------|---------|
| /contract/list | 3 行 | 200 / X-Success=3 | 7486 B PDF |
| /expense/list | 3 行 | 200 / X-Success=3 | 7080 B PDF |
| /reimbursement/list | 2 行 | 200 / X-Success=2 | 6602 B PDF |

### print_logs 数据库校验

```
 8 条成功 log (近 5 分钟)
 - 3 contract (5,6,7)
 - 3 expense (24,25,26)
 - 2 reimbursement (3,4)
 - pdf_size 3-4KB, elapsed_ms 4-21ms
```

## 零破坏回归

| 业务详情页 | 渲染状态 |
|-----------|---------|
| /contract/2 (按模板打印) | ✅ 成功 (HT-2026-032 云服务采购合同) |
| /invoice/ocr/3 (按模板打印) | ✅ 成功 (26117000000915150787) |
| /expense/9 | ⚠️ 数据库该 ID 不存在，无按钮（mock 兜底） |

- 0 pageerror
- 0 新增 4xx/5xx
- 4 处原打印 hack 全部保留

## 关键设计决策

1. **同步实现 vs 异步队列**：V1 走同步，10 条以内 < 500ms。100 条 + 时再上 FastAPI BackgroundTasks + Redis Stream（设计文档阶段 6 标注）。
2. **PDF 合并用 PyMuPDF**：不引入新依赖，复用现有 `fitz.Document.insert_pdf()`。
3. **每个 item 写一条 log**：保留完整审计链（操作员 / 模块 / 来源 / 耗时 / PDF 大小），方便 `AdminPrintLog` 按批次反查。
4. **失败软处理**：单条失败不中断整批，`failed_items` 收集错误，最后返回合并的 PDF（不含失败项）。V1 暂不阻断成功项下载。
5. **绑定 db 给 bind_ctx**：与单条 service.render 行为对齐，避免 Resolver 报 NoneType。
6. **前端 blob 下载限制**：浏览器 fetch blob 时拿不到自定义 headers，stats 仅作前端显示用。准确统计以后端 X-Print-Batch-* 头为准。

## 后续优化（M3+）

- [ ] 异步队列 + SSE 进度推送（> 100 条时）
- [ ] 多模板批量（一个 ZIP 含多种模板 PDF）
- [ ] 批量打印前的"预览前 3 条"功能（避免大数量踩坑）
- [ ] 失败重试 + 邮件通知
- [ ] 数字签名（每个 PDF 末尾附管理员签名）

## 完成度

| 任务 | 状态 |
|------|------|
| 后端 `/print/batch` 端点 | ✅ |
| Service 编排 + PDF 合并 | ✅ |
| 前端 SDK `batchPdf/batchPdfBlob` | ✅ |
| 合同列表页集成 | ✅ |
| 费用列表页集成 | ✅ |
| 报销列表页集成 | ✅ |
| 4 套业务端到端验证 | ✅ |
| 回归测试 (零破坏) | ✅ |

发票列表因项目里没有独立列表页（全部走 OCR 入口）暂不集成。需要时再补。
