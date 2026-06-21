# 数智化管理系统 · 前端设计稿 + 文档

> 项目交付总览

## 1. 一图总览

```
📁 design/      前端（页面 + 文档）
   ├── *.html           32 个页面（28 业务 + 4 AI）
   ├── assets/          设计系统
   └── *.md             8 份核心文档

📁 backend/     后端（FastAPI 骨架 + 样板模块）
📁 deploy/      部署（Docker + compose + 监控）
```

---

## 2. 页面（32 个：28 业务 + 4 AI 数智化）

### 第一阶段 · 入口（5）
- `index.html` 预览入口
- `login.html` 登录
- `dashboard.html` 总览
- `invoice-ocr.html` 发票识别主页
- `assets/common.css` 设计系统（含 14 类 AI 组件样式）

### 第二阶段 · 6 大业务模块（5）
- `invoice-template.html` 发票模板
- `sales-expense.html` 销售费用
- `project.html` 项目管理
- `contract.html` 合同管理
- `receivable.html` 回款管理

### 第三阶段 · 详情/编辑/弹窗（6）
- `invoice-detail.html` 发票详情
- `invoice-template-edit.html` 发票模板编辑器
- `sales-expense-create.html` 销售费用录入（Drawer）
- `project-detail.html` 项目详情
- `contract-detail.html` 合同详情
- `receivable-detail.html` 回款详情

### 第四阶段 · 发票识别子模块（3）
- `invoice-ocr-batch.html` 批量上传（含 SSE Demo）
- `invoice-ocr-records.html` 识别记录
- `invoice-ocr-verify.html` 查验真伪

### 第五阶段 · 创建表单（5）
- `contract-create.html` 合同起草
- `project-create.html` 项目立项
- `receivable-create.html` 回款计划
- `client-create.html` 客户档案
- `template-create.html` 发票模板新建

### 第六阶段 · 辅助页面（5）
- `error-404.html` 404 错误页
- `error-403.html` 403 无权限
- `error-500.html` 500 服务器错误
- `error-network.html` 网络异常
- `components-states.html` 空状态/加载状态/AI 状态 Demo

### 🆕 第七阶段 · AI 数智化（4，新增）
- `ai-center.html` AI 中心主页（hero + 6 大能力 + 问数 + 任务 + 提醒 + 模型状态）
- `ai-extract-demo.html` 字段抽取交互演示（左右对比 + 置信度色阶 + AI 高亮 + 智能关联）
- `ai-panel-project.html` 详情页 AI 分析 Tab（5 维健康度 + 风险预警 + 智能摘要 + 相似项目 + 时间线）
- _（更多 AI 页面按需扩）_

## 3. 核心文档（8 份）

| 文档 | 内容 |
|------|------|
| `API.md` | 59 个老接口 + SSE 实时通信约定 |
| **`AI-API.md`** | **🆕 AI 18 个新接口契约（独立前缀 /api/v1/ai/*，0 破坏老接口）** |
| `BACKEND.md` | FastAPI 技术栈 + 25 张表 DDL + RBAC 权限矩阵 + 进场清单 |
| `OCR-选型.md` | PaddleOCR 自建 + 诺诺兜底（月成本 < ¥300） |
| `PaddleOCR-部署指南.md` | 🆕 PaddleOCR 工程师专用的部署 + 接口对接指南 |
| `DESIGN-TOKENS.md` | 完整设计 Token 字典（颜色/字体/间距/组件） |
| `E2E-TESTING.md` | Playwright 测试样例 + Mock Server |
| `ROADMAP.md` | 完整 Roadmap（技术 + 交付双视角） |

## 4. 部署

```bash
cd deploy
cp .env.example .env
docker compose up -d
# 启用监控（可选）
docker compose --profile monitoring up -d
```

详见 `deploy/README.md` + `deploy/monitoring/README.md`。

---

## 5. 本地预览（仅设计稿）

```bash
cd design
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080
# 推荐入口：http://localhost:8080/index.html
```

**亮点页面**（优先看这几个）：
- `index.html` — 设计稿目录
- `dashboard.html` — 工作台
- `invoice-ocr-batch.html` — SSE 实时通信
- `ai-center.html` 🆕 — AI 数智化能力中心
- `ai-extract-demo.html` 🆕 — 字段抽取交互
- `ai-panel-project.html` 🆕 — AI 分析 Tab 范例
- `components-states.html` — 所有状态/AI 组件 Demo

---

## 6. 已确认的技术决策

| 决策 | 方案 |
|------|------|
| 前端样式 | 纯 HTML + 公共 CSS（科技金融风） |
| 后端栈 | **Python 3.11 + FastAPI + PostgreSQL 15 + Redis 7 + Celery 5** |
| 实时通信 | **SSE**（不用轮询） |
| OCR | **PaddleOCR 自建** + 诺诺兜底 |
| 数据存储 | **金额用分（BIGINT）** · 状态用 VARCHAR + CHECK |
| 权限 | **RBAC**（9 角色 × 6 资源 + 数据范围 all/dept/self/custom） |
| AI 能力 | **PaddleOCR（OCR）+ Qwen2.5（LLM）+ 自研风险模型 v2.3** |
| AI 接口 | **统一前缀 `/api/v1/ai/*`，0 破坏老接口，老 SSE 通道直接复用** |
| AI 部署 | 独立 `ai-service` 容器（与后端解耦，挂可降级） |
| 部署 | Docker Compose（含 OCR/AI 微服务 + 监控 profile） |
| E2E | Playwright + MSW（前端可独立跑测试） |
| 移动端 | CSS @media 响应式（< 640px 全屏抽屉） |

---

## 7. 后续工作（按优先级）

详见 `ROADMAP.md`。最高优先级：
1. 后端代码实现（4-6 周）
2. PaddleOCR 真实部署（参考 `PaddleOCR-部署指南.md`）
3. 5 大业务模块的 API 联调
4. 🆕 AI 数智化能力开发（参考 `AI-API.md`，独立里程碑，不阻塞主线）
5. CI/CD 流水线

---

## 8. 关键文件

| 路径 | 说明 |
|------|------|
| `design/assets/common.css` | 设计系统（13+ 业务组件 + 14 类 AI 组件 + 响应式） |
| `design/API.md` | 老 API 契约（59 接口） |
| `design/AI-API.md` | 🆕 AI 接口契约（18 必出接口 + DDL + 降级） |
| `design/BACKEND.md` | 后端架构基线 |
| `design/PaddleOCR-部署指南.md` | 🆕 PaddleOCR 部署 + 对接指南 |
| `design/ai-center.html` | 🆕 AI 中心主页 |
| `deploy/docker-compose.yml` | 一键部署 |
| `backend/ONBOARDING.md` | 后端工程师进场指引 |
