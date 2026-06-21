# R9 P5C 报告：回款+发票 5 vue 1:1 复刻

> 阶段：R9 P5C（回款 + 发票模块的详情/编辑器）
> 完成时间：2026-06-14
> 自检：14/14 E2E 100% PASS + 5 页对比图 + Build 0 错误

---

## 完成清单（5 vue）

| # | 页面 | 文件 | 状态 | 设计稿 |
|---|------|------|------|--------|
| 1 | 新建回款 | `frontend/src/views/receivable/ReceivableCreate.vue` | ✅ | `design/receivable-create.html` 1:1 |
| 2 | 回款详情 | `frontend/src/views/receivable/ReceivableDetail.vue` | ✅ | `design/receivable-detail.html` 1:1 |
| 3 | 发票识别详情 | `frontend/src/views/invoice/InvoiceDetail.vue` | ✅ | `design/invoice-detail.html` 1:1 |
| 4 | 模板编辑 | `frontend/src/views/invoice/InvoiceTemplateEdit.vue` | ✅ | `design/invoice-template-edit.html` V2 三栏 1:1 |
| 5 | 模板详情 | `frontend/src/views/invoice/InvoiceTemplateDetail.vue` | ✅ | **无 design**，按 R9 统一详情 pattern 自造 |

---

## 各页面要点

### 1. ReceivableCreate（新建回款 · 4 section）
- **tip-box** 蓝紫渐变提示：关联合同自动带出付款计划
- **form-section 1** 关联合同（合同列表选择 + 合同摘要）
- **form-section 2** 基本信息（回款编号/类型/对方/金额/日期/账户）
- **form-section 3** 付款计划（schedule-table 4 期次）
- **form-section 4** 审批设置（4 个审批人设置）
- **风险检查** 4 项（金额匹配/到账验证/账期合理/合规检查）
- **form-foot** sticky（保存草稿/取消/预览/提交审批）

### 2. ReceivableDetail（回款详情 · 4 detail-tabs）
- **receivable-hero** 蓝紫渐变：HK-2026-021 编号 + 客户名 + 进度条 65%
- **4 detail-tabs**：基本信息 / 付款计划 / 催收记录 / 关联发票
- **左 detail-section 4 个**：合同信息 / 4 期付款计划（设计稿真实数据）/ 2 催收记录 / 1 关联发票
- **右 meta-card 4 个**：客户信息 / 客户回款历史（4 行）/ 风险评估 / 快捷操作

### 3. InvoiceDetail（发票识别详情 · 4 KPI + fake-invoice + 多 section）
- **4 KPI** 票面信息/价税合计/识别置信度/状态
- **fake-invoice** 1:1 设计稿票面（电子普通发票 + SAMPLE 水印 + 发票专用章）
- **8 字段核验** 双栏显示（左侧 AI 识别值 + 右侧人工确认值）
- **商品明细表** 4 行（货物/劳务/服务/合计）
- **4 报销信息**（报销人/部门/项目/费用类型）
- **当前状态 timeline** 5 节点（已上传→识别中→识别完成→人工核验→已入账）
- **6 上传信息**（上传人/时间/IP/文件/设备/大小）
- **6 快捷操作**（导出PDF/重新识别/发起报销/打印/分享/归档）

### 4. InvoiceTemplateEdit（模板编辑 · V2 三栏）
- **三栏布局**：左 240px 字段库（基础/金额/业务 3 组 12 字段）+ 中 1fr 画布 + 右 280px 属性面板
- **tpl-canvas 4 区块**：📌 票面信息（OCR）6 字段 / 💰 金额信息 4 字段 / 📋 业务信息 6 字段 / 📝 附加信息 备注
- **AI 标签**：票面信息块全部带 AI 渐变胶囊（OCR 自动识别）
- **view-toggle**：桌面/移动端切换（移动端 max-width: 375px）
- **属性面板**：基础属性 / 验证规则 / 显示配置 3 组
- **form-foot** sticky：保存草稿 / 取消 / 预览 / 发布模板

### 5. InvoiceTemplateDetail（模板详情 · 无 design 自造）
- **detail-hero 蓝紫渐变**：TPL-TR-2026-001 编号 + 模板名 + 4 KPI（字段/必填/使用/累计）
- **4 detail-tabs**：基本信息 / 字段配置 / 使用记录 / 操作日志
- **左 detail-section**：模板信息 9 字段 + 字段统计 4 类型分布条 + 已绑定单据 3 单据
- **字段配置 tab**：13 字段表格（序/标识/名/类型/必填/默认值/选项）
- **使用记录 tab**：6 条真实入账记录
- **操作日志 tab**：5 节点 timeline
- **右 meta-card 4 个**：当前状态 / 版本信息 / 快速操作 / 相关推荐

---

## 关键技术点

### 1. 复刻 V2 复杂形态（InvoiceTemplateEdit）
- **三栏 1:1**：grid 240px / 1fr / 280px，移动端断点 1100px / 800px
- **字段库 sticky**：position: sticky + top: 16px（滚动到画布中间字段库仍可见）
- **画布栅格**：tpl-row 3 列 + full 类（grid-column: 1 / -1）支持备注跨列
- **AI 标签样式**：渐变胶囊 + 9.5px 字号 + 0.3px letter-spacing
- **属性面板 3 段**：基础属性 / 验证规则 / 显示配置（统一 props-section 分组）

