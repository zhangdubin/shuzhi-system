# R9 计划：30+ 页面 1:1 复刻 + 全链路打通

> 目标：把整个系统 33 个 design HTML 严格 1:1 转化为可用 Vue 程序，4 个 ocr sub-tabs 走"统一父页面"方案，全链路打通后端 + E2E 100% 通过。
> 范围：A 方案 2（统一父页面设计）+ B 全做（33 个 design）+ C 照跑（E2E + 真后端）

---

## 总体节奏

| 阶段 | 名称 | 工期 | 交付物 |
|---|---|---|---|
| **P1** | 设计系统基线 + 工具链 | 1.5h | `design/common.css` 重构 + `frontend/src/assets/styles/` 统一 |
| **P2** | 父页面 design 统一化 | 2h | 4 个 ocr sub-tab + 业务 6 大模块"列表-详情-编辑"三联屏父页面 design |
| **P3** | 基础页 design 补全 | 2h | Login / Dashboard / 5 错误页 / NoticeCenter 父页面重画 |
| **P4** | 业务页 1:1 转化（Phase A） | 4h | Login + Dashboard + 6 大模块列表页（10 vue）|
| **P5** | 业务页 1:1 转化（Phase B） | 4h | 6 大模块详情 + 编辑（12 vue）|
| **P6** | OCR 4 sub-tab 父页面统一 | 2h | 1 个父页面 design + InvoiceOcr.vue 彻底重写 |
| **P7** | 业务页 1:1 转化（Phase C） | 3h | 客户/AI 中心/admin 8 个 vue |
| **P8** | 通知中心 + AI panel 抽屉 | 1.5h | 4 个 vue |
| **P9** | 后端 E2E 全量重写 + 跑通 | 3h | 14 个 E2E 100% PASS |
| **P10** | 文档 + 上线报告 | 1h | R9-REPORT.md + 更新 GO-LIVE |

**总工期：~24h（约 3 天连续）**

---

## P1 设计系统基线 + 工具链

### 1.1 重构 design/common.css（统一设计令牌）
- 颜色变量：8 个色（primary / primary-bg / success / warning / danger / info / purple / text 三级）
- 字体：sans + mono（统一到 design/common.css，所有 design 文件统一引用）
- 圆角：sm 6 / md 12 / lg 16
- 阴影：sm / md
- 间距：4 / 8 / 12 / 16 / 24
- z-index：sidebar / modal / toast

### 1.2 重构 frontend/src/assets/styles/variables.scss
- 把 scss 变量对齐到 design common.css
- 删 darken()（用 color.adjust 替代）
- 统一 box-shadow、transition 曲线

### 1.3 通用 SCSS mixin 库
- `frontend/src/assets/styles/mixins.scss`：
  - `@mixin card`（统一卡片样式）
  - `@mixin btn-primary` / `btn-outline` / `btn-ghost`
  - `@mixin tag-{color}`（4 状态 tag）
  - `@mixin page-card`（page-card 容器）
  - `@mixin table-base`（统一表格）
  - `@mixin form-field`（统一表单）

### 1.4 公共组件抽取
- `frontend/src/components/common/`：
  - `PageHeader.vue`（h1 + breadcrumb + toolbar slot）
  - `DataTable.vue`（props: columns, data, with-checkbox, with-pagination）
  - `FilterPanel.vue`（props: fields（field[]）, actions slot）
  - `StatusTabs.vue`（props: tabs, v-model:active）
  - `StatCard.vue`（props: label, value, unit, icon, delta）
  - `EmptyState.vue`
  - `TagPill.vue`（props: type（6 色）, label）
  - `FormField.vue`（props: label, required, error）

### 1.5 验证
- `cd frontend && npm run build 0 错`

---

## P2 父页面 design 统一化

### 2.1 业务模块"列表-详情-编辑"父页面 design

**4 个统一父页面模板**（每个都遵循：sidebar + 顶栏 + h1 + breadcrumb + toolbar + content）：

| 父页面 | 适用 | 复用 |
|---|---|---|
| `design/_pattern-list.html` | 6 业务模块列表 | contract / project / expense / receivable / invoice-template / client |
| `design/_pattern-detail.html` | 6 业务模块详情 | 同上 |
| `design/_pattern-create.html` | 6 业务模块创建/编辑 | 同上 |
| `design/_pattern-ai.html` | AI 中心 | AiCenter + 子页 |

