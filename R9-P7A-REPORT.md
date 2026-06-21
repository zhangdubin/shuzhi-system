# R9 P7A 报告：AI 中心 5 vue 1:1 复刻

> 阶段：R9 P7A（AI 中心：智能问答/风险/任务/提醒）
> 完成时间：2026-06-14
> 自检：14/14 E2E 100% PASS + 5 页对比图 + Build 0 错误

---

## 完成清单（5 vue）

| # | 页面 | 文件 | 状态 | 设计稿 |
|---|------|------|------|--------|
| 1 | AI 中心 | `frontend/src/views/ai/AiCenter.vue` | ✅ | `design/ai-center.html` 1:1（670 行）|
| 2 | 智能问答 | `frontend/src/views/ai/AiAsk.vue` | ✅ | **无 design**，按 ai-center ask-box 派生 |
| 3 | 风险识别 | `frontend/src/views/ai/AiRisk.vue` | ✅ | **无 design**，按 ai-panel-contract 风险评分派生 |
| 4 | 任务中心 | `frontend/src/views/ai/AiTasks.vue` | ✅ | **无 design**，按 ai-center 任务列表 + 抽屉 |
| 5 | 智能提醒 | `frontend/src/views/ai/AiAlerts.vue` | ✅ | **无 design**，按 ai-center 今日提醒派生 |

---

## 各页面要点

### 1. AiCenter（AI 中心 · 1:1 复刻 670 行）
- **ai-hero 蓝紫渐变** + radial-gradient ::before 装饰 + 巨大 ✦ ::after
- **6 大 AI 能力 cap-grid**（3 列 × 2 行，响应式 900px/600px 断点）
  - 智能字段抽取（NEW badge）/ 风险识别 / 银行流水匹配 / 自然语言问数 / 智能起草 / Agent 自动化
  - hover 上浮 3px + AI 紫色 box-shadow
- **ai-main 2:1 双栏**：
  - 左：问数输入框（紫色 focus-within 发光）+ 5 快捷问题胶囊 + 5 任务列表（3 running 带 3 圆点 bounce 动画 + 1 done + 1 failed）
  - 右：今日 AI 提醒 3 条（danger/warning/success 3 色）+ 模型状态 5 行（normal/degraded/down 3 状态点）+ 快捷入口 6 链接（hover 反白渐变）
- **AI 主题色**：$color-ai #7C3AED + $gradient-ai + $color-ai-border rgba(124, 58, 237, 0.25)
- **ai-thinking-dots 动画**：3 圆点 1.4s bounce 循环

### 2. AiAsk（智能问答 · 自造聊天界面）
- **左 240px 会话列表**：4 历史会话 + 新建按钮（紫色圆形 +）
- **右聊天区**：用户消息（紫色气泡右对齐）/ AI 消息（左对齐 + 紫色渐变头像 ✦）
- **3 类 AI 响应**：
  - 普通文本（支持 **加粗** + 换行）
  - 数据表格（3 条数据演示，含 mono 字体编号 + AI 紫色金额）
  - SQL 黑色代码块（深色 #1F2937 + 11.5px 等宽字体）
- **AI 响应操作**：复制 / 有用反馈 / 重新生成
- **底部 ask-input**：✦ 图标 + **textarea**（E2E 兼容）+ 紫色发送按钮 + 7 快捷问题胶囊
- **思考中动画**：3 圆点 bounce + "正在分析中..."
- **支持路由 ?q= 自动发送**（从 AiCenter 跳转过来）

### 3. AiRisk（风险识别 · 自造 8 条风险列表）
- **4 KPI 卡**（高/中/低/已处理）带 trend 趋势文字
- **5 type-tabs**（全部/合同/项目/发票/凭证）含数量徽章
- **风险列表 8 条**：每条含等级 tag + 类型 + 创建时间 + 名称 + 描述 + 关联单据 + 金额
  - 高风险：合同逾期/付款异常/项目超期 3 条（红色左边框）
  - 中风险：发票异常/项目回款延迟 3 条（橙色左边框）
  - 低风险：凭证借贷不平/违约金缺失 2 条（紫色左边框）
- **详情侧栏**：5 维健康度（履约/付款/条款/变更/信用，各 100 分评分带进度条）+ 异常事件 timeline（4 节点）+ AI 建议 3 条

### 4. AiTasks（任务中心 · 自造 10 任务表格）
- **4 KPI 卡**（总/进行中/已完成/失败）
- **5 status-tabs**（全部/进行中/已完成/失败/排队）
- **任务表格 10 条**：图标 + 任务名 + 描述 + 类型 chip + 进度条（running 紫/done 绿/failed 红）+ 状态 tag + 创建时间 + ETA + 操作
- **进度条动画**：完成度百分比
- **bounce 动画**：running 状态 3 圆点
- **详情抽屉（覆盖层）**：选中任务显示进度 + 4 步骤 timeline（创建/校验/推理/入库）+ 4 任务参数
- **重试/取消/查看** 3 类操作

### 5. AiAlerts（智能提醒 · 自造 12 条提醒列表）
- **4 KPI 卡**（紧急/重要/普通/已处理）
- **5 level-tabs**（全部/紧急/重要/普通/已忽略）
- **提醒列表 12 条**：等级图标（!/⚠/○）+ level-tag（紧急/重要/普通 3 色）+ 标题 + 来源标签 + 时间 + 描述 + 关联单据（hover 变紫）+ 2 操作按钮
  - 3 紧急：合同逾期/账户余额低/项目回款逾期
  - 5 重要：发票 OCR 异常/重复报销/合同条款/预算执行/客户回款延迟
  - 4 普通：回款匹配/项目里程碑/客户续约/月度结账
- **空状态**：📭 暂无相关提醒
- **顶部操作**：规则配置 + 全部已读

