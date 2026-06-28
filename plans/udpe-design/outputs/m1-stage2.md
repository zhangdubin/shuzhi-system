# M1 阶段 2 交付报告：数据库与接口

> 对应 ChatGPT 流程 2 / UDPE 设计文档 §十三 阶段 2
> 完成时间：1 个工作日（原计划 1 周）
> 状态：✅ 完成

## 交付物

### 1. 数据库（3 张新表）

| 表名 | 用途 | 关键字段 |
|---|---|---|
| `print_templates` | 模板主表 | code (unique), doc_type, status, schema_json JSONB, is_default |
| `print_template_versions` | 历史版本快照 | template_id, version, schema_json JSONB |
| `print_logs` | 渲染/导出日志 | template_code, action, status, source_module, request_data JSONB |

**alembic 迁移**：`20260628_0010_add_udpe_print_tables.py`（down_revision: 20260623_1730）

**验证**：
```sql
-- PG 中已建
shuzhi=# \dt print_*
 public | print_logs              | table | shuzhi
 public | print_template_versions | table | shuzhi
 public | print_templates         | table | shuzhi
```

### 2. 权限码（5 个）

| code | resource | action | name |
|---|---|---|---|
| `print:template:read` | print | read | 查看打印模板 |
| `print:template:write` | print | write | 编辑打印模板 |
| `print:template:admin` | print | admin | 管理打印模板（发布/删除） |
| `print:document:read` | print | read | 预览单据 |
| `print:document:export` | print | export | 导出单据 PDF |

`super_admin` 角色自动获得全部 5 个权限（通过现有 `ROLE_PERMS` 列表的 `[p[0] for p in PERMISSIONS]` 模式）。

### 3. 核心抽象（`backend/app/core/print/`）

| 文件 | 内容 |
|---|---|
| `protocols.py` | 3 个 Protocol：`Renderer` / `DataResolver` / `VariableProvider` |
| `registry.py` | 3 个注册中心：`RendererRegistry` / `ResolverRegistry` / `ProviderRegistry` |
| `context.py` | 4 个数据类：`BindContext` / `RenderContext` / `PrintRequest` / `PrintResult` |
| `exceptions.py` | 7 个 UDPE 异常族（3101-3107） |
| `__init__.py` | 公共 API 导出 |

**验证**：单测全过，Protocol 运行时检查通过，Registry 注册/查询正常。

### 4. REST 端点（8 个）

| 方法 | 路径 | 权限 | 状态 |
|---|---|---|---|
| GET | `/api/v1/admin/print-templates` | `print:template:read` | ✅ |
| GET | `/api/v1/admin/print-templates/{tid}` | `print:template:read` | ✅ |
| POST | `/api/v1/admin/print-templates` | `print:template:write` | ✅ |
| POST | `/api/v1/admin/print-templates/update` | `print:template:write` | ✅ |
| POST | `/api/v1/admin/print-templates/publish` | `print:template:admin` | ✅ |
| POST | `/api/v1/admin/print-templates/archive` | `print:template:admin` | ✅ |
| POST | `/api/v1/print/preview` | `print:document:read` | ✅ |
| POST | `/api/v1/print/pdf` | `print:document:export` | ✅ |
| POST | `/api/v1/print/log` | `print:document:read` | ✅ |

**OpenAPI 验证**：
```
$ curl /openapi.json | grep print
/api/v1/admin/print-templates                      [GET, POST]
/api/v1/admin/print-templates/archive              [POST]
/api/v1/admin/print-templates/publish             [POST]
/api/v1/admin/print-templates/update              [POST]
/api/v1/admin/print-templates/{tid}               [GET]
/api/v1/print/log                                 [POST]
/api/v1/print/pdf                                 [POST]
/api/v1/print/preview                             [POST]
```

### 5. 端到端 smoke test（通过）

```
1. GET  /print-templates           → 200, 0 条
2. POST /print-templates           → 200, 创建 id=1 (status=draft)
3. GET  /print-templates           → 200, 1 条
4. POST /print-templates/publish   → 200, status=active
5. POST /print/pdf                 → 200, 36 字节, 头 4 字节 = %PDF
6. POST /print/log                 → 200, 1 条 success, elapsed=0ms, src=invoice
```

## 关键决策（评审通过）

| # | 议题 | 决策 | 实现位置 |
|---|---|---|---|
| 1 | M1 不做项 | 推迟到 M2+ | 本阶段严格按计划做 |
| 2 | 第一个示范模块 | `InvoiceDetail` | M1 阶段 5 第一个迁移点 |
| 3 | 预置模板 | 4 套（合同/报销/发票/费用） | M1 阶段 3 写 4 个 presets JSON |
| 4 | schema 校验 | V1 不强制，预留 `inputSchema` 字段 | `PrintTemplateCreate.inputSchema` 字段已加，V1 不消费 |
| 5 | request_data 完整快照 | 保留（含金额） | `print_logs.request_data` 直接存 `req.data` |

## 暂未实现（按计划 M1 阶段 3 做）

- [ ] HtmlRenderer / PdfRenderer（reportlab 渲染）
- [ ] 4 个业务 Resolver（Contract / Reimbursement / Expense / Invoice）
- [ ] SystemVars Provider
- [ ] 4 套预置模板 JSON（合同/报销/发票/费用）
- [ ] Redis 模板缓存

## 零破坏验证

- 现有 8 个业务模块 router/service 未改动
- 现有 4 处打印 hack 完全未动
- 现有 28 个权限码继续可用
- 现有 audit_logs 继续记录（UDPE 写 print_logs 是子集补充）

## 风险与缓解

| 风险 | 当前状态 | 缓解 |
|---|---|---|
| 后端容器 rebuild 慢 | 实测 30s（缓存命中） | 无需特殊处理 |
| alembic 文件需在容器内可见 | 已通过 `COPY backend/ ./` 包含 | 下次 rebuild 自动带新文件 |
| 5 个新权限码不与现有冲突 | grep 验证通过 | 命名空间 `print:*` 隔离 |
| print_logs.request_data 含敏感字段 | 按评审决策 #5 保留 | 业务方需自评合规 |

## 下一步

**M1 阶段 3 启动**（按计划 1 周）：
1. D1-2: HtmlRenderer (Jinja2) + PdfRenderer (reportlab)
2. D3: SystemVars Provider + 4 个业务 Resolver
3. D4: 4 套预置模板 JSON
4. D5: Redis 模板缓存（沿用 core.cache）
5. D6-7: 端到端验证 + 真实 PDF 字节验证