**模板内容**（按现有 design 抽出公共结构）：
- sidebar（深色 + 蓝紫激活）
- 顶栏（h1 + breadcrumb + 右侧 toolbar slot）
- content 区（h1 已在顶栏，正文按业务）

### 2.2 OCR 4 sub-tab 统一父页面 design

**新文件：`design/invoice-ocr-parent.html`**
- 顶栏：h1「发票识别」+ breadcrumb「首页 / 发票识别」
- sub-tabs 4 个（智能识别 / 批量上传 / 识别记录 / 查验真伪）
- 工具栏（按 tab 不同，按钮组 + 全局操作）
- content（按 active tab 切换 4 个 content section）

**4 个 sub-section design（嵌入 parent 内的 4 个 section）**：
- `_ocr-1-single.html`：上传区 + stats-row + preview + result（沿用 invoice-ocr.html 内容）
- `_ocr-2-batch.html`：模板选择 + 拖拽 + 队列（沿用 invoice-ocr-batch.html）
- `_ocr-3-records.html`：filter + status-tabs + 表格（沿用 invoice-ocr-records.html）
- `_ocr-4-verify.html`：4 stat + 风险卡 + 表单 + 结果 + 记录（沿用 invoice-ocr-verify.html）

**4 个 content section 共享**：
- 卡片 padding（16px）
- 圆角（12px）
- 字号（12px 表格 / 14px 标题 / 24px 数字）
- 颜色（status 5 色一致）

### 2.3 验证
- 用 `shuzhi-design-preview` 容器（已存在）跑：`curl http://localhost:8090/invoice-ocr-parent.html` 看效果
- 截图给你 review

---

## P3 基础页 design 补全

### 3.1 5 个 design 已有但需要统一化
- `login.html`（已 OK，复用 P1 基线）
- `dashboard.html`（已 OK，复用 P1 基线）
- `error-403.html` / `error-404.html` / `error-500.html` / `error-network.html`（4 个统一风格）

### 3.2 新增 design
- `design/notice-center.html`（通知中心，目前没有）
- `design/_pattern-modal.html`（所有弹窗/抽屉统一样式）
- `design/_pattern-empty.html`（空状态/loading 态）

---

## P4 业务页 1:1 转化（Phase A：基础 + 列表）

### 4.1 改 vue 文件
| Vue | Design | 改动 |
|---|---|---|
| `auth/Login.vue` | `login.html` | 1:1 复刻 |
| `dashboard/Dashboard.vue` | `dashboard.html` | 1:1 复刻 |
| `error/Error403.vue` | `error-403.html` | 1:1 复刻 |
| `error/Error404.vue` | `error-404.html` | 1:1 复刻 |
| `client/ClientList.vue` | 新画 | 1:1 复刻 |
| `contract/ContractList.vue` | `contract.html` | 1:1 复刻 |
| `project/ProjectList.vue` | `project.html` | 1:1 复刻 |
| `expense/ExpenseList.vue` | `sales-expense.html` | 1:1 复刻 |
| `receivable/ReceivableList.vue` | `receivable.html` | 1:1 复刻 |
| `invoice/InvoiceTemplateList.vue` | `invoice-template.html` | 1:1 复刻 |

### 4.2 验证
- `cd frontend && npm run build 0 错`
- 每个页面 playwright 截图 vs design 截图
- 截图给你 review（每页 2 张：1-design-*.png + 2-real-*.png）

---

## P5 业务页 1:1 转化（Phase B：详情 + 编辑）

### 5.1 改 vue 文件
| Vue | Design |
|---|---|
| `contract/ContractCreate.vue` | `contract-create.html` |
| `contract/ContractDetail.vue` | `contract-detail.html` |
| `contract/ContractTemplate.vue` | `template-create.html` |
| `project/ProjectCreate.vue` | `project-create.html` |
| `project/ProjectDetail.vue` | `project-detail.html` |
| `expense/ExpenseCreate.vue` | `sales-expense-create.html` |
| `expense/ExpenseDetail.vue` | 新画（与 contract-detail 共享详情 pattern） |
| `receivable/ReceivableCreate.vue` | `receivable-create.html` |
| `receivable/ReceivableDetail.vue` | `receivable-detail.html` |
| `invoice/InvoiceDetail.vue` | `invoice-detail.html` |
| `invoice/InvoiceTemplateDetail.vue` | 新画（与 contract-detail 共享） |
| `invoice/InvoiceTemplateEdit.vue` | `invoice-template-edit.html` |

### 5.2 验证（同 P4）

---