---

## 关键技术点

### 1. 1:1 复刻复杂 AI 主题（AiCenter）
- **gradient-ai**：`linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%)` 蓝紫渐变（和 brand 渐变相同）
- **ai-hero 装饰**：::before radial-gradient(circle, rgba(255,255,255,0.15), transparent 70%) 280px 圆形 + ::after 巨大 ✦ 160px 8% 不透明
- **ai-thinking-dots 动画**：3 圆点 1.4s bounce 循环
- **ai-suggestion 3 状态**：danger(red) / warning(orange) / success(green) icon 圆形 + actions
- **ai-quick hover 反白**：普通态紫色背景 → hover 渐变 + 白字 + icon 反色

### 2. E2E selector 兼容（重要经验）
- **问题**：test-03-ai-ask 找 `.ai-ask-input textarea`、`.msg.assistant .msg-content`、`.ai-ask-suggestions .suggestion`，但新版用了不同类名
- **解决**：在保持 1:1 自造风格的同时**叠加 E2E 期望的类名**（`.ai-ask-title`、`.ai-ask-input`、`.ai-ask-suggestions`、`.msg.assistant`、`.msg-content`、`.suggestion`）
- **input → textarea**：用 textarea 满足 `textarea` 选择器（按 E2E 期望的标签名）
- **教训**：早期 E2E 写死的 selector 反映老 vue 的实现，新版兼容老 selector 比改 E2E 更稳

### 3. 复用 R9 统一组件库
- **page-header / page-card**：所有 vue 统一头部
- **status-tabs** 复用：5 vue 全部用 status-tabs 模式
- **stat-card**：4 KPI 卡（不同颜色 border-left）
- **timeline** 自实现：左侧虚线 + 圆点 + content

### 4. 路由细节
- **AiCenter** 路由是 `/ai`（不是 `/ai/center`）
- **AiAsk 支持 `?q=` 参数**：从 AiCenter 跳过来自动填入 + 发送
- **AiTasks 详情用覆盖层 mask**：不用 el-drawer（避免额外依赖），手写 mask + slide-in 动画

### 5. 风险/任务/提醒三页统一 pattern
- 顶部 **4 KPI**（左 border 4 色 + trend 文字）
- 中部 **5 tabs**（含数量徽章）
- 主体 **左列表 + 右详情**（AiRisk）/ **全列表**（AiTasks/AiAlerts）
- 列表项 **4 段**：head（等级+类型+时间）/ name（粗体）/ desc（灰色描述）/ foot（关联单据+金额/操作）

---

## 自检结果

| 自检项 | 结果 |
|--------|------|
| `npm run build` | ✅ 0 错误，3.84s |
| 14/14 E2E | ✅ 100% PASS |
| 5 张对比图 | ✅ 1 design（AiCenter）+ 4 自造截图 |
| 路由可达 | ✅ 5/5 |
| 浏览器渲染 | ✅ 240-450KB 截图正常 |

### E2E 14/14 列表
- test-01-login-dashboard ✅
- test-02-contract-list ✅
- **test-03-ai-ask** ✅ ← 修复 selector 兼容
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

### 6 张截图
- `docs/screenshots/compare/1-design-p7a-ai-center.png`（design 450KB）
- `docs/screenshots/compare/2-real-p7a-ai-center.png`（实际 352KB）
- `docs/screenshots/compare/2-real-p7a-ai-ask.png`（实际 248KB）
- `docs/screenshots/compare/2-real-p7a-ai-risk.png`（实际 313KB）
- `docs/screenshots/compare/2-real-p7a-ai-tasks.png`（实际 245KB）
- `docs/screenshots/compare/2-real-p7a-ai-alerts.png`（实际 238KB）

---

## 整体进度

### R9 P7（8 vue 全部 1:1 复刻）
- **P7A** AI 中心 5 vue（AiCenter + AiAsk + AiRisk + AiTasks + AiAlerts）：✅ **本报告**
- **P7B** admin 4 vue（AdminUser + AdminRole + AdminDept + AdminDict）：待做
- **P7C** AiExtract 对齐 + 收尾：待做

### R9 累计
- P1-P5C：✅（P5 累计 12 vue：合同 3 + 客户 1 + 项目 2 + 费用 2 + 回款 2 + 发票 3）
- **P7A AI 中心 5 vue**：✅ ← 本报告
- P7B admin 4 vue：待做
- P7C AiExtract 收尾：待做
- P8 通知 + AI panel 4 vue：待做
- P10 文档 + R9 报告：待做

---

## 下一步
- **P7B**：admin 4 vue 1:1 复刻（无 design 自造，结构相似）~ 2h
- **P7C**：AiExtract 对齐 ai-extract-demo.html + P7 总报告 ~ 0.5h
- **P8**：AiPanelContract + AiPanelProject + Drawer + NoticeCenter 4 vue ~ 1.5h
- **P10**：R9-FINAL-REPORT.md + GO-LIVE-REPORT 更新 ~ 1h

---

## 关键经验总结（写进 memory）

1. **早期 E2E selector 兼容**：当新版 vue 重写时，**保持老 E2E selector 有效**比改 E2E 更稳。方法：叠加类名 + 用对的标签名（input vs textarea）。
2. **AI 主题色独立**：AI 模块的紫色 #7C3AED 和 brand 渐变是**同色**，但语义上是 AI 专属——`ai-bg` / `ai-border` / `ai-shadow` 单独命名清晰。
3. **1:1 复刻时装饰要还原**：::before radial-gradient + ::after 巨大字符是 design 的灵魂，**不能简化掉**。
4. **chat 界面 3 类响应**：普通文本 / 数据表格 / SQL 代码块是 AI 问答的 3 大类内容，必须都支持。
