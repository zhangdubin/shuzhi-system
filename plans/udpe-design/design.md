# 统一单据打印引擎（Unified Document Print Engine, UDPE）架构设计

> 角色：首席架构师
> 状态：设计稿（待评审）
> 原则：**零破坏、零重复、可插拔、可演进**
> 不动任何业务代码；所有现有打印能力 100% 保留

---

## 〇、设计动机（基于现状）

经全面摸底，项目当前"打印"能力**完全散落在 4 个文件里**：

| 文件 | 现状 | 问题 |
|---|---|---|
| `frontend/src/views/invoice/InvoiceDetail.vue:191` | 隐藏 iframe + `contentWindow.print()` 加载原始 PDF | 跟发票原始文件绑死，模板化能力 = 0 |
| `frontend/src/views/reimbursement/ReimburseDetail.vue:436` | `window.open` 写死 HTML + `@page A4` + `win.print()` | "下载 PDF" 实际是浏览器"另存为"，**不是真 PDF** |
| `frontend/src/views/reimbursement/TemplateManager.vue:128` | 同上方案，模板 schema 在前端 state | 模板无法持久化共享 |
| `frontend/src/views/expense/ExpenseDetail.vue:23` | `el-dialog` + `@media print` | 又一种 hack，跟上面三种都不通用 |

**结论**：每个业务模块"自己造轮子"，**0 复用**、**0 模板化**、**0 跨模块统一**、**0 服务端 PDF**。

UDPE 的目标：**用 1 套基础设施，替换这 4 处 hack**；未来新业务模块零成本接入。

---

## 一、命名与边界

**UDPE** 不是一个"功能模块"，而是一个**领域基础设施层**，跟 `core/database` `core/sse` `core/cache` 平级。

| 命名空间 | 职责 |
|---|---|
| `app.core.print` | 核心抽象：协议 / 接口 / 引擎 / 注册中心 / 上下文 |
| `app.modules.print_runtime` | 运行时后端模块：模板 CRUD + 调用引擎 + SDK 端点 + 审计 |
| `frontend/src/api/print.ts` | 前端 SDK：业务模块只调这个 |
| `frontend/src/views/admin/PrintTemplate.vue` | 模板管理 UI（V1：列表 + JSON 编辑器） |

**关键边界**：
- UDPE **不**内置任何业务单据的"默认模板"内容
- UDPE **不**强加任何字段名约定
- UDPE **不**改任何现有代码（兼容 `InvoiceDetail.printInvoice()` 等所有现存调用）
- UDPE **不**绑死 PDF 库（V1 用 reportlab 起步，V2 可替换为 WeasyPrint）

---

## 二、目录结构

### 2.1 后端新增

```
backend/app/core/print/                     # 核心抽象（与 core/database 同级）
├── __init__.py
├── protocols.py            # 类型协议：Renderer / DataResolver / VariableProvider
├── registry.py             # 全局注册中心：renderer/resolver/provider 三类
├── context.py              # PrintContext / RenderContext / BindContext 数据类
├── exceptions.py           # UDPE 自定义异常
└── events.py               # UDPE 内部事件钩子（pre_render / post_render / on_error）

backend/app/modules/print_runtime/          # 业务模块（与 contract/expense 同级）
├── __init__.py
├── models.py               # PrintTemplate / PrintTemplateVersion / PrintLog 三张表
├── schemas.py              # Pydantic：PrintTemplateCreate / PrintRequest / PrintResponse
├── router.py               # /api/v1/print/*  +  /api/v1/admin/print-templates/*
├── service.py              # 编排：权限 → 数据装载 → 渲染 → 输出
├── renderers/
│   ├── __init__.py
│   ├── base.py             # 抽象类 Renderer（protocol）
│   ├── html_renderer.py    # 模板 → HTML（Jinja2 渲染）—— 用于预览
│   ├── pdf_renderer.py     # 模板 → PDF 字节流（reportlab）—— V1 主力
│   └── weasyprint_renderer.py  # 占位文件，V2 启用
├── resolvers/
│   ├── __init__.py
│   ├── base.py             # 抽象类 DataResolver
│   ├── static_resolver.py  # 静态 JSON 传入（兜底）
│   ├── contract_resolver.py# 业务解析器：合同 ID → 合同数据
│   ├── reimbursement_resolver.py
│   ├── expense_resolver.py
│   ├── invoice_resolver.py
│   └── ...（按业务模块按需添加）
├── variables/
│   ├── __init__.py
│   ├── system_vars.py      # 系统变量：当前时间、用户、企业、IP 等
│   └── ...（按需扩展）
└── presets/                # 预置模板（首次启动 seed 进 DB）
    ├── reimbursement_v1.json
    ├── contract_v1.json
    └── invoice_v1.json
```

### 2.2 前端新增

```
frontend/src/api/print.ts                   # SDK：业务模块唯一入口
frontend/src/views/admin/PrintTemplate.vue  # 模板管理 V1（列表 + JSON 编辑器）
frontend/src/components/print/              # V1 不上设计器，仅放预览 iframe
└── PrintPreviewDialog.vue                  # WYSIWYG 预览（HTML 渲染 + 缩放）
```

**没有新增子包**（`packages/print` monorepo 改造）。**V1 沿用现有单仓结构**，等 UDPE 稳定后（V3）再考虑抽 monorepo。理由：项目当前没有 monorepo 基础设施（lerna/turborepo/yarn workspaces 都没有），提前拆收益小、成本高。

---

## 三、数据库模型

### 3.1 三张新表（不破坏现有表）

