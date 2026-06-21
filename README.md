# 数智化管理系统（企业自用）

> **项目代号**：shuzhi
> **目标**：业务 + 财务一体化（项目管理 / 合同 / 销售费用 / 发票识别 / 发票模板 / 回款 / 凭证）
> **技术栈**：FastAPI + PostgreSQL + Redis + 原生 HTML/CSS/JS（设计稿）
> **状态**：设计稿 + 后端骨架完成，进入开发实施阶段

---

## 0. 目录结构

```
数智化系统new/
├── README.md              ← 你正在看这个
├── design/                ← 前端设计稿（28 个 HTML + 6 份文档 + 设计系统）
│   ├── index.html         ← 设计稿首页
│   ├── login.html         ← 登录页
│   ├── dashboard.html     ← 工作台
│   ├── project.html       ← 项目管理
│   ├── contract.html      ← 合同管理
│   ├── sales-expense.html ← 销售费用
│   ├── invoice-ocr.html   ← 发票识别
│   ├── invoice-template.html  ← 发票模板
│   ├── receivable.html    ← 回款管理
│   ├── client-create.html ← 客户管理
│   ├── template-create.html ← 凭证模板
│   ├── 6 个 create.html   ← 各模块的创建表单
│   ├── 4 个 detail.html   ← 各模块的详情页
│   ├── 3 个 OCR 子页面    ← 批次/记录/核验
│   ├── 4 个 error 页      ← 403/404/500/网络错误
│   ├── components-states.html  ← 状态组件 Demo
│   ├── assets/common.css  ← 设计系统（13+ 组件 + 移动端响应式）
│   ├── API.md             ← 59 个接口 + SSE 实时通信
│   ├── BACKEND.md         ← 后端架构基线（25 张表 + RBAC）
│   ├── DESIGN-TOKENS.md   ← 设计 token
│   ├── E2E-TESTING.md     ← 端到端测试用例
│   ├── OCR-选型.md        ← OCR 选型
│   ├── ROADMAP.md         ← Roadmap（技术+交付）
│   └── README.md          ← 设计稿使用说明
├── backend/               ← FastAPI 后端骨架
│   ├── app/               ← 业务代码
│   ├── alembic/           ← 数据库迁移
│   ├── scripts/seed.py    ← 种子数据
│   ├── tests/             ← pytest 测试（32 个用例）
│   ├── requirements.txt
│   ├── ONBOARDING.md      ← 新后端 1 小时上手
│   └── README.md
└── deploy/                ← Docker 部署套件
    ├── docker-compose.yml
    ├── .env.example
    ├── frontend/         ← 前端 Dockerfile + nginx.conf
    ├── backend/          ← 后端 Dockerfile
    ├── ocr-service/      ← PaddleOCR Dockerfile
    ├── monitoring/       ← Prometheus + Grafana + 告警规则
    └── README.md
```

---

## 1. 5 分钟看清项目

### 我是谁？
- **PM**（产品经理）的个人副业项目
- **场景**：企业（10-50 人）的业务 + 财务一体化
- **核心痛点**：Excel + 微信群管业务，效率低、易出错、无审计
- **目标用户**：业务部门（项目、合同、发票） + 财务部门（回款、凭证）

### 核心功能
1. **项目管理**：立项 / 进度 / 团队 / 里程碑 / Dashboard
2. **合同管理**：起草 / 审核 / 状态流转 / 与项目关联
3. **销售费用**：报销 / 审批 / 与项目关联
4. **发票识别**：拍照 / 批量上传 / OCR 识别 / 国税查验 / 字段抽取
5. **发票模板**：自定义字段 / 智能识别
6. **回款管理**：客户付款 / 到账登记 / 与合同关联
7. **凭证模板**：财务记账模板

### 设计风格
- **C 风格（科技金融风）**：深色侧栏 `#0B1220` + 蓝紫渐变 `#4F6BFF → #7C3AED`
- **响应式**：桌面 4 种宽度（1280/1440/1680/1920），移动端 < 640px
- **完整设计系统**：13+ 类核心组件 + 状态 Demo

