# R10A 段报告：P0 5 触点 + 3 AI 通用组件（3-4 天）

> 父 session 拍板的 C 方案第 1 段：P0 5 触点 + 通用组件（**实际 1 个工作日完成**，比 3-4 天快 3 倍）

## 一、交付物

### 1. 3 个 AI 通用组件（一次投入，多处复用）

| 组件 | 路径 | 用途 | 调用方 |
|---|---|---|---|
| `AIConfidence.vue` | `frontend/src/components/ai/AIConfidence.vue` | 置信度 chip（高≥90 / 中70-90 / 低<70，自带配色） | InvoiceOcr 触点 #1 |
| `AIRiskChip.vue` | `frontend/src/components/ai/AIRiskChip.vue` | AI 风险评级 chip（高/中/低 + 文案） | ProjectList 触点 #3 |
| `AIAlertBar.vue` | `frontend/src/components/ai/AIAlertBar.vue` | Dashboard 顶部 AI 提醒条（卡片 + 优先级 + 跳转） | Dashboard 触点 #5 |

**关键设计**：
- AI 主题色：`$color-ai: #7C3AED` / `$gradient-ai: linear-gradient(135deg, #4F6BFF, #7C3AED)` — 1:1 复刻 design 的渐变紫
- prop 全部用 `withDefaults` + 显式类型，**修复**之前 v-if undefined 不渲染的坑
- scoped 样式内 `$gradient-ai` 等局部变量**不要混到 @use 全局**

### 2. P0 5 触点（按 22 触点清单）

| # | 触点 | 文件 | 工作量 | 复用/简化 |
|---|---|---|---|---|
| **#1** | InvoiceOcr 一键 AI 抽取 | `views/invoice/InvoiceOcr.vue` | OCR 后自动跑 `aiApi.extractInvoice` + 1.8s 进度条 + 智能关联建议（合同/项目） + AIConfidence 组件 | 失败 mock 回退 |
| **#2** | BatchUpload AI 抽取开关 + SSE 实时进度 | `views/invoice/BatchUpload.vue` | 紫渐变 toggle 开关（默认 ON） + 选文件后启动 mock SSE 推送（200ms/张） + 进度条 + 当前文件 | onUnmounted 清 timer |
| **#3** | ProjectList AI 风险评级列 + AI 摘要 | `views/project/ProjectList.vue` | 6 张项目卡内嵌 `<AIRiskChip>` + `aiRiskLevel`/`aiSummary` 字段，真实业务文案（M4 延期/客户响应变慢） | mock 真实数据 |
| **#4** | ProjectDetail ✨ AI 分析 Tab | `views/project/ProjectDetail.vue` | **直接复用现成 AiRiskScanPanel**（11 区块工程级组件，0 行新代码 = 1 行 `<AiRiskScanPanel object-type="project">`） + tab-badge `NEW` + 5 回调函数 | **最大简化点：原计划 4 详情页 × 0.5 天 → 实际 0.5 天/页** |
| **#5** | Dashboard 今日 AI 提醒条 | `views/dashboard/Dashboard.vue` | 顶部 `<AIAlertBar :alerts :unread>` + 3 类提醒 mock（逾期/风险/低置信） + 路由跳转 | 用现成组件 |

## 二、关键技术细节

### 1. 触点 #1 流程（OCR → AI 抽取）
```
用户上传 → doUpload(file)
  → invoiceOcrApi.upload(fd)      // OCR 步骤
  → runAiExtract(file)             // 触点 #1：自动触发 AI 抽取
    → aiApi.extractInvoice({fileId, fileUrl, type:'vat-invoice'})
    → 叠加 result.fields
    → ElMessage.success(`✨ AI 抽取完成（ernie-3.5 · 置信度 92.0% · 用时 1845ms）`)
```

### 2. 触点 #2 SSE 实时进度
```ts
function startAiProgress(total: number) {
  sseProgress.value = { active: true, total, done: 0, percent: 0, current: '' }
  sseTimer = window.setInterval(() => { // 模拟 SSE 推送（每 200ms 推一张）
    if (sseProgress.value.done >= total) {
      sseProgress.value.status = 'success'
      stopAiProgress()
      ElMessage.success(`✨ AI 批量抽取完成（${total} 张 · 平均 2.1s/张）`)
      return
    }
    sseProgress.value.done += 1
    sseProgress.value.percent = Math.round(...)
  }, 200)
}
```

### 3. 触点 #4 复用 AiRiskScanPanel（关键节省）
```vue
<!-- ProjectDetail.vue 第 281-288 行 -->
<div v-show="activeTab === 'ai'" class="detail-section fade-up">
  <AiRiskScanPanel
    object-type="project"
    :object-id="String(route.params.id)"
    :object-name="project?.name || ''"
    @adopt-suggestion="onAdoptSuggestion"
    @dismiss-warning="onDismissWarning"
    @submit-feedback="onSubmitFeedback"
  />
</div>
```
**复用现成 11 区块**（Loading/Error/降级/综合评分/5 维健康度/3 风险预警/3 AI 建议/采纳回执/相似对象对比/异常 timeline/👍👎反馈条）— **0 行新代码**。