```sql
-- 模板主表（一行 = 一个 doc_type 的当前活跃版本指针）
CREATE TABLE print_templates (
  id            BIGSERIAL PRIMARY KEY,
  code          VARCHAR(64) NOT NULL,          -- 业务唯一 code: 'reimbursement_v1'
  name          VARCHAR(128) NOT NULL,         -- 中文名: '费用报销单（标准版）'
  doc_type      VARCHAR(32) NOT NULL,          -- 单据类型: 'reimbursement' | 'contract' | 'expense' | 'invoice' | 'custom'
  paper         VARCHAR(16) NOT NULL DEFAULT 'A4',  -- A3/A4/A5/Letter/Custom
  width_mm      NUMERIC(8,2) DEFAULT 210,
  height_mm     NUMERIC(8,2) DEFAULT 297,
  orientation   VARCHAR(16) NOT NULL DEFAULT 'portrait',  -- portrait/landscape
  status        VARCHAR(16) NOT NULL DEFAULT 'draft',     -- draft/active/archived
  is_default    BOOLEAN NOT NULL DEFAULT FALSE,           -- 同 doc_type 只能有一个 default
  description   TEXT,
  created_by    BIGINT REFERENCES users(id),
  created_at    TIMESTAMP NOT NULL DEFAULT now(),
  updated_at    TIMESTAMP NOT NULL DEFAULT now(),
  -- 模板内容用 JSONB 存，不拆子表（V1 简单优先；V2 再考虑热加载和分片）
  schema_json   JSONB NOT NULL DEFAULT '{}'::jsonb,       -- 模板定义：组件 + 布局 + 绑定
  version       INTEGER NOT NULL DEFAULT 1,               -- 乐观锁
  CONSTRAINT uq_print_templates_code UNIQUE (code)
);
CREATE INDEX ix_print_templates_doc_type ON print_templates(doc_type);
CREATE INDEX ix_print_templates_status ON print_templates(status);

-- 模板历史版本（V1 只做"软存档"；V2 上回滚 UI）
CREATE TABLE print_template_versions (
  id            BIGSERIAL PRIMARY KEY,
  template_id   BIGINT NOT NULL REFERENCES print_templates(id) ON DELETE CASCADE,
  version       INTEGER NOT NULL,
  schema_json   JSONB NOT NULL,
  snapshot_by   BIGINT REFERENCES users(id),
  snapshot_at   TIMESTAMP NOT NULL DEFAULT now(),
  note          TEXT,
  CONSTRAINT uq_ptv UNIQUE (template_id, version)
);

-- 打印/导出日志（业务模块 + 引擎共用；不进 audit_logs 因为 schema 不同）
CREATE TABLE print_logs (
  id            BIGSERIAL PRIMARY KEY,
  template_id   BIGINT REFERENCES print_templates(id),
  template_code VARCHAR(64) NOT NULL,
  doc_type      VARCHAR(32) NOT NULL,
  action        VARCHAR(16) NOT NULL,           -- preview/pdf/print
  status        VARCHAR(16) NOT NULL,           -- success/failed
  operator_id   BIGINT,
  operator_name VARCHAR(64),
  source_module VARCHAR(32),                    -- 'reimbursement' | 'admin' | ...
  source_id     VARCHAR(64),                    -- 业务单据 ID（字符串，跨模块兼容）
  elapsed_ms    INTEGER,
  error_msg     TEXT,
  pdf_size      INTEGER,                        -- 仅 action='pdf'
  request_data  JSONB,                          -- 入参快照（脱敏后）
  ip            VARCHAR(45),
  created_at    TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_print_logs_template_code ON print_logs(template_code);
CREATE INDEX ix_print_logs_operator_id ON print_logs(operator_id);
CREATE INDEX ix_print_logs_created_at ON print_logs(created_at);
```

**不**建：组件库表、字体表、图章表。**这些放进 `schema_json` 里**——V1 阶段不值得为它们单建表。

### 3.2 与现有表的关系

- **不影响** `approval_templates` / `invoice_templates` / `reimbursement_templates`（业务模板，各管各的）
- **不冲突** `audit_logs`（UDPE 的 `print_logs` 是更专业的子集；审计中间件仍会打 `print.*` 写接口到 `audit_logs`）

---

## 四、模板 Schema 设计（V1）

V1 不上设计器，schema 由"懂技术的产品"手写 JSON。Schema 是个**纯数据描述**，不绑死任何渲染器。

```json
{
  "version": "1.0",
  "meta": {
    "docType": "reimbursement",
    "title": "费用报销单（标准版）",
    "description": "标准 3 段式报销单 A4 纵向"
  },
  "paper": { "size": "A4", "orientation": "portrait", "marginMm": { "top": 18, "right": 18, "bottom": 18, "left": 18 } },
  "fonts": {
    "default": { "family": "STSong-Light", "size": 10, "color": "#1F2937" },
    "title":   { "family": "STSong-Light", "size": 18, "bold": true, "color": "#0F172A" }
  },
  "vars": [
    { "key": "formNo",     "path": "form.formNo",   "type": "string" },
    { "key": "applicant",  "path": "form.applicant.name", "type": "string" },
    { "key": "total",      "path": "form.totalAmount", "type": "money", "unit": "yuan" },
    { "key": "details",    "path": "form.details",  "type": "list" },
    { "key": "now",        "source": "system",      "type": "datetime" }
  ],
  "body": [
    { "type": "text",      "bind": "form.formNo",   "x": 80, "y": 20, "w": 50, "h": 6, "align": "right", "font": "default" },
    { "type": "title",     "text": "{{ meta.title }}", "x": 0, "y": 30, "w": 210, "h": 12, "align": "center" },
    { "type": "table",     "bind": "form.details",  "x": 18, "y": 60, "w": 174, "h": 120,
      "columns": [
        { "key": "seq",       "label": "序号", "width": 12, "align": "center" },
        { "key": "title",     "label": "事项", "width": 60, "align": "left"   },
        { "key": "amount",    "label": "金额", "width": 30, "align": "right", "type": "money" }
      ]
    }
  ]
}
```

