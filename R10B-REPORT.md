# R10B 段报告：P1 8 触点（合同/回款/费用/客户/模板）

> 父 session 拍板开 R10B 1 天跑完（实际 1 个工作日内完成）

## 一、交付物：P1 8 触点全部完成

| # | 触点 | 文件 | 工作量 | 接的接口 |
|---|---|---|---|---|
| **#6** | ContractCreate ✦ AI 一键起草 Drawer | `views/contract/ContractCreate.vue` | 紫渐变按钮 + Drawer 表单（合同类型/客户/金额/关键需求）+ 1.8s 进度 + 8 项标准条款输出 + 一键采纳 | `POST /ai/generate/draft` (新补) |
| **#7** | ContractList AI 风险标签列 | `views/contract/ContractList.vue` | 加 "AI 风险" 列（th + td），6 条合同嵌 `<AIRiskChip>` 真实业务文案（"条款完整"/"付款条款较严"/"违约金比例偏高"） | 后端字段 |
| **#8** | ContractDetail AI 合同体检 Drawer | `views/contract/ContractDetail.vue` | 复用顶栏 "🤖 AI 体检" 按钮 + Drawer（78 分健康度 + 5 维进度 + 3 风险预警 + 3 建议 + 跳 AI 中心） | `POST /ai/risk/scan`（已有） |
| **#9** | ReceivableList AI 智能匹配 | `views/receivable/ReceivableList.vue` | 紫渐变按钮 + Drawer（3 类匹配 radio + 3 候选排名 + 评分 + 4 维理由 + 采纳按钮） | `POST /ai/match/run` (新补) |
| **#10** | ExpenseCreate ✦ AI 拍照识别 | `views/expense/ExpenseCreate.vue` | 紫渐变按钮 + Drawer（大虚线 dropzone + 65% 进度 + 字段识别结果 + 采纳到表单） | `POST /ai/extract/upload type:receipt`（已有） |
| **#11** | ExpenseList AI 建议标签 | `views/expense/ExpenseList.vue` | 加 "AI 建议" 列（th + td），5 行审批单 chip 3 色（绿"建议通过" / 黄"建议复核" / 红"风险提示"） | 后端字段 |
| **#12** | ReceivableCreate ✦ AI 智能提醒日期 | `views/receivable/ReceivableCreate.vue` | 首次回款日期旁加 ✦ AI 建议按钮 + 弹建议条（日期 + 理由 + 采纳按钮） | `POST /ai/generate/draft` (新补) |
| **#13** | InvoiceTemplateEdit 字段 AI 开关 | `views/invoice/InvoiceTemplateEdit.vue` | 右属性面板"验证规则"加 el-switch + 渐变高亮行 + 开关后弹说明条 | `POST /ai/extract/upload`（已有） |

## 二、技术决策

### 1. aiApi.ts 补 2 个 mock 接口（前端可独立跑）
- `aiApi.generateDraft({type, context, templateId?})` → 返回完整 draft（title/content/sections[8]/fields/confidence/model/durationMs）
- `aiApi.matchRun({type, source, candidates?})` → 返回 matches 数组（targetId/name/score/reasons）+ bestMatchId
- 后端等资质：frontend `.catch(() => null)` + mock 兜底

### 2. 8 触点用统一 UI 模式
```
[紫渐变按钮 + ✦/✨ 图标] → 弹 el-drawer (rtl, 480-540px)
  → 表单输入（el-form/select/date-picker）
  → [紫渐变"开始 AI"主按钮] → 进度条/loading
  → 结果区（卡片/章节/匹配列表）
  → [采纳 + 关闭] 按钮组
```

### 3. 复用 R10A 经验
- 所有 AI 接口用 `.catch(() => null)` + mock 回退（前端不因 AI 挂就崩）
- 紫渐变主题色：`$gradient-brand: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%)`（design 1:1）
- 通用组件 `<AIRiskChip>` 在 #7 直接复用（R10A 投资一次，多处复用）

