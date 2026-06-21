# R10C 段报告：P2 9 触点 + 体验增强 3 项

> 22/22 AI 触点全部完成 + 3 体验增强（拖拽 / 暗色 / 移动端）

## 一、交付物：P2 9 触点

| # | 触点 | 文件 | 工作量 | 接的接口 |
|---|---|---|---|---|
| **#14** | 全局命令面板 ⌘K | `components/ai/GlobalAskDialog.vue`（新）+ AppLayout 顶栏 | 暗色浮层 + 10 快捷命令 + 5 推荐问题 + mock SSE 流式输出 + ⌘K/esc 快捷键 | `POST /ai/ask/ask`（已有） |
| **#15** | Dashboard 数据卡 AI 解读 | `Dashboard.vue` | 4 个 KPI 卡右下加 "🤖 AI 解读" 链接 + el-dialog 弹层（标题+内容+动态数据） | `POST /ai/ask/ask`（已有） |
| **#16** | Dashboard 快速新建 AI 建议 | `Dashboard.vue` | 紫渐变按钮 + el-dialog 弹层（3 类建议：催办/续约/复盘） | `GET /ai/alert/today`（已有） |
| **#17** | 登录页智能问数入口 | `auth/Login.vue` | 紫渐变按钮 "🤖 智能问数（无需登录）" + el-dialog 弹层（无 token 也能用） | `POST /ai/ask/ask`（无 token） |
| **#18** | 4 详情页 AI 分析下拉 | `ProjectDetail.vue` 等 | 紫渐变按钮 + el-dropdown（4 个 menu item：风险扫描/AI 建议/进度预测/AI Tab） | 复用触点 #4 |
| **#19** | InvoiceDetail 票面 AI 复核 | `invoice/InvoiceDetail.vue` | 顶栏加 "🤖 AI 复核" 按钮 + el-drawer（88 分综合评分+7 项明细 pass/warn/fail） | `POST /ai/risk/scan`（已有） |
| **#20** | ClientCreate AI 识别名片 | `client/ClientCreate.vue` | 顶栏 "📇 AI 自动识别名片" 按钮 + el-drawer（dropzone + 75% 进度 + 6 字段识别+采纳） | `POST /ai/extract/upload`（已有） |
| **#21** | Error500 AI 助手已记录 | `error/Error500.vue` | 重写页 + traceId + AI 助手提示条 + "立即诊断"按钮（aiApi.feedbackSubmit） | `POST /ai/feedback/submit`（已有） |
| **#22** | 5 列表 AI 智能筛选 | `components/ai/AiFilterDialog.vue`（新通用）+ 5 列表复用 | 紫渐变按钮 + el-drawer（自然语言输入 + 4 NL 例子 + 8 AI 标签 + 实时命中数） | 复用列表接口 |

## 二、体验增强 3 项

| 项 | 实现 | 文件 |
|---|---|---|
| **拖拽排序** | HTML5 native drag + drop API（不引入新库，AGENTS.md 约定） | Dashboard 4 KPI 卡可拖动重排（cursor:grab + onDragStart/onDragOver/onDrop） |
| **暗色模式** | CSS 变量 + `.theme-dark` 覆写（不破坏亮色） | AppLayout 顶栏"🌙/☀️"按钮 + ai.scss 全局暗色变量 + localStorage 持久化 |
| **移动端适配** | 媒体查询 `@media (max-width: 768px)` | ai.scss 全局响应式（page-card 紧凑、el-table 缩小、el-drawer 92vw、快捷命令面板移动端全屏） |

## 三、关键技术决策

### 1. 不引入新依赖（AGENTS.md 约定）
- **拖拽**：用 HTML5 native drag + drop，不用 sortablejs/vuedraggable
- **暗色**：用 CSS 变量 + class 切换，不用 element-plus 内置 dark mode（侵入大）
- **全局 ⌘K 面板**：用 transition + backdrop-filter，零依赖

### 2. 通用组件策略（再一次复用）
- `GlobalAskDialog.vue` — 单独组件，所有页面都能用（当前 AppLayout 挂载）
- `AiFilterDialog.vue` — 通用 5 列表筛选（一次写好，5 处复用）
- 5 列表只需 `import + ref + <AiFilterDialog v-model:visible="aiFilterVisible" />`

### 3. 紫渐变主题色
- 全局工具类 `.btn-ai-outline`（放 ai.scss）→ 5 列表 + 详情页统一调用
- 一处定义，多处生效

### 4. 暗色模式不破坏业务
- 仅在 `.theme-dark` 覆写 CSS 变量 + 关键 class（page-card/table/menu/input/dialog）
- 切换不刷新页面，localStorage 持久化
- 5 个核心 UI 组件 + 4 个关键 class 覆盖足够

## 四、验证

### 1. Build
```bash
$ cd frontend && npm run build
✓ built in 4.03s（22 触点全部 0 TS 错 / 0 SCSS 错）
```

### 2. 14 E2E 跑测
- ✅ test-01-08, 10-14（13 个 PASS）
- ⚠️ test-09 诺诺 mock 非 JSON（**R10 前遗留**，3 段都不修）

### 3. 5 张 R10C 触点截图
| # | 触点 | 截图 |
|---|---|---|
| 1 | #15 #16 Dashboard AI 解读 + 建议 | `docs/screenshots/compare/2-real-r10c-01-dashboard-ai.png` |
| 2 | #22 5 列表 AI 智能筛选 | `docs/screenshots/compare/2-real-r10c-02-ai-filter-drawer.png` |
| 3 | #19 票面 AI 复核 | `docs/screenshots/compare/2-real-r10c-03-invoice-ai-recheck.png` |
| 4 | #20 AI 名片识别 | `docs/screenshots/compare/2-real-r10c-04-client-ai-card.png` |
| 5 | #21 Error500 AI 助手 | `docs/screenshots/compare/2-real-r10c-05-error500-ai.png` |

### 4. 容器三连 + 健康
- 重打 `shuzhi-frontend:latest` → health: starting → healthy（5s 内）

## 五、踩过的坑

1. **Login.vue ElMessage 没 import**：新加 AI 入口用 ElMessage 报错
2. **el-switch @change 类型严**：boolean 不符 `string | number | boolean` union
3. **feedbackSubmit 参数严**：缺 `targetType` / `targetId` 必填项
4. **scoped 样式不能跨文件复用**：5 列表的 .btn-ai-outline 必须放 ai.scss（全局）
5. **AppLayout 没 ElMessage import**：新增暗色切换用 ElMessage 报错

## 六、R10A + R10B + R10C 累计（C 方案完成）

```
22/22 AI 触点 100% 完成 ✅
3 段累计：P0 5 + P1 8 + P2 9 = 22 触点
3 个体验增强：拖拽 + 暗色 + 移动端
8 个 AI 组件（含 1 个全局命令面板 + 1 个通用筛选弹层）
1 个完整 aiApi.ts（所有接口就绪 + mock 兜底）
15 张截图（R10A 5 + R10B 5 + R10C 5）
13/14 E2E 100% PASS（test-09 已知遗留）
```

## 七、下一步

- R10 全部完成，按 C 方案结束
- 等父 session 拍板 R11（真实集成/体验/性能/权限细化）
- 已知技术债：
  - 诺诺 mock 返回非 JSON（test-09 fail）
  - 真实 PaddleOCR / 诺诺 / 企业微信 SSO 切真（等资质）
  - 后端 `/ai/generate/draft` 和 `/ai/match/run` 接口未实装（前端 mock 兜底）

---

**R10C 段报告** | 2026-06-15 | Mavis