**约束**（V1 范围）：

- 组件类型白名单：`text` / `title` / `image` / `line` / `rect` / `table` / `qrcode` / `barcode` / `html` / `pagebreak` / `header` / `footer` / `pagenum`
- 绑定语法：`{{ form.totalAmount | money }}`（JSONPath + 过滤器）
- 过滤器 V1：`money` / `date` / `datetime` / `upper` / `lower` / `default` / `chinese_money`（金额大写）
- 表达式 V1：**不**支持 `IF/SUM/COUNT`（V2 再做）

---

## 五、接口设计

### 5.1 模板管理（`/api/v1/admin/print-templates/*`）

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| `GET`    | `/admin/print-templates`           | `print:template:read`  | 列表（按 doc_type/code 过滤） |
| `GET`    | `/admin/print-templates/{id}`      | 同上                    | 详情 |
| `POST`   | `/admin/print-templates`           | `print:template:write` | 创建 |
| `PUT`    | `/admin/print-templates/{id}`      | 同上                    | 更新（自动存版本快照） |
| `DELETE` | `/admin/print-templates/{id}`      | `print:template:admin` | 软删（status=archived） |
| `POST`   | `/admin/print-templates/{id}/publish` | `print:template:admin` | 发布（draft→active） |
| `POST`   | `/admin/print-templates/{id}/rollback` | `print:template:admin` | 回滚到指定版本（V2） |
| `POST`   | `/admin/print-templates/seed`      | `print:template:admin` | 一键加载 presets/ |

### 5.2 运行时（`/api/v1/print/*`）— 业务模块调这里

| 方法 | 路径 | 权限 | 用途 |
|---|---|---|---|
| `POST` | `/print/preview` | `print:document:read`  | 返回 HTML 字符串（用于浏览器预览/打印） |
| `POST` | `/print/pdf`     | `print:document:export`| 返回 PDF 字节流（`application/pdf`） |
| `POST` | `/print/log`     | `print:document:read`  | 业务方主动写日志（成功/失败） |

### 5.3 请求/响应模型

```python
class PrintRequest(BaseModel):
    templateCode: str                              # 推荐用 code 寻址（不绑死 id）
    data: dict                                     # 业务数据（按模板 vars 声明）
    options: Optional[PrintOptions] = None

class PrintOptions(BaseModel):
    paper: Optional[str] = None                    # 临时覆盖纸型
    copies: int = 1
    watermark: Optional[str] = None                # 文字水印
    renderMode: str = "pdf"                        # "html" | "pdf"  内部路由
    sourceModule: Optional[str] = None             # 调用方模块名
    sourceId: Optional[str] = None                 # 业务单据 ID
```

**寻址策略**：优先用 `templateCode`（业务含义稳定）；**不**暴露 `templateId` 给业务方（DB id 容易变）。

### 5.4 响应（流式）

```python
@router.post("/print/pdf")
async def print_pdf(req: PrintRequest, ...):
    pdf, fname = await service.render_pdf(req, current_user)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"; filename*=UTF-8\'\'{fname}',
            "X-Print-Log-Id": str(log_id),           # 调试用：前端可回传
        },
    )
```

---

## 六、引擎架构

### 6.1 三层调用链

```
[业务模块]
   │  printApi.pdf({ templateCode: 'reimbursement_v1', data: {...} })
   ▼
[Frontend SDK: print.ts]                          ← 唯一入口
   │  http.post('/api/v1/print/pdf', payload, { responseType: 'blob' })
   ▼
[Router: /api/v1/print/pdf]
   │  require_permission('print:document:export')
   ▼
[Service: print_runtime.service.render_pdf]
   │
   │  ① 加载模板（缓存命中走 Redis，否则 DB）
   │  ② 装载数据：模板里声明 source='system' 的变量走 SystemVars；其它走 DataResolver 注册中心
   │  ③ 鉴权：模板级 ACL（V1 用 doc_type 级；V2 做行级）
   │  ④ 渲染：RendererRegistry.get('pdf').render(template, data, ctx)  → bytes
   │  ⑤ 审计：写 print_logs（成功 + 失败）
   ▼
[Response: application/pdf stream]
```

### 6.2 核心抽象

```python
# protocols.py
from typing import Protocol, Any

class Renderer(Protocol):
    """模板 → 输出字节流"""
    name: str                                       # 'pdf' | 'html' | 'image'
    mime_type: str
    async def render(self, template: dict, data: dict, ctx: RenderContext) -> bytes: ...

class DataResolver(Protocol):
    """业务单据 ID → 业务数据 dict"""
    doc_type: str                                   # 'contract' | 'reimbursement' | ...
    async def resolve(self, identifier: Any, ctx: BindContext) -> dict: ...

class VariableProvider(Protocol):
    """系统变量提供方"""
    name: str
    async def provide(self, ctx: BindContext) -> dict: ...
```

```python
# registry.py —— 注册中心（启动时由 lifespan 装载）
from app.core.print.registry import RendererRegistry, ResolverRegistry, ProviderRegistry

# 在某业务模块的 startup 钩子里：
RendererRegistry.register(MyRenderer())           # name='pdf'
ResolverRegistry.register(ContractResolver())     # doc_type='contract'
ProviderRegistry.register(CompanyInfoProvider())  # name='company'
```

