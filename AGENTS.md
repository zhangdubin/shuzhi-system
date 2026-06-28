# AGENTS.md — 数智化管理系统

> 项目级工作约定（仅本仓库内有效）。跨项目的通用经验请写到 coder agent memory。

## 项目结构

```
数智化系统new/
├── frontend/   # Vue 3 + Vite + Element Plus + TS（业务前端）
├── backend/    # Python 后端（FastAPI/SQLAlchemy，看 app/）
├── design/     # 静态 HTML 设计稿（所有页面的视觉基准，1:1 复刻的 source of truth）
├── deploy/     # Docker / 部署相关
├── doc/        # 文档自动生成脚本（doc-filelist.js 等）
├── 404/        # 静态 404 页
└── README.md
```

**关键约束**：
- 设计稿在 `design/*.html`，**纯 HTML + 公共 CSS（`design/assets/common.css`）**；
- 前端复刻任务是**对照 design/ 1:1 还原**，不是 free-style 设计。
- 前端不要无端引入新依赖（拖拽库等），能省则省。
- 后端 Schemas 在 `backend/app/modules/<domain>/schemas.py`，前端类型在 `frontend/src/api/modules.ts`，
  **两端类型可能不一致**（前端早期用了简化版），复刻时按前端实际渲染需要补结构即可，不要直接同步后端 camelCase。

## 前端复刻任务的标准工作流

接到"1:1 复刻"任务时，按这个顺序：

1. **看设计稿**：`design/<domain>*.html`（如 `design/contract-detail.html`、`design/invoice-template-edit.html`）。
2. **看现有标杆实现**：通常在 `frontend/src/views/<domain>/`，找已经做完的详情/列表页（最常用 `ContractDetail.vue`）。
3. **看设计令牌**：`frontend/src/assets/styles/`（`variables.scss` 颜色 / 圆角 / 阴影，`detail.scss` 详情页 / 编辑器样式）。
4. **看类型 + 路由**：`frontend/src/api/modules.ts` 和 `frontend/src/router/index.ts`。
5. **写 `.vue`**，复用 `detail-hero` / `detail-tabs` / `detail-section` / `info-grid` / `form-section` / `form-row-3` / `form-foot` / `tag-*`。
6. **注册路由**（注意 name 不要和已有路由冲突）。
7. **跑自检**：`cd frontend && npm run build 2>&1 | tail -10`，必须 0 错误。
8. **写 `deliverable.md`** 到 `plans/.../outputs/<task-name>/deliverable.md`。
9. **更新 board.md**（追加 `---` 分割 + 时间戳条目）。
10. **向 parent session 报回**：`mavis communication send --to <parent> --command prompt --content "..."`。

## 关键设计令牌（不要新造）

```scss
$color-primary: #4F6BFF;        // 蓝
$color-primary-bg: rgba(79,107,255,0.08);  // 浅蓝
$gradient-brand: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);  // 蓝紫渐变
$radius-lg: 14px;                // 卡片圆角
$font-family-mono: 'SF Mono'...  // 编号/单据号
```

## 路由命名约定

- 列表：`/contract/list`, `/invoice/template`
- 详情：`/contract/:id`, `/invoice/template/:id`（name: `ContractDetail`, `InvoiceTemplateDetail`）
- 编辑：`/contract/:id/edit`, `/invoice/template/:id/edit`（name: `ContractEdit`, `InvoiceTemplateEdit`）
- 列表 name 用域+List（如 `ContractList`），**不要**用纯 `Contract`（和路由路径冲突）。

## 类型扩展的破坏性测试

扩展 `api/modules.ts` 里的 `interface Xxx` 时：

- 用 `grep` 全仓找引用方；
- 如果原字段是数组（`fields: string[]`），改成对象数组（`fields: Field[]`）前要确认调用方是否用 `.length` / `.map` / `.filter`；
- **length / ?.** / for-of 兼容；**类型断言 / 解构具体字段**会断。

## 自检命令

```bash
cd frontend && npm run build 2>&1 | tail -10
# 期望：✓ built in <Ns>  且无 TS 错误
```

## 已知坑（项目内）

1. **el-table 没有行拖拽**（Element Plus 不内置）。要拖拽排序需引入 vuedraggable / sortablejs。复刻任务里通常用"上移/下移按钮"代替。
2. **设计稿 V2 形态复杂**（如 `design/invoice-template-edit.html` 三栏：字段库 + 画布 + 属性面板），复刻 V1 一般只做"基础信息 + 字段配置 + 预览 + 底部"，**不要为了对齐 design 把 V2 全做**（任务规格怎么说就怎么做）。
3. **mock 数据兜底**：详情 / 编辑器在 API 失败时回退到 mock 演示数据（用 `*.catch(() => null)` 模式），保证可交互。

## Docker + Vite Dev 是两套独立 chunk 系统

`deploy/docker-compose.yml` 里 `frontend` service 从 `frontend/Dockerfile` build,构建产物 COPY 到 nginx 容器。这意味着:

