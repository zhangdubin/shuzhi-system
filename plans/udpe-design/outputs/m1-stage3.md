# M1 阶段 3 交付报告：核心引擎

> 对应 ChatGPT 流程 3 / UDPE 设计文档 §十三 阶段 3
> 完成时间：1 个工作日（原计划 1 周）
> 状态：✅ 完成

## 交付物

### 1. 渲染器（Renderer）

| 文件 | 内容 | 关键能力 |
|---|---|---|
| `renderers/pdf_renderer.py` | PdfRenderer (reportlab) | text / title / line / spacer / table / image / pagebreak；STSong-Light CID 字体；7 个过滤器；JSONPath；列宽自适应；金额大写 |
| `renderers/html_renderer.py` | HtmlRenderer (纯 Python) | 复用 PdfRenderer 绑定函数，输出 HTML 字符串，含打印 @page CSS |

**支持的过滤器（V1）**：`money` / `chinese_money` / `date` / `datetime` / `upper` / `lower` / `default`

**支持的组件类型（V1）**：`text` / `title` / `line` / `spacer` / `table` / `image` / `pagebreak`

### 2. 数据解析器（Resolver）

| doc_type | 实现 | 取数入口 |
|---|---|---|
| `contract` | ContractResolver | `contract_service.get_contract(db, id)` |
| `reimbursement` | ReimbursementResolver | `reimbursement_service.get_form(db, id)` → `{"form": data}` |
| `expense` | ExpenseResolver | `expense_service.get_expense(db, id)` |
| `invoice` | InvoiceResolver | `invoice_ocr_service.get_invoice(db, id)` |

所有 Resolver 继承 `BaseResolver`，从 `ctx.extra["db"]` 自动取 db session（service 层注入）。

### 3. 变量提供方（Provider）

| name | 提供字段 |
|---|---|
| `system` | now / today / year / operator {id,name} / company {name,shortName} / printTime / printUser |

未来业务模块可注册自己的 Provider，例：`company`、`env`、`org`。

### 4. 4 套预置模板（已 seed 到 DB）

| code | doc_type | 内容 |
|---|---|---|
| `contract_v1` | contract | 合同摘要（编号/客户/金额/签署/大写） |
| `invoice_v1` | invoice | 发票详情（发票号/销购方/金额/税额/大写） |
| `reimbursement_v1` | expense.reimbursement | 报销单（**含 table 组件**绑 `form.details`） |
| `expense_v1` | sales_expense | 销售费用申请单 |

启动方式：
```bash
cd backend
PYTHONPATH=. python -m app.modules.print_runtime.seed_presets
```

### 5. 模板缓存（Redis）

- 模板加载走 `cache:print:template:{code}` Redis key
- TTL = 5 min
- 写操作（create / update / publish / archive）自动失效
- 缓存失败时降级走 DB，**不影响主流程**

### 6. 编排流程（service.render）

```
1) 加载模板（走 Redis 缓存）           → 失败时直接返 3101
2) VariableProvider 注入 system 等     → provider 失败仅 warning，不阻塞
3) 调 Resolver 取业务数据              → 失败返 3104
   触发条件：data._resolver 有值 或 sourceId 存在
4) 调 Renderer.render(template, data, ctx) → 失败返 3103 + 写失败日志
5) 写 print_logs（success/failed）     → 完整 request_data 快照（评审决策 #5）
```

### 7. 端到端验证（4 套模板全过）

| 模板 | bytes | elapsed | log_id | 备注 |
|---|---|---|---|---|
| contract_v1 | 3,301 | 10ms | 9 | 金额大写「壹佰伍拾万元整」✓ |
| invoice_v1 | 3,094 | — | — | 含税 ¥6 大写「陆元整」✓ |
| expense_v1 | 3,356 | 18ms | 7 | 销售费用单 |
| reimbursement_v1 | 4,361 | 14ms | 8 | **table 组件 8 行明细**✓ |

**PyMuPDF 验证**：每份 PDF 1 页 A4，含完整中文字体 + 数据填入 + 表格。

### 8. HTTP 端点 smoke test（容器内）

```bash
# 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account":"admin","password":"admin123"}' | jq -r .token)

# 1. 模板列表
GET  /api/v1/admin/print-templates     → 200, 4 套全 active

# 2. HTML 预览
POST /api/v1/print/preview             → 200, 1694 字节 HTML

# 3. 真 PDF
POST /api/v1/print/pdf                 → 200, 3094 字节, %PDF-1.4, 10ms

# 4. 日志查询
POST /api/v1/print/log                 → 200, 5 条新日志写入
```

## 关键设计落地