### 6.3 渲染器实现

**V1 只做两个 Renderer**：

1. **`HtmlRenderer`** —— 用 Jinja2 把 `body[]` 渲染成 HTML
   - 适合：浏览器内预览、客户端再走 `window.print()`
   - 实现：`backend/app/modules/print_runtime/renderers/html_renderer.py`
2. **`PdfRenderer`** —— 用 reportlab 把 `body[]` 渲染成 PDF
   - 适合：服务端真 PDF 导出
   - 实现：`backend/app/modules/print_runtime/renderers/pdf_renderer.py`
   - 中文字体：`UnicodeCIDFont("STSong-Light")`（与 `invoice_verify/cert_generator.py` 同款）

**V2 才做的 Renderer**：
- `WeasyPrintRenderer`（HTML+CSS → PDF，支持更复杂样式）
- `ImageRenderer`（单页 → PNG/JPG，存档用）
- `PclRenderer` / `EscPosRenderer`（物理打印机指令）

### 6.4 解析器（Resolver）实现

```python
# contract_resolver.py
class ContractResolver:
    doc_type = "contract"
    async def resolve(self, identifier, ctx):
        # identifier 可能是 int (DB id) 或 str (合同编号)
        c = await contract_service.get_contract(ctx.db, int(identifier))
        return _contract_to_dict(c)
```

V1 必须实现的 4 个 Resolver（覆盖 4 个有"打印"需求的业务模块）：
- `ContractResolver` / `ReimbursementResolver` / `ExpenseResolver` / `InvoiceResolver`

**V2 才做的**：`ProjectResolver` / `ReceivableResolver` / `ClientResolver` —— 按需添加。

### 6.5 业务模块如何"零成本接入"

**两种集成模式**，业务方自选：

**模式 A（推荐，V1 主推）**：业务方自己组装 data，UDPE 只管渲染

```ts
// ReimburseDetail.vue
const data = {
  form: form.value,
  details: details.value,
  applicant: currentUser.value,
}
const { blob, filename } = await printApi.pdf({
  templateCode: 'reimbursement_v1',
  data,
  options: { sourceModule: 'reimbursement', sourceId: String(form.value.formId) },
})
// 下载 / 预览
```

**模式 B**：业务方只传 ID，UDPE 内部用 Resolver 拉数据

```ts
const { blob } = await printApi.pdf({
  templateCode: 'reimbursement_v1',
  data: { _resolver: { docType: 'reimbursement', id: 12345 } },
})
```

模式 B 优势：业务方不用关心数据组装；劣势：UDPE 跟业务模块耦合更深（要认识所有 doc_type）。V1 主推模式 A，模式 B 作为可选增强。

---

## 七、SDK 设计（前端）

### 7.1 唯一入口 `frontend/src/api/print.ts`

```ts
import { http } from '@/utils/request'

export interface PrintOptions {
  copies?: number
  watermark?: string
  sourceModule?: string
  sourceId?: string
  paper?: string
  renderMode?: 'html' | 'pdf'
}

export interface PrintRequest {
  templateCode: string
  data: Record<string, any>
  options?: PrintOptions
}

export const printApi = {
  /** 浏览器预览（返回 HTML 字符串，调用方塞到 iframe） */
  async preview(req: PrintRequest): Promise<{ html: string; templateId: number; logId: number }> {
    const r: any = await http.post('/print/preview', req)
    return { html: r.html, templateId: r.templateId, logId: r.logId }
  },

  /** 导出 PDF（返回 Blob 与后端给的文件名） */
  async pdf(req: PrintRequest): Promise<{ blob: Blob; filename: string; logId: number }> {
    // 用原生 axios 拿 blob（避开业务 http 拦截器对 blob 的特殊处理）
    const axios = (await import('axios')).default
    const userStore = (await import('@/stores/user')).useUserStore()
    const base = (import.meta.env?.VITE_API_BASE as string | undefined) || '/api/v1'
    const resp = await axios.post(`${base}/print/pdf`, req, {
      responseType: 'blob',
      headers: userStore.token ? { Authorization: `Bearer ${userStore.token}` } : {},
    })
    const cd = resp.headers['content-disposition'] || ''
    const m = cd.match(/filename\*=UTF-8''([^;]+)|filename="([^"]+)"/)
    const filename = m ? decodeURIComponent(m[1] || m[2]) : `${req.templateCode}.pdf`
    return { blob: resp.data as Blob, filename, logId: Number(resp.headers['x-print-log-id']) || 0 }
  },

  /** 模板管理（仅 admin） */
  listTemplates: (params?: { docType?: string; status?: string }) =>
    http.post<{ list: any[]; total: number }>('/admin/print-templates', params || {}),
  getTemplate: (id: number) =>
    http.post<any>('/admin/print-templates/detail', undefined, { params: { id } }),
  createTemplate: (data: any) =>
    http.post<{ id: number }>('/admin/print-templates', data),
  updateTemplate: (id: number, data: any) =>
    http.post<{ id: number }>('/admin/print-templates/update', data, { params: { id } }),
  deleteTemplate: (id: number) =>
    http.post('/admin/print-templates/delete', { id }),
  publishTemplate: (id: number) =>
    http.post('/admin/print-templates/publish', { id }),
}
```

**关键决策**：
- 业务模块**只能**通过 `printApi` 接触打印；**禁止**直接 `http.post('/print/...')`（ESLint 规则兜底）
- 现有 `InvoiceDetail.printInvoice` 等函数**保留不动**（兼容），但新代码必须用 SDK