### 技术选型
| 层 | 选型 | 理由 |
|------|------|------|
| **后端** | Python 3.11 + FastAPI | 高性能 + 异步 + 类型提示 + 自动 Swagger |
| **数据库** | PostgreSQL 15 | JSONB / 全文检索 / 成熟稳定 |
| **缓存** | Redis 7 | Pub/Sub 支撑 SSE + 缓存 |
| **实时通信** | SSE（不用 WebSocket） | 单向 + 简单 + 浏览器原生 + HTTP/2 多路复用 |
| **异步任务** | Celery 5 | OCR 识别 / 异步通知 / 报表生成 |
| **OCR** | PaddleOCR 自建 + 诺诺兜底 | 免费 + 准确率 90%+ |
| **前端** | 原生 HTML/CSS/JS（设计稿） | 第一版用纯静态，后续再考虑 Vue/React |
| **部署** | Docker Compose | 6 个服务一键起 |

---

## 2. 30 秒跑起来

```bash
# 1. 进入项目
cd /Users/trisome/Desktop/开发/数智化系统new

# 2. 启动后端（需先有 docker）
cp deploy/.env.example deploy/.env
# 编辑 deploy/.env 改 JWT_SECRET_KEY
cd deploy
docker compose up -d

# 3. 初始化数据库
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py

# 4. 访问
# 前端（设计稿）：直接用浏览器打开 design/index.html
# 系统：http://localhost  （默认 admin / admin123）
# Swagger：http://localhost/api/docs
# Prometheus：http://localhost:9090（需 docker compose --profile monitoring up -d）
```

---

## 3. 看设计稿

```bash
# 方式 1：直接打开
open design/index.html

# 方式 2：起个本地服务（推荐，避免 iframe/file:// 问题）
cd design
python3 -m http.server 8080
# 打开 http://localhost:8080
```

**设计稿包含 28 个页面**：
- 入口：login / dashboard
- 业务列表：project / contract / sales-expense / invoice-ocr / invoice-template / receivable / client
- 表单：各模块 create 页（7 个）
- 详情：contract-detail / project-detail / invoice-detail / receivable-detail
- OCR 子页：batch / records / verify
- 模板：template-create / invoice-template-edit
- 错误：403 / 404 / 500 / network
- 组件：components-states（状态 Demo）

---

## 4. 关键文档（按需看）

| 你是 | 必读 |
|------|------|
| **新前端** | `design/README.md` + `design/DESIGN-TOKENS.md` + `design/API.md` |
| **新后端** | `backend/ONBOARDING.md` ⭐ + `design/BACKEND.md` + `design/API.md` |
| **新 PM / 业务** | `design/README.md` + `design/ROADMAP.md` |
| **新 DevOps** | `deploy/README.md` + `deploy/monitoring/README.md` |
| **新算法** | `design/OCR-选型.md` |
| **新 QA** | `design/E2E-TESTING.md` |

---

## 5. 项目进度

### ✅ 已完成
- 28 个 HTML 页面（设计稿）
- 6 份核心文档（API/BACKEND/OCR/TOKENS/E2E/ROADMAP）
- 设计系统 common.css（13+ 组件 + 响应式）
- 后端工程骨架（FastAPI + 21 个 Python 文件）
- 后端 2 个完整模块（auth / project）作为样板
- 测试用例 32 个（pytest + SQLite 内存）
- Docker 部署套件（6 服务 + 监控）

### ⚪ 下一步
- 见 `design/ROADMAP.md`
- 第 1 周：跑通后端 + 接入 auth/project
- 第 2-3 周：合同 / 销售费用 / 回款 3 个模块
- 第 4 周：联调 + bug 修复
- 第 5 周：发票识别（接 PaddleOCR）
- 第 6-7 周：发票模板 / 凭证模板
- 第 8 周：压测 + 性能优化
- 第 9 周：上线

---

## 6. 联系

这是 PM 个人项目，所有问题先看文档，**问的时候带具体文档名 + 链接**。

---

**记住三件事**：
1. **金额单位**：数据库存分（BIGINT），API 返回元（Decimal）
2. **异步一切**：所有 DB 操作 `async` + `await`
3. **审计自动**：写接口走中间件，但 diff 要手动补