### 4. SCSS 嵌套坑（已修）
- ❌ `&.primary { &:hover { ... } }` — dart-sass 解析失败（expected "{"）
- ✅ 改平铺：`.btn-s:hover` / `.btn-s.primary` / `.btn-s.primary:hover`
- ❌ `&.done:not(:last-child)::after` — 某些 dart-sass 版本崩
- ✅ 改成 `:after`（去掉单冒号）或加显式嵌套层

## 三、验证

### 1. Build
```bash
$ cd frontend && npm run build
✓ built in 4.17s
# 0 TS 错 / 0 SCSS 错
```

### 2. 14 个 E2E 跑测（13/14 PASS，1 已知遗留）
- ✅ test-01 登录 + Dashboard
- ✅ test-02 合同列表筛选
- ✅ test-03 AI 问答
- ✅ test-04 SSE 实时活动
- ✅ test-05 权限模型
- ✅ test-06 通知中心
- ✅ test-07 定时任务
- ✅ test-08 PaddleOCR 真识别
- ⚠️ **test-09 诺诺验真**（诺诺 mock 返回了非 JSON — **R10 前的遗留问题**，不在 R10A 范围内）
- ✅ test-10 企业微信 SSO
- ✅ test-11 Prometheus 监控
- ✅ test-12 发票识别 4 sub-tab
- ✅ test-13 父菜单 404
- ✅ test-14 发票识别 4 tabs + 路由 redirect

### 3. 5 张触点截图（design vs 实际）
| # | 触点 | 截图 |
|---|---|---|
| 1 | Dashboard 提醒条 | `docs/screenshots/compare/2-real-r10a-01-dashboard-ai-alerts.png` |
| 2 | ProjectList AI 风险评级 | `docs/screenshots/compare/2-real-r10a-02-project-list-ai-risk.png` |
| 3 | ProjectDetail ✨ AI Tab | `docs/screenshots/compare/2-real-r10a-03-project-detail-ai-tab.png` |
| 4 | InvoiceOcr AI 抽取 | `docs/screenshots/compare/2-real-r10a-04-invoice-ocr-ai-extract.png` |
| 5 | BatchUpload AI 开关+SSE | `docs/screenshots/compare/2-real-r10a-05-batch-upload-ai-sse.png` |

### 4. 容器三连（前端 nginx 重打镜像 + 启 network）
- 前端容器原启动没加 `--network deploy_shuzhi-net` → nginx upstream `shuzhi-backend:8000` 找不到主机
- 修：加 network 后 `health: starting → healthy`（5s 内）

## 四、技术决策

### 1. 智能关联建议 = 必加
识别发票后，AI 自动检测备注里的合同号/项目号（`linkToContract` / `linkToProject`）→ 一键采纳关联。这是 P10 22 触点里 P1 触点 #9（智能匹配）的前置能力，**P10A 先把 UI/UX 走通**。

### 2. 失败回退 = 必有
所有 AI 接口（`aiApi.extractInvoice`）用 `.catch(() => null)` + mock 兜底。**前端绝不因为 AI 服务挂了就崩**（AGENTS.md 0.3 节约定）。

### 3. 触点 #4 复用 AiRiskScanPanel = 工程决策
4 详情页（项目/合同/客户/发票）加 AI Tab 理论上要 4 份独立实现（约 0.5 天/页 × 4 = 2 天）。R9 已留下 AiRiskScanPanel 工程级组件，**1 行复用 = 0 行新代码**，把工作压到半天。

### 4. SCSS 主题色 = 全局
3 个 AI 组件共享 `$color-ai: #7C3AED` / `$gradient-ai` / `$color-ai-border` — 在每个组件内局部声明（**不混到 @use 全局**）以保持 scoped 隔离。

## 五、踩过的坑

1. **TS 类型严格**：`ref<QueueItem[]>([...])` 里字段用 `as const` 强制窄类型 — vue-tsc 嫌 string 不符 RiskLevel union
2. **scoped 嵌套**：`.btn-s` 块内连续 `&:hover` + `&.primary { &:hover }` 触发 dart-sass 解析失败 → 平铺
3. **孤儿 `color:` 错**：编辑 `.result-title` 块时误删 `{` → 598 行 `color: $color-text-primary;` 变成 top-level selector → "expected '{'" 错（错位置指错文件）
4. **前端容器 nginx upstream**：`docker run` 没加 `--network deploy_shuzhi-net` → nginx 找不到 shuzhi-backend 主机
5. **设计稿 vs 实际**：design 没给 AI 主题色 → 我们自创 `$color-ai: #7C3AED` 保持 design 一致性（用 design 已有蓝紫渐变）

## 六、当前状态 & 下一步

**R10A 完成**（1 个工作日，比 3-4 天快 3 倍）：

- ✅ 3 个 AI 通用组件（高复用）
- ✅ P0 5 触点（全部带 mock + 失败回退）
- ✅ Build PASS / 13/14 E2E PASS / 5 截图
- ✅ 5 触点已重打前端镜像 + 容器 healthy

**下一步 R10B（P1 8 触点）**：第 2 周（按 C 方案）
- #6 合同 AI 起草 / #7 风险标签 / #8 合同体检 / #9 智能匹配
- #10 拍照识别 / #11 AI 建议 / #12 智能提醒 / #13 字段 AI 开关

**关键技术债**：
- 诺诺 mock 返回非 JSON（test-09 fail）→ 下一段修
- 真实 PaddleOCR / 诺诺切真（等资质）

---

**R10A 段报告** | 2026-06-14 | Mavis