### 7.2 预览组件

```vue
<!-- PrintPreviewDialog.vue (V1) -->
<template>
  <el-dialog v-model="visible" :title="title" width="900px" top="5vh">
    <div class="toolbar no-print">
      <el-radio-group v-model="zoom">
        <el-radio-button :value="0.6">60%</el-radio-button>
        <el-radio-button :value="0.8">80%</el-radio-button>
        <el-radio-button :value="1">100%</el-radio-button>
        <el-radio-button :value="1.25">125%</el-radio-button>
      </el-radio-group>
      <el-button @click="onPrint">🖨 浏览器打印</el-button>
      <el-button type="primary" @click="onDownload">📄 下载 PDF</el-button>
    </div>
    <div class="paper" :style="{ transform: `scale(${zoom})` }">
      <iframe v-if="html" :srcdoc="html" frameborder="0" />
    </div>
  </el-dialog>
</template>
```

---

## 八、事件机制

UDPE 提供**三阶段钩子**，不绑死任何具体业务：

| 阶段 | 钩子 | 时机 | 用途 |
|---|---|---|---|
| Pre-render | `on_pre_render(template, data, ctx)` | 渲染前 | 鉴权 / 数据脱敏 / 注入额外变量 |
| Post-render | `on_post_render(template, data, ctx, output)` | 渲染后 | 存档 / 推送到 OSS / 通知业务方 |
| On-error | `on_render_error(template, data, ctx, exc)` | 失败时 | 告警 / 重试 / fallback |

```python
# 用法示例：在 reimbursement 模块注册事件
@EventBus.on('udpe.post_render')
async def archive_pdf(template, data, ctx, output: bytes):
    if ctx.source_module == 'reimbursement':
        await storage.put(f"print/{ctx.source_id}.pdf", output)
```

V1 用**内存事件总线**（asyncio + dict）；V2 改 SSE 推送 + Redis Pub/Sub。

---

## 九、依赖关系（零冲突原则）

### 9.1 后端新增依赖

| 依赖 | 来源 | 是否需要装 |
|---|---|---|
| `reportlab` | 已有（`requirements.txt` 第 19 行） | **不需要** |
| `Jinja2` | FastAPI 自带依赖 | **不需要** |
| `weasyprint` | 暂无 | V2 再说 |

**V1 不引入任何新依赖**。这是硬性约束。

### 9.2 前端新增依赖

**V1 不引入任何新依赖**。预览用原生 `<iframe srcdoc>`，PDF 下载用 axios blob。

V2 才考虑：`pdf.js`（PDF 预览）、`vue-draggable`（设计器拖拽）。

### 9.3 冲突面

| 现有功能 | UDPE 接入后 | 是否冲突 |
|---|---|---|
| `InvoiceDetail.printInvoice` iframe 方案 | 保留不动，UDPE 提供 `printApi.pdf` 作为新选项 | **零冲突** |
| `ReimburseDetail.onNativePrint` 浏览器打印 | 保留作为"快速打印"入口；UDPE 提供真 PDF 下载 | **零冲突** |
| `TemplateManager.vue` 报销模板管理 | 保留报销模板（业务模板）；UDPE 管打印模板（基础设施模板） | **零冲突**（两类模板） |
| `audit_logs` 审计中间件 | UDPE 写 `print_logs`（更专业子集），audit 中间件继续打 `print.*` 写接口 | **零冲突** |
| 合同 `service.download_contract` 端点 | 保留为"业务 PDF"（合同摘要）；UDPE 通用模板也能产合同 PDF | **共存**，推荐未来迁移 |

---

## 十、扩展点（未来演进路线）

| 扩展点 | 当前（V1） | V2 | V3 |
|---|---|---|---|
| **设计器** | ❶ 无（手写 JSON） | ❷ 简化版（拖拽 + 属性面板） | ❸ 完整版（撤销重做 + 组件库 + 条件显示） |
| **表达式** | ❶ `{{ path \| filter }}` | ❷ `IF / ELSE / FOR` 基础表达式 | ❸ 完整表达式语言（含自定义函数） |
| **数据源** | ❶ 业务模块组装 data | ❷ Resolver 模式（ID 自动拉） | ❸ GraphQL/外部 API 接入 |
| **渲染器** | ❶ PDF + HTML | ❷ WeasyPrint + Image | ❸ PCL/ESC-POS（物理打印机） |
| **打印队列** | ❶ 同步生成 | ❷ 异步 + Worker | ❸ 分布式队列 + 优先级 |
| **数字签名** | ❶ 无 | ❷ 占位字段 | ❸ 真实 PDF 数字签名 |
| **国际化** | ❶ 中文为主 | ❷ 多语言字典 | ❸ RTL + 复杂文种 |
| **多租户 / SaaS** | ❶ 单租户 | ❷ 模板按部门隔离 | ❸ 完整多租户 |
| **可视化监控** | ❶ `print_logs` 列表 | ❷ 趋势图 + 失败告警 | ❸ 实时大屏 |
| **包发布** | ❶ 单仓内 `core/print` | ❷ 抽 `packages/print-core` | ❸ 独立 npm + PyPI 包 |

每个扩展点都是**独立可插拔的**：V1 上线时，V2/V3 的扩展点文件可以**预先创建但留空**或**完全不存在**——UDPE 不会因为缺这些文件而运行失败。

---

## 十一、与现有系统的集成方案

### 11.1 路由挂载