## P6 OCR 4 sub-tab 父页面统一

### 6.1 改文件
- **`design/invoice-ocr-parent.html`**（新画，统一 4 tab）
- **`frontend/src/views/invoice/InvoiceOcr.vue`**（彻底重写：sub-tabs v-show + 4 sub-section）
- 4 个子组件（BatchUpload / RecordsList / InvoiceVerify / 智能识别）按"统一父页面"语言重写
- 删掉 P1-P5 中子组件的 page-header（统一在 InvoiceOcr.vue 里）
- 路由：`/invoice/ocr/batch` 等仍 redirect 到 `?tab=batch`（保留 1:1 兼容）

### 6.2 验证
- 4 sub-tab 切换：DOM 布局统一（同样的 padding/圆角/字号）
- 截图 4 tab vs design 4 section
- test-14 PASS

---

## P7 业务页 1:1 转化（Phase C：客户/AI/admin）

### 7.1 改 vue 文件
| Vue | Design |
|---|---|
| `client/ClientCreate.vue` | `client-create.html` |
| `ai/AiCenter.vue` | `ai-center.html` |
| `ai/AiAsk.vue` | 新画（在 ai-center pattern 上） |
| `ai/AiRisk.vue` | 新画 |
| `ai/AiTasks.vue` | 新画 |
| `ai/AiAlerts.vue` | 新画 |
| `ai/AiExtract.vue` | `ai-extract-demo.html` |
| `admin/AdminUser.vue` | 新画（admin 列表 pattern） |
| `admin/AdminRole.vue` | 新画 |
| `admin/AdminDept.vue` | 新画 |
| `admin/AdminDict.vue` | 新画 |

### 7.2 验证（同 P4）

---

## P8 通知中心 + AI panel 抽屉

### 8.1 改文件
| Vue | Design |
|---|---|
| `notice/NoticeCenter.vue` | `notice-center.html`（P3 新画） |
| `ai/AiPanelContract.vue` | `ai-panel-contract.html` |
| `ai/AiPanelProject.vue` | `ai-panel-project.html` |
| 新建 `ai/AiPanelContractDrawer.vue` | `ai-panel-contract-drawer.html` |

### 8.2 验证
- 截图 + 交互测试

---

## P9 后端 E2E 全量重写 + 跑通

### 9.1 E2E 改造
- 14 个 E2E 全部用新的统一父页面 selector（`.page-header` / `.data-table` / `.filter-panel`）
- 新增 2 个 E2E：
  - `test-15-pagination.js`（分页组件）
  - `test-16-empty-state.js`（空状态）

### 9.2 跑通
- `cd e2e && node run-all.js`
- 目标：16/16 PASS

---

## P10 文档 + 上线报告

### 10.1 R9-REPORT.md
- 33 个 design 复刻清单（design path + vue path + 状态）
- 设计系统基线说明
- 4 OCR sub-tab 父页面统一说明
- 16/16 E2E 报告

### 10.2 更新
- `GO-LIVE-REPORT.md`：加 R9 段
- `DESIGN-TOKENS.md`：更新统一后的设计令牌

---

## 风险点 + 应对

1. **设计稿重画量大**：3 天工期吃紧，必要时分 2 周做（中间 review）
2. **新旧 design 兼容**：旧 33 个 design 不能删，新画的设计用 `_pattern-` 前缀
3. **vue 改动可能破 E2E**：所有 E2E selector 必须在改 vue 时同步改
4. **后端 6 模块可能受 vue 改动影响**：表单字段名/类型不能动

---

## 我要你拍板的 3 件事

### Q1: 工期节奏
- A: 3 天连续做完（中间不 review，分阶段交付）
- B: 6 天做完（每 2 天一个 review 点，P2/P4/P6/P9 结束各 review 一次）
- C: 其他

### Q2: 旧 33 个 design 文件
- A: 保留旧 33 个 + 新增 1 个 `invoice-ocr-parent.html`（你 review 旧 + 新）
- B: 旧 33 个全删（或移 archive），只留 `invoice-ocr-parent.html` + 4 sub-section + _pattern-*
- C: 其他

### Q3: 哪几个 vue 不动
有些 vue 已经做得很好了（ContractDetail / Dashboard / AiCenter 等），我应该全 1:1 复刻还是"已好的保留，没做的复刻"？
- A: 全 1:1 复刻（统一设计语言，强制一致）
- B: 已好的保留（省工时）
- C: 其他

---

**等你 3 个问题的答复后我开干。**