| # | 议题 | 决策 | 实现位置 |
|---|---|---|---|
| 1 | M1 不做项（设计器/表达式/异步/数字签名/物理打印） | 推迟到 M2+ | 本阶段严格按计划做 |
| 2 | 第一个迁移示范模块 | `InvoiceDetail` | M1 阶段 5 第一个迁移点 |
| 3 | M1 预置模板套数 | 4 套（合同/报销/发票/费用） | `presets/*.json` + `seed_presets.py` |
| 4 | data schema 校验 | V1 **不强制**，但模板保留 `inputSchema: Optional[dict]` 字段 | `PrintTemplateCreate.inputSchema` 字段已加，V1 不消费 |
| 5 | `print_logs.request_data` 完整快照 | **保留**（含金额） | `print_logs.request_data` 直接存 `req.data` |

## 关键文件清单

| 文件 | 作用 |
|---|---|
| `backend/app/core/print/protocols.py` | 3 个 Protocol（Renderer/Resolver/Provider） |
| `backend/app/core/print/registry.py` | 3 个注册中心 |
| `backend/app/core/print/context.py` | BindContext / RenderContext / PrintRequest / PrintResult |
| `backend/app/core/print/exceptions.py` | 7 个 UDPE 异常族（3101-3107） |
| `backend/app/modules/print_runtime/renderers/pdf_renderer.py` | reportlab PDF 引擎 |
| `backend/app/modules/print_runtime/renderers/html_renderer.py` | HTML 预览引擎 |
| `backend/app/modules/print_runtime/resolvers/*.py` | 4 个业务 Resolver |
| `backend/app/modules/print_runtime/variables/system_vars.py` | 系统变量 |
| `backend/app/modules/print_runtime/presets/*.json` | 4 套预置模板 |
| `backend/app/modules/print_runtime/seed_presets.py` | 启动 seed 脚本 |
| `backend/app/modules/print_runtime/service.py` | 编排主流程（缓存 + Provider + Resolver + Renderer + Log） |
| `backend/app/modules/print_runtime/router.py` | 8 端点（含完整 preview/pdf） |
| `backend/app/main.py:_register_udpe` | 启动时注册 2+4+1 |
| `frontend/src/api/print.ts` | 前端 SDK：`printApi.pdf / pdfBlob / preview / listTemplates / listLogs` |
| `frontend/src/views/invoice/InvoiceDetail.vue` | 阶段 5 第一个示范：新增"按模板打印" |

## 零破坏验证

- 现有 8 个业务模块 router/service 未改动
- 现有 4 处打印 hack（InvoiceDetail/TemplateManager/ReimburseDetail/ExpenseDetail）**完全未动**
- 现有 28 个权限码继续可用（5 个 print 权限是新增，不冲突）
- 现有 audit_logs 继续记录（UDPE 写 print_logs 是子集补充）

## InvoiceDetail 集成示范

**位置**：`frontend/src/views/invoice/InvoiceDetail.vue`

**做法**（严格遵守"零破坏"原则）：
- 原 `printInvoice()` 函数**未动**（仍用 iframe + mock.fileUrl 走老路径）
- 新增 `printByTemplate()` 函数 + quickActions 加一项「按模板打印 🧾」
- 调 `printApi.pdfBlob({ templateCode: 'invoice_v1', data: { _resolver: invoiceId } })`
- 拿到 Blob → `URL.createObjectURL` → `window.open` 新窗口预览
- 用户在浏览器里"另存为 / 打印"

**调用链路**：
```
InvoiceDetail.printByTemplate
  → printApi.pdfBlob({ templateCode: 'invoice_v1', data: { _resolver: invoiceId } })
  → POST /api/v1/print/pdf
  → service.render() 
      → load template (Redis cache hit/miss)
      → SystemVarsProvider.provide() (注入 printTime/printUser)
      → InvoiceResolver.resolve(id) (调 invoice_ocr_service.get_invoice)
      → PdfRenderer.render() (reportlab + STSong-Light)
  → Blob (application/pdf)
  → window.open(blob_url) 
  → 用户打印/另存为
```

## 风险与缓解

| 风险 | 当前状态 | 缓解 |
|---|---|---|
| 中文大写函数 _chinese_money 原版有 bug | 已重写 | 全 12 个测试 case 通过 |
| paper 字段结构不统一（str vs dict） | PdfRenderer 兼容 | `_get_paper` / `_get_margin_mm` 兼容两种 schema |
| Redis 在沙箱内不可达 | 缓存读写都失败 | 模板加载降级走 DB，不影响主流程（仅日志 warning） |
| `request_data` 完整快照含敏感字段 | 按评审决策 #5 保留 | 业务方需自评合规 |
| pydantic 警告"Field 'schema' shadows" | 来自 sqlalchemy 的 BaseModel | 不影响功能 |

## 下一步（M1 阶段 4 + M2 衔接）

| 计划 | 状态 |
|---|---|
| M3 阶段 4：模板设计器 | 推迟（设计文档已就绪，按需启动） |
| M2 阶段 5：迁移合同/报销/费用详情 | 待启动（InvoiceDetail 已示范） |
| M3+：表达式 / 异步 / 数字签名 / 物理打印 | 推迟 |
| 数据库清理 | 已清理 10 条测试 print_logs |