## 三、验证

### 1. Build
```bash
$ cd frontend && npm run build
✓ built in 4.13s（8 触点全部 0 TS 错 / 0 SCSS 错）
```

### 2. 14 个 E2E 跑测（13/14 PASS，test-09 已知遗留）
- ✅ test-01 登录 + Dashboard
- ✅ test-02 合同列表筛选（**覆盖 #7 触点列**）
- ✅ test-03 AI 问答
- ✅ test-04 SSE 实时活动
- ✅ test-05 权限模型
- ✅ test-06 通知中心
- ✅ test-07 定时任务
- ✅ test-08 PaddleOCR 真识别
- ⚠️ test-09 诺诺验真（**R10 前遗留**，本段不修）
- ✅ test-10 企业微信 SSO
- ✅ test-11 Prometheus 监控
- ✅ test-12 发票识别 4 sub-tab
- ✅ test-13 父菜单 404
- ✅ test-14 发票识别 4 tabs + 路由 redirect

### 3. 5 张触点截图
| # | 触点 | 截图 |
|---|---|---|
| 1 | #7 合同列表 AI 风险标签列 | `docs/screenshots/compare/2-real-r10b-01-contract-list-ai-risk.png` |
| 2 | #8 合同详情 AI 体检 Drawer | `docs/screenshots/compare/2-real-r10b-02-contract-detail-ai-checkup.png` |
| 3 | #6 合同创建 AI 一键起草 Drawer | `docs/screenshots/compare/2-real-r10b-03-contract-create-ai-draft.png` |
| 4 | #9 回款列表 AI 智能匹配 | `docs/screenshots/compare/2-real-r10b-04-receivable-ai-match.png` |
| 5 | #12 回款创建 AI 智能提醒日期 | `docs/screenshots/compare/2-real-r10b-05-receivable-ai-date.png` |

### 4. 容器三连
- 重打 `shuzhi-frontend:latest` + 启 network `deploy_shuzhi-net`
- 验证 `health: starting → healthy`（5s 内）

## 四、踩过的坑

1. **template div 漏闭合**：ContractCreate 加 AI Drawer 在 page-container 内但少一个 `</div>` → vue-tsc 报 "Element is missing end tag"
2. **el-switch @change 类型严**：typescript 严格模式嫌 boolean 不符 `string | number | boolean` → 改参数联合类型
3. **aiApi.generateDraft 调用链**：R10A 的 aiApi.ts 没有 draft/match 接口，**先补 2 个 mock 接口**才能 8 触点全跑
4. **mock 真实感**：每个触点的 mock 数据都基于"真实业务文案"（如"付款条款较严" / "客户响应变慢"），不是 "warning" 这种空字符串

## 五、当前状态 & 下一步

**R10B 完成**（1 个工作日）：

- ✅ 8 触点全部完成 + 1:1 复刻（合同/回款/费用/模板）
- ✅ aiApi.ts 补 2 个 mock 接口
- ✅ Build PASS / 13/14 E2E PASS（test-09 已知遗留）/ 5 截图
- ✅ 容器三连 + 健康

**下一步 R10C（P2 9 触点 + 体验增强）**：第 3 周（按 C 方案）
- #14 全局命令面板 ⌘K
- #15 Dashboard 解读
- #16 登录 AI 入口 / #17 错误页 AI 助手
- #18 4 详情页 AI 操作
- #19 票面 AI 复核
- #20-#22 5 列表 AI 筛选
- 体验增强：拖拽排序 / 暗色模式 / 移动端

**技术债**：
- 诺诺 mock 返回非 JSON（test-09 fail）
- 真实 PaddleOCR / 诺诺 / 企业微信 SSO 切真（等资质）

**R10A + R10B 累计**：
- 13 触点完成（P0 5 + P1 8）
- 3 个 AI 通用组件
- 1 个 aiApi.ts mock 完整
- 10 张截图

---

**R10B 段报告** | 2026-06-15 | Mavis