```python
# main.py（V1 实施时改）
app.include_router(print_runtime.router, prefix="/api/v1/print", tags=["打印引擎"])
# 模板管理挂在 admin 下，不新增顶层路由
app.include_router(print_runtime.admin_router, prefix="/api/v1/admin/print-templates", tags=["打印模板"])
```

### 11.2 权限码（新增 4 个）

```sql
INSERT INTO permissions (code, resource, action, name) VALUES
  ('print:template:read',   'print', 'read',   '查看打印模板'),
  ('print:template:write',  'print', 'write',  '编辑打印模板'),
  ('print:template:admin',  'print', 'admin',  '管理打印模板（发布/删除）'),
  ('print:document:read',   'print', 'read',   '预览单据'),
  ('print:document:export', 'print', 'export', '导出单据 PDF');
```

V1 实施时**一次性 seed**（脚本：`backend/app/scripts/seed_print_perms.py`），不修改 `requirements.txt` 之类。

### 11.3 业务模块接入（V1 只做 1 个示范）

**ReimburseDetail.vue**（示范迁移）：

```ts
// before:
async function onDownloadPDF() { onNativePrint() }  // 伪 PDF

// after:
import { printApi } from '@/api/print'
async function onDownloadPDF() {
  pdfBusy.value = true
  try {
    const { blob, filename } = await printApi.pdf({
      templateCode: 'reimbursement_v1',
      data: {
        form: form.value,
        details: details.value,
        applicant: currentUser.value,
        company: { name: '数智化管理系统' },
      },
      options: { sourceModule: 'reimbursement', sourceId: String(form.value.formId) },
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = filename
    a.click(); URL.revokeObjectURL(url)
    ElMessage.success(`已下载 ${filename}`)
  } catch (e: any) {
    ElMessage.error(e?.message || 'PDF 生成失败')
  } finally { pdfBusy.value = false }
}
```

**`onNativePrint` 保留**（快速打印入口），但 `onDownloadPDF` 改用 SDK。

**`InvoiceDetail.printInvoice` 保留不动**（用户原始 PDF 是合同附件，UDPE 管"模板化打印"是另一个需求）。

### 11.4 模板管理 UI

新增路由 `/admin/print-template`（V1 只做列表 + JSON 编辑器）：

```
/admin/print-template
  → PrintTemplateList.vue
      - 左侧：doc_type 分类树（合同/报销/费用/发票/自定义）
      - 右侧：模板列表（name / version / status / 更新时间 / 操作）
      - 顶部按钮：新建 / 加载预置 / 导出 / 导入
  → PrintTemplateEditor.vue（V1 简单 JSON 编辑器 + 实时预览）
```

**V1 不上设计器**——这是关键约束，避免第一阶段膨胀。

### 11.5 审计

- **业务操作**（创建/更新/发布/删除模板）由现有 `AuditLogMiddleware` 自动打 `audit_logs`（`resource_type='print_template'`）
- **运行操作**（预览/导出 PDF/失败）由 UDPE 写 `print_logs`（更专业 schema，含 elapsed_ms、pdf_size）

---

## 十二、性能与稳定性

| 维度 | V1 目标 | 实现手段 |
|---|---|---|
| 单 PDF 生成 | < 2s（5 页内） | reportlab 单进程 + 模板 Redis 缓存（5 min TTL） |
| 并发 | 10 QPS | FastAPI async + DB 连接池（20） |
| 缓存命中 | 95%+ | `cache:print:template:{code}` Redis key |
| 失败率 | < 1% | 全链路 try/except + 失败写 print_logs + 返回 200 + 错误体 |
| 大文档 | < 10s（50 页） | 同步生成长文档；V2 上 async worker |
| 10000 张连续打印 | V2 实现 | 队列 + 多 worker |

---

## 十三、分阶段开发计划

### 阶段 2（ChatGPT 流程 2）— 数据库与接口（**M1 前半周 ~ 1 周**）

> 对应 ChatGPT 建议的"生成数据库与接口"步骤。
> 目标：先有"骨架"（DB 表 + REST 端点 + 权限码），跑通最小调用链，但还没真渲染。
> 这一步不交付业务价值，只让"接口契约"稳定下来——后续所有阶段都按这个契约走。

| 任务 | 时间 |
|---|---|
| alembic migration：`print_templates` / `print_template_versions` / `print_logs` 三表 | 0.5d |
| 权限码 seed 脚本：5 个新权限（`print:template:read/write/admin`、`print:document:read/export`） | 0.5d |
| `core/print/` 抽象层：protocols / registry / context / exceptions（只空壳，能 import） | 0.5d |
| `router.py` 全部端点定义 + 鉴权 + 输入校验（service 返回 mock 占位数据） | 1d |
| OpenAPI 文档自动生成（FastAPI 自带） | 0.5d |

**完成定义**：5 个权限码在 PG，3 张表在 PG，6 个端点 OpenAPI 可见，curl 调用能拿到 mock 响应。

---

### 阶段 3（ChatGPT 流程 3）— 核心引擎（**M1 后半周 ~ 1 周**）

> 对应 ChatGPT 建议的"生成核心引擎"步骤。
> 目标：注册中心、3 类 Protocol、Jinja2 / reportlab 两种 Renderer、4 个业务 Resolver 全部跑通。
> 业务方此时**还没接入**，但引擎已经能独立跑端到端（用预置模板 + mock data）。