- `dist/` (本地 `npm run build`) = Docker 容器里看到的内容
- `node_modules/.vite/` (Vite dev server) = Vite 自己服务的 chunks,独立于 Docker

**测试时端口决定看到哪套**:
- `http://localhost:8088` → Docker 容器里 nginx 托管的旧 dist（如果容器在跑）
- `http://localhost:80` → 同上（如果容器映射到 80）
- `node_modules/.vite/` 热重载 → Vite dev server（本地 `npm run dev` 起的）

**修改源码后,Docker 容器不会自动感知,必须 rebuild**:

前端 `dist/` 是 volume 挂载，`npm run build` 即可，不需要重建前端镜像：
```bash
cd frontend && npm run build
# nginx 容器自动读到新 dist/
```

后端必须重建镜像并重启容器：
```bash
cd deploy && docker compose build --no-cache backend
docker compose up -d --no-deps backend
```

**排查线索**: 如果 curl 一个刚加的后端接口返回 `{"detail":"Method Not Allowed"}` (405)，先确认后端容器是否已 rebuild —— 本地改了代码但容器里跑的还是旧镜像。

**Dockerfile context 注意**: `docker-compose.yml` 的 `context: ..` 指向项目根,`dockerfile: frontend/Dockerfile`。Dockerfile 里的 `COPY frontend/ .` 路径相对于项目根。



## 补 CRUD 功能的标准链路

给已有列表页补一个操作（如删除、导入），必须三层一起补：

1. **后端 service** — `backend/app/modules/<domain>/service.py`，写业务函数
2. **后端 router** — `backend/app/modules/<domain>/router.py`，注册端点（注意权限 `require_permission`）
3. **前端 API** — `frontend/src/api/<domain>.ts`，加调用方法
4. **前端页面** — `frontend/src/views/<domain>/<Page>.vue`，加按钮 + 处理函数

**不要只改一端**：后端加了接口但前端没按钮 = 用户看不到；前端加了按钮但后端没接口 = 405 报错。

## 接入已有组件前先检查

项目里有些组件已经写好但**没有接入页面**（如 `ExcelImportDialog.vue`、`WordImportDialog.vue`）。
补功能时先 `find` / `grep` 一下组件目录，看看是否已有现成的，避免重复造轮子。

接入步骤：
1. `import` 组件
2. 加 `ref<boolean>` 控制显隐
3. 页面头部加触发按钮
4. 模板里加 `<XxxDialog v-model="visible" @success="onSuccess" />`
5. 写 success 回调（通常就是刷新列表）

## 删除功能的状态保护

删除按钮不能对所有状态都显示。常见模式：
- `active`（已发布）→ 不显示删除，先归档
- `draft`（草稿）/ `archived`（已归档）→ 可删除

后端也要做同样的校验，防止 API 直接调用绕过前端限制。

## Vue 模板 ref 可选链规范

`InvoiceOcr.vue` 的 `v-if="(result as any).suggestions?.linkToContract"` 写法正确,但里面子元素用了 `(result as any).suggestions.linkToContract`（少 `?.`）——当 `result.value === null` 时,外层 v-if 条件为 false 但 Vue 3 编译时子表达式仍被求值,访问 null 的 `.suggestions` 直接抛 TypeError 导致整组件崩溃。

**规范:模板里访问 ref 的嵌套属性,全程用 `?.`**:
```vue
<!-- 正确 -->
<div v-if="(result as any)?.suggestions?.linkToContract">
  <strong>{{ (result as any)?.suggestions?.linkToContract }}</strong>

<!-- 错误:外层过了但内层仍炸 -->
<div v-if="(result as any).suggestions?.linkToContract">
  <strong>{{ (result as any).suggestions.linkToContract }}</strong>
```

## UDPE 后续方向经验（2026-06-28）

### 多语言 i18n 规范
- 模板组件 text 支持两种多语言格式：
  1. `text: {"zh": "合同", "en": "Contract"}`（dict 格式）
  2. `text: "合同"` + `locales: {"en": "Contract"}`（兼容旧格式）
- 渲染时通过 `options.locale` 参数切换语言
- i18n 模块在 `backend/app/modules/print_runtime/i18n.py`
- grid cells、table headers 也支持多语言

### PDF 导入
- 端点: `POST /admin/print-templates/import/pdf/preview` 和 `/confirm`
- 解析器: `backend/app/modules/print_runtime/importers/pdf_importer.py`
- 用 PyMuPDF 提取文本块坐标和字号，启发式表格检测

### 模板预设
- 预设文件在 `backend/app/modules/print_runtime/presets/`
- 格式: `{version, meta, paper, schemaJson: {body: [...]}}`
- 新增: purchase_order / delivery_note / salary_slip / receipt

### 压测脚本
- `backend/tests/test_print_load.py` — 60 并发，120 请求/端点
- 独立运行: `python -m pytest tests/test_print_load.py -v -s`

### E2E 测试
- `frontend/e2e/print-template.spec.ts` — Playwright 10 个用例
- 配置: `frontend/playwright.config.ts`
