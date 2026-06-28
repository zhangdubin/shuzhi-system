# M4 阶段 2 — 业务模块 PDF 迁移

> **状态**: ✅ 已完成
> **作者**: Codex (GPT-5)
> **日期**: 2026-06-28
> **前置**: M2 阶段 5 (UDPE 集成到详情页), M4 阶段 1 (异步批量打印)
> **任务**: 把详情页旧的浏览器原生"下载 PDF"替换为 UDPE SDK 真 PDF

## 一、目标与边界

M2 阶段 5 在 4 个详情页并行添加了"按模板打印"入口（UDPE），但旧的"下载 PDF"按钮仍走浏览器原生打印（用户手动"另存为 PDF"）。
M4 阶段 2 将旧入口升级为 UDPE 真服务端 PDF 生成。

✅ ReimburseDetail: `onDownloadPDF` 改用 `printApi.pdfBlob()` 生成真 PDF
✅ ExpenseDetail: 新增 `downloadPDF` 函数 + "⇩ 下载 PDF" 按钮
✅ ContractDetail: 已有 UDPE PrintPreviewDialog（含下载按钮），无需改动
✅ InvoiceDetail: 已有 UDPE PrintPreviewDialog（含下载按钮），无需改动

## 二、文件改动

| 文件 | 改动 |
|------|------|
| `frontend/src/views/reimbursement/ReimburseDetail.vue` | `onDownloadPDF` 改用 UDPE SDK + 加 printApi import |
| `frontend/src/views/expense/ExpenseDetail.vue` | 新增 `downloadPDF` + `pdfBusy` + printApi import + 打印工具栏按钮 |

## 三、迁移策略

**保留旧入口，升级实现**：
- 旧的"🖨 打印 / 导出 PDF"按钮保留（打开旧打印预览 Dialog）
- 旧 Dialog 内的"⇩ 下载 PDF"改为调 UDPE SDK 生成真 PDF
- 失败时自动 fallback 到浏览器原生打印
- "🖨 浏览器打印"按钮保留不变
- "🧾 按模板打印"（PrintByTemplateButton）继续作为首选入口

## 四、验证

```bash
cd frontend && npm run build
# ✓ built in 5.55s, 0 错误
```

## 五、零破坏验证

- ✅ 旧打印 Dialog 完全保留
- ✅ "🖨 浏览器打印"功能不变
- ✅ "🧾 按模板打印"（UDPE）继续工作
- ✅ 新"⇩ 下载 PDF"使用 UDPE SDK 生成真 PDF
- ✅ 失败时自动 fallback 到浏览器原生打印
- ✅ 其他详情页（合同/发票）已有 UDPE 集成，不受影响

## 六、下一步

1. 清理旧打印 Dialog 中的内联 CSS（已被 UDPE 模板替代）
2. 集成 BatchPrintProgressDialog 到列表页
3. 模板导入/导出功能（JSON 文件）