| 任务 | 时间 |
|---|---|
| Renderer / Resolver / VariableProvider 三个 Protocol + Registry 实现 | 1d |
| `HtmlRenderer`（Jinja2 渲染 body[] → HTML） | 0.5d |
| `PdfRenderer`（reportlab 渲染 body[] → PDF bytes，STSong-Light 中文字体） | 1.5d |
| 4 个业务 Resolver：ContractResolver / ReimbursementResolver / ExpenseResolver / InvoiceResolver | 1d |
| `service.py` 编排：模板加载（Redis 缓存）→ 数据装载 → 渲染 → 写 print_logs | 1d |

**完成定义**：直接调  带预置模板 + 真实合同/报销/费用/发票 ID，能拿到真 PDF。

**目标**：业务模块能用 `printApi.pdf()` 拿到真 PDF。

| 周 | 任务 | 验收 |
|---|---|---|
| W1 D1-2 | DB migration（`print_templates` / `print_template_versions` / `print_logs` 三表） | alembic upgrade ok，PG 里能看到表 |
| W1 D3-4 | 权限码 seed（5 个新权限） | seed 脚本能跑幂等 |
| W1 D5 | `core/print/` 抽象层（protocols / registry / context / exceptions） | 单测覆盖 registry 注册/查询 |
| W1 D6-7 | `pdf_renderer.py`（reportlab）+ `html_renderer.py`（Jinja2） | 单测：3 种组件类型（text/table/title） |
| W2 D1-2 | `service.py` 编排 + 4 个 Resolver（Contract/Expense/Reimbursement/Invoice） | 单测：每个 resolver 能跑 |
| W2 D3 | `router.py`（`/print/preview` `/print/pdf`） + `/admin/print-templates` CRUD | 端到端：curl 调通 |
| W2 D4 | `presets/` 3 个预置 JSON（合同/报销/发票） | seed 脚本加载 3 个模板 |
| W2 D5 | 前端 `api/print.ts` SDK | 单元测 + 浏览器实测 |
| W2 D6 | `ReimburseDetail.vue` 迁移示范（`onDownloadPDF` 改用 SDK） | 浏览器点"下载 PDF"拿到真 PDF 字节流 |
| W2 D7 | 端到端验收：build + 重启容器 + 浏览器实测 | `print_logs` 表有记录 |

**明确不做**：
- 设计器（V2）
- 表达式（V2）
- 异步队列（V2）
- 数字签名（V3）
- 物理打印机（V3）

**完成定义（DoD）**：
- 业务方能写 `printApi.pdf({ templateCode, data })` 拿到真 PDF
- 模板在 admin 后台能 CRUD
- `print_logs` 表有运行记录
- 不破坏任何现有功能

---

### 阶段 4（ChatGPT 流程 4）— 模板设计器（**M3 阶段，4 周**）

> 对应 ChatGPT 建议的"开发模板设计器"步骤。
> 目标：业务人员（非工程师）能自助配置模板，不用手写 JSON。

| 任务 | 时间 |
|---|---|
| 设计器 V1：三栏布局（组件库 / 画布 / 属性面板）+ 拖拽添加 + 坐标定位 | 2w |
| 属性面板：字体 / 字号 / 对齐 / 边框 / 填充 / 数据绑定 | 1w |
| 数据绑定 UI：点选字段 → 绑定到 JSON path；表达式 V2（IF / FOR） | 1w |

**M2 配套**：阶段 5 之前必须有管理 UI（哪怕最简 JSON 编辑器），否则业务方拿不到模板。
所以实际节奏是 M1 末 → M2 初先上"JSON 编辑器 + 实时预览"（5 天），再进入 M3 完整设计器。

---

### 阶段 5（ChatGPT 流程 5）— 接入现有业务（**M1 末 + M2 阶段，1.5 周**）

> 对应 ChatGPT 建议的"接入发票、报销等现有业务"步骤。
> 目标：把 4 处现有打印 hack 全部替换成 SDK 调用。

| 任务 | 时间 |
|---|---|
| M1 末：`ReimburseDetail.vue` 迁移示范（`onDownloadPDF` 改用 SDK） | 0.5d |
| M2 初：`ExpenseDetail.vue` 迁移 | 0.5d |
| M2 初：`InvoiceDetail.printInvoice` 增加"UDPE 真 PDF"按钮（保留原 iframe 不破坏） | 0.5d |
| M2 初：`ContractDetail` 增加"按合同模板打印"按钮 | 0.5d |
| M2 中：移除所有现有 hack（如能证明完全无回归；否则保留兜底） | 1d |
| 端到端回归：4 个迁移点全部走 SDK 拿到真 PDF | 1d |

**完成定义**：浏览器实测 4 个模块的"打印 / 导出 PDF"按钮全部能拿到 PDF 字节流，0 回归。

**与阶段 4/5 同步推进的 M2 工作（设计器之前的过渡 UI，3 周）**：

| 任务 | 时间 |
|---|---|
| `PrintTemplateList.vue` + `PrintTemplateEditor.vue`（JSON 编辑器 + 实时预览） | 1 周 |
| 数据绑定表达式 V2：`IF` / `FOR` / `SUM` | 1 周 |
| 模式 B（Resolver 模式）上线 | 0.5 周 |
| 业务模块批量迁移：Expense / InvoiceDetail / ContractDetail | 0.5 周 |

---

### 阶段 6（ChatGPT 流程 6）— 高级功能（**M3 末 + M4+，按需排期**）

> 对应 ChatGPT 建议的"完善打印、PDF、电子签章、批量任务等高级功能"步骤。