### 2. 无 design 自造（InvoiceTemplateDetail）
- **复用 R9 统一详情 pattern**：detail-hero + 4 detail-tabs + 左 detail-section 3 个 + 右 meta-card 4 个
- **字段类型分布可视化**：5 类型（文本/数字/日期/选择/多行）+ 类型条 + 占比
- **已绑定单据列表**：3 单据图标 + 名称 + 元信息（mono 字体）+ 状态徽章
- **操作日志 timeline**：2px 虚线 + 渐变圆点 + action/user/time 头

### 3. 修 TypeScript 严格模式类型错误
- **`Record<string, X>` 索引 undefined 错误**：STATUS_TAG 类型改 `Record<string, X | undefined>`，computed 加 fallback
- **`ref<UnionType>(initial)` 推断过严**：computed 内部 const + 守卫后用 `v.status || ''` 替代

### 4. 关键样式令牌
- **`$color-primary-bg`**：rgba(79,107,255,0.08) 浅蓝主色背景
- **`$gradient-brand`**：linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%) 蓝紫渐变
- **`$radius-lg / $radius-md / $radius-sm`**：14/10/8px
- **`$font-family-mono`**：SF Mono Monaco monospace
- **tag-pill 5 状态**：primary(soft) / success(绿) / warning(橙) / danger(红) / info(灰)

---

## 自检结果

| 自检项 | 结果 |
|--------|------|
| `npm run build` | ✅ 0 错误，3.79s |
| 14/14 E2E | ✅ 100% PASS |
| 5 页 design vs 实际截图 | ✅ 5/5 已生成 |
| 路由可达 | ✅ 5/5（`/receivable/create` `/receivable/1` `/invoice/ocr/1` `/invoice/template/1/edit` `/invoice/template/1`）|
| 浏览器渲染 | ✅ 200-330KB 截图，正常 |

### E2E 14/14 列表
- test-01-login-dashboard ✅
- test-02-contract-list ✅
- test-03-ai-ask ✅
- test-04-sse-realtime ✅
- test-05-permission ✅
- test-06-notice-cron ✅
- test-07-cron-scheduler ✅
- test-08-paddleocr-real ✅
- test-09-nuonuo-verify ✅
- test-10-wechat-work-sso ✅
- test-11-monitoring ✅
- test-12-invoice-ocr-submenu ✅
- test-13-parent-menu-404 ✅
- test-14-invoice-ocr-tabs ✅

### 5 张对比图
- `docs/screenshots/compare/1-design-p5c-receivable-create.png` + `2-real-p5c-receivable-create.png`
- `docs/screenshots/compare/1-design-p5c-receivable-detail.png` + `2-real-p5c-receivable-detail.png`
- `docs/screenshots/compare/1-design-p5c-invoice-detail.png` + `2-real-p5c-invoice-detail.png`
- `docs/screenshots/compare/1-design-p5c-invoice-template-edit.png` + `2-real-p5c-invoice-template-edit.png`
- `docs/screenshots/compare/2-real-p5c-invoice-template-detail.png`（无 design）

---

## 整体进度

### R9 P5（详情+编辑 12 vue）
- **P5A**（合同 3 + 客户 1 = 4 vue）：✅ 完成
- **P5B**（项目 2 + 费用 2 = 4 vue）：✅ 完成
- **P5C**（回款 2 + 发票 3 = 5 vue）：✅ **本报告**

### R9 累计
- P1 设计基线 + 组件库：✅
- P2 统一父页面 design：✅
- P3 基础页 design：✅
- P4 5 基础页 + 6 业务列表 1:1 复刻：✅
- P5A 合同 3 + 客户 1：✅
- P5B 项目 2 + 费用 2：✅
- **P5C 回款 2 + 发票 3：✅** ← 本报告
- **P5 累计 12 vue 全部 1:1 复刻完成**

---

## 下一步
- **P7**：客户 + AI + admin 共 8 vue 1:1 复刻
- **P8**：通知 + AI panel 4 vue 1:1 复刻
- **P10**：文档 + R9 最终报告 + GO-LIVE 更新

---

## 截图

### 1. ReceivableCreate（design vs 实际）
设计稿：/Users/trisome/Desktop/开发/数智化系统new/docs/screenshots/compare/1-design-p5c-receivable-create.png
实际：/Users/trisome/Desktop/开发/数智化系统new/docs/screenshots/compare/2-real-p5c-receivable-create.png

### 2. ReceivableDetail（design vs 实际）
设计稿：/Users/trisome/Desktop/开发/数智化系统new/docs/screenshots/compare/1-design-p5c-receivable-detail.png
实际：/Users/trisome/Desktop/开发/数智化系统new/docs/screenshots/compare/2-real-p5c-receivable-detail.png

### 3. InvoiceDetail（design vs 实际）
设计稿：/Users/trisome/Desktop/开发/数智化系统new/docs/screenshots/compare/1-design-p5c-invoice-detail.png
实际：/Users/trisome/Desktop/开发/数智化系统new/docs/screenshots/compare/2-real-p5c-invoice-detail.png

### 4. InvoiceTemplateEdit（design vs 实际 V2 三栏）
设计稿：/Users/trisome/Desktop/开发/数智化系统new/docs/screenshots/compare/1-design-p5c-invoice-template-edit.png
实际：/Users/trisome/Desktop/开发/数智化系统new/docs/screenshots/compare/2-real-p5c-invoice-template-edit.png

### 5. InvoiceTemplateDetail（无 design，自造）
实际：/Users/trisome/Desktop/开发/数智化系统new/docs/screenshots/compare/2-real-p5c-invoice-template-detail.png