| 任务 | 优先级 |
|---|---|
| 异步队列（FastAPI BackgroundTasks + Redis Stream + SSE 进度推送） | P0 |
| 批量打印（） | P0 |
| WeasyPrintRenderer（替换/补充 reportlab，处理复杂 CSS） | P1 |
| PDF 数字签名（用  或 ） | P1 |
| 二维码 / 条码组件（用  + ） | P1 |
| 物理打印：Windows / macOS / Linux CUPS 桥接 | P2 |
| PDF/A 归档 | P2 |
| 多租户 + SaaS 化（拆 monorepo 抽 ） | P3 |

不做（除非明确要求）：
- 在线协同编辑（多人同时编辑同一模板）
- 版本回滚 UI（V2 用  表存历史，V3 再做 UI）

| 任务 | 时间 |
|---|---|
| FastAPI BackgroundTasks + Redis Stream 异步生成 | 1 周 |
| SSE 推送进度（前端进度条） | 0.5 周 |
| 模板设计器 V1（三栏布局 + 拖拽 + 属性面板 + 数据绑定） | 2.5 周 |

---

## 十四、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| reportlab 中文渲染缺字 | 低 | 中 | 复用 `UnicodeCIDFont("STSong-Light")`，与 `cert_generator.py` 同款 |
| 业务方对"模板"概念抗拒 | 中 | 中 | 阶段 1 预置 3 套，业务方不改；阶段 2 再推广自定义 |
| `printApi` 与现有 `http.post` 风格不一致 | 低 | 低 | SDK 内部封装 axios blob，外部 API 保持简洁 |
| 模板 schema V1 → V2 升级不兼容 | 中 | 中 | schema 带 `version` 字段；migration 脚本明确写升级路径 |
| reportlab 复杂布局表达力差 | 高 | 中 | V2 引入 WeasyPrint（HTML+CSS 渲染），renderer 可替换 |
| 大文档同步生成阻塞 API 进程 | 中 | 中 | 阶段 3 之前用 FastAPI 异步 + 短超时保护；阶段 3 切队列 |
| 权限码与现有命名冲突 | 极低 | 低 | `print:*` 前缀隔离 |

---

## 十五、关键决策记录（ADR 摘要）

| # | 决策 | 理由 |
|---|---|---|
| ADR-1 | UDPE 是 `core/print` + `modules/print_runtime`，**不是** 单一 `modules/print` | 核心抽象跨模块复用，必须放 core |
| ADR-2 | V1 **不**做设计器 | 设计器是 3~4 周单独投入，V1 不该扛 |
| ADR-3 | 寻址用 `templateCode` **不**用 `id` | 业务 ID 稳定；DB id 易变 |
| ADR-4 | Renderer / Resolver / Provider 三类**注册中心**模式 | 业务模块自己 register，零侵入 |
| ADR-5 | 业务模块接入推**模式 A**（业务方组装 data） | UDPE 跟业务模块解耦最彻底 |
| ADR-6 | 审计分两套：业务操作走 `audit_logs`，运行操作走 `print_logs` | schema 差异大，硬合一会污染 audit_logs |
| ADR-7 | V1 **不**引入新依赖 | reportlab + Jinja2 已存在；过早引入 WeasyPrint 风险大 |
| ADR-8 | `reimbursement_templates` / `invoice_templates` 业务模板**保留** | UDPE 管的是打印模板，跟业务模板职责不同 |
| ADR-9 | 现有 4 处打印 hack **全部保留** | 零破坏；新代码用 SDK，旧代码不动 |
| ADR-10 | 包结构**不**立刻抽 monorepo | 提前抽收益小、基础设施没有；V3 再说 |

---

## 十六、评审决策记录（已通过）

> 评审人：项目负责人
> 评审时间：M1 启动前
> 全部 5 个问题已决策，本节为最终基线

| # | 议题 | 决策 | 影响 |
|---|---|---|---|
| 1 | M1 不做项（设计器/表达式/异步/数字签名/物理打印） | **同意推迟到 M2+** | M1 范围冻结 = 阶段 2 + 3 + 阶段 5 第一个示范 |
| 2 | 第一个迁移示范模块 | **`InvoiceDetail`**（用户最多） | 不再做 ReimburseDetail（第二个示范可后续补） |
| 3 | M1 预置模板套数 | **4 套**：合同 / 报销 / 发票 / 费用 | presets/ 目录 4 个 JSON |
| 4 | data 字段是否强校验 | **V1 不强制，但必须预留 Schema 能力** | 模板 schema 加 `inputSchema` 字段（JSON Schema draft-07），V1 不启用校验逻辑；V2 启动校验时无需改 schema |
| 5 | print_logs.request_data 字段 | **保留完整快照（含金额），不做脱敏** | 业务方需自评合规；PII 风险由业务侧 SOP 控制 |

**ADR-11 补充决策**：模板 schema 增加可选字段 `inputSchema: JSONSchema`，V1 引擎不调用校验器（保持灵活），V2 启动时只需在 `RenderContext` 注入 `jsonschema` 库即可启用。

---

## 十七、文档与交付物

每个阶段交付：
- 本设计文档随实现迭代更新（章节 13 进度表）
- 每个阶段产出 `plans/udpe-design/outputs/m{N}.md`（实现总结 + 自测报告）
- 端到端验证脚本（`scripts/e2e_udpe_m1.py`）
- 模板预置 JSON（`backend/app/modules/print_runtime/presets/*.json`）
- 模板管理 UI 截图

---

**总预算**：阶段 1（2 周）+ 阶段 2（3 周）+ 阶段 3（4 周） = **9 周（约 2 个月）**全功能上线。V1 之后每个业务模块接入**几乎零成本**（1 行 SDK 调用 + 1 个 schema JSON）。

**最重要的承诺**：**V1 期间，0 行现有业务代码被破坏**。
