# 数智化管理系统 · 项目手册（PROJECT_HANDBOOK）

> **项目交接 / 演示 / 汇报一站式索引**  
> **创建**：2026-06-15（R15 文档整理）  
> **覆盖**：R1 ~ R14 全部阶段交付物  
> **目标读者**：运维 / 业务 / 新接手开发 / 评审 / 演示客户

---

## 0. 阅读指南

| 你是谁 | 看哪些章节 |
|---|---|
| **运维**（接手部署） | 1.项目概览 → 3.产出物索引（deploy/scripts/） → 4.集成切真 → 5.后续 |
| **业务**（了解功能） | 1.项目概览 → 2.R1-R14 阶段交付（看业务功能上线节点） → 5.后续 |
| **新开发**（接手代码） | 1.项目概览 → 3.产出物索引（frontend/ backend/） → design/API.md + design/BACKEND.md |
| **PM**（汇报 / 演示） | 1.项目概览 → 2.阶段交付（关键数字） → 4.集成切真（资质等待） |
| **评审 / 客户** | 1.项目概览 → 2.阶段交付（一句话+数字） → 6.截图索引（看 38 vue 1:1 复刻） |

---

## 1. 项目概览

### 1.1 是什么

**数智化管理系统** —— 企业自用财务/业务一体化系统。  
- **不是** SaaS / 多租户
- **是** 内部系统（单租户、强审计、细权限）
- **6 大业务模块**：发票识别 / 发票模板 / 销售费用 / 项目管理 / 合同管理 / 回款管理
- **22 AI 触点**（R10 接入） + 3 套真实集成（PaddleOCR / 诺诺 / 企业微信 SSO）

### 1.2 技术栈

```
前端：Vue 3 + Vite + TypeScript + Element Plus + Pinia + Vue Router 4
后端：Python 3.11 + FastAPI + SQLAlchemy 2 (async) + Pydantic v2
数据库：PostgreSQL 15 + Redis 7
集成：PaddleOCR / 诺诺开放平台 / 企业微信 OAuth
监控：Prometheus + Grafana + Alertmanager
部署：Docker + Docker Compose
测试：Playwright (E2E) + k6 (压测)
```

### 1.3 架构图

```
                        ┌──────────┐
                        │  Nginx   │  :80  (:8088 docker)
                        └─────┬────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
        │ Frontend  │   │  Backend  │   │   OCR     │  shuzhi-ocr-service
        │ (Vue 3)   │   │ (FastAPI) │◄──┤  Service  │  PaddleOCR ch_PP-OCRv4
        │ :8088     │   │ :8000     │   │  :8001    │
        └───────────┘   └─────┬─────┘   └───────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
        │PostgreSQL │   │   Redis   │   │  SSE Bus  │  Redis Pub/Sub
        │   :5432   │   │   :6379   │   └───────────┘
        └───────────┘   └───────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
        │Prometheus │   │  Grafana  │   │Alertmanager│
        │   :9090   │   │   :3000   │   │   :9093    │
        └───────────┘   └───────────┘   └────────────┘
```

### 1.4 关键数字（截至 R14C）

| 维度 | 数字 |
|---|---|
| 前端 .vue 文件 | **38 个**（业务页）+ 8 个 AI 组件 + 8 个 common 组件 + 1 PWA 组件 |
| 后端 API 接口 | **128 个**（12 类：合同/项目/费用/回款/发票/admin/ai/auth/common/cron/dashboard/other） |
| DB 数据 | 37 合同 / 7 项目 / 多费用 / 25 发票 / 8 部门 / 多用户 |
| E2E 测试 | **14 个 Playwright 套件 + 1 暗色 spec**（全过） |
| 压测场景 | **3 个 k6 场景**（基线 20 RPS P95 14ms） |
| 真实集成 | **PaddleOCR 已切真** / 诺诺/企微 等资质 |
| 前端构建 | index 12KB / CSS 27KB / 12 domain chunk 24-88KB |
| 后端 worker | 4 uvicorn workers（稳定 20 RPS） |
| 监控指标 | 50+ Prometheus 自定义（business_ocr / db_query / data_scope / ...） |

---

## 2. R1-R14 阶段交付（按时间顺序）

> 每阶段一句话 + 关键数字 + 详细报告路径。完整细节看对应 R* 报告。

### R1-R2 基础设施
- **R1**：项目初始化、基础架构、设计系统（design/*.html + common.css）
- **R2**：设计稿 5 页 + 登录 + Dashboard 基础

### R3-R4 业务后端 + 前端基础
- **R3**：后端核心模块（合同/项目/费用/回款/发票）+ DB schema
- **R4**：前端基础页（登录 + Dashboard + 发票识别）
- 📄 [R3-REPORT.md](R3-REPORT.md) | [R4-REPORT.md](R4-REPORT.md)

### R5-R6 业务扩展
- **R5**：6 大业务模块列表页（合同/项目/费用/回款/发票模板/发票识别）
- **R6**：详情页 + 编辑器 + Drawer 交互
- 📄 [R5-REPORT.md](R5-REPORT.md) | [R6.2-REPORT.md](R6.2-REPORT.md) | [R6.3-R6.5-REPORT.md](R6.3-R6.5-REPORT.md)

### R7 设计系统 + 监控 + 体验
- **R7**：详细设计稿（33 design HTML）+ 业务 1:1 复刻设计
- 📄 [R7-REPORT.md](R7-REPORT.md) | [PRODUCTION-READY-REPORT.md](PRODUCTION-READY-REPORT.md) | [GO-LIVE-REPORT.md](GO-LIVE-REPORT.md)

### R8-R9 1:1 复刻（38 vue）
- **R8**：菜单修复 + 4 tab 单页化
- **R9**：33 design HTML → 28+ vue 1:1 复刻（实际 38 vue，含 admin + 通知 + AI 中心）
- 📄 [R9-FINAL-REPORT.md](R9-FINAL-REPORT.md)（**467 行完整总览**） | [R9-P5C-REPORT.md](R9-P5C-REPORT.md) | [R9-P7-REPORT.md](R9-P7-REPORT.md) | [R9-P7A-REPORT.md](R9-P7A-REPORT.md) | [R9-P7B-REPORT.md](R9-P7B-REPORT.md) | [R9-P8-REPORT.md](R9-P8-REPORT.md)

### R10 22 AI 触点 + 体验增强
- **R10A 性能优化**：index.js 99KB→12KB（-88%），CSS 385KB→27KB（-93%），12 domain chunk
- **R10B 权限细化**：data_scope 5 档（admin 37 / 张明 19 / 刘洋 4 / 王芳 9），v-permission 指令
- **R10C 真实集成切真文档**：3 套集成代码 + 自动 fallback + 0 代码改动
- 📄 [R10A-REPORT.md](R10A-REPORT.md) | [R10B-REPORT.md](R10B-REPORT.md) | [R10C-REPORT.md](R10C-REPORT.md)

### R11 性能 + 权限 + 切真文档深耕
- **R11A 性能** + **R11B 权限细化** + **R11C 真实集成切真文档**（400+ 行 INTEGRATION_DEPLOY + 资质清单 + 一键脚本）
- 📄 [R11A-REPORT.md](R11A-REPORT.md) | [R11B-REPORT.md](R11B-REPORT.md) | [R11C-REPORT.md](R11C-REPORT.md)

### R12 PaddleOCR 真实切真 🎉
- PaddleOCR 容器已部署 + URL 配对 + /health 显示 `status=ok` + E2E test-08 真发票 7/7 字段 confidence 0.941
- 📄 [R12-REPORT.md](R12-REPORT.md)

### R13 一键上线全流程演练 SOP
- 升级 cutover-real-integrations.sh（199 → 410+ 行）+ 写完整 CUTOVER_SOP.md（410 行 5 段流程）
- 跑 PaddleOCR 切真完整流程验证 SOP 可用
- 📄 [R13-REPORT.md](R13-REPORT.md) | [CUTOVER_SOP.md](CUTOVER_SOP.md)

### R14 暗色 + 压测 + PWA 三件套 ⭐
- **R14A 暗色模式**：body #0F1320 + 49 行 CSS 覆写 + 5 页 E2E 验证
- **R14B 压测基线**：k6 + 3 场景 + 业务核心 20 RPS P95 14ms 0% 错
- **R14C PWA**：vite-plugin-pwa + 43 项 precache + 5 路由缓存策略 + 离线降级 + 安装提示
- 📄 [R14-REPORT.md](R14-REPORT.md) | [R14C-REPORT.md](R14C-REPORT.md)

---

## 3. 产出物索引（按类型）

### 3.1 报告文档（根目录）

| 报告 | 行数 | 覆盖范围 |
|---|---|---|
| GO-LIVE-REPORT.md | 260+ | 部署架构 + 上线步骤 + 容器管理 + R8/R9 段 |
| R9-FINAL-REPORT.md | 467 | 38 vue 1:1 复刻总览 |
| R3 ~ R8 报告 | 各 200-500 | 各阶段交付 |
| R10A / R10B / R10C | 各 ~250 | 22 AI 触点 / 权限 / 切真 |
| R11A / R11B / R11C | 各 ~200 | 性能深耕 / 权限细化 / 切真文档 |
| R12 / R13 / R14 / R14C | 各 ~120-200 | PaddleOCR 切真 / 一键切真 / 暗色压测PWA |
| CUTOVER_SOP.md | 410 | 真实集成切真 5 段 SOP |
| INTEGRATION_DEPLOY.md | 368 | 3 套集成架构 + 切真步骤 |
| INTEGRATION_CHECKLIST.md | 201 | 资质等待清单 |
| PROJECT-READY-REPORT.md | - | R7 阶段生产就绪 |
| **本文件 PROJECT_HANDBOOK.md** | - | **R15 全流程索引** |

### 3.2 设计文档（design/）

| 文档 | 用途 |
|---|---|
| [design/README.md](design/README.md) | 设计系统入口 |
| [design/API.md](design/API.md) | 46 个 API 接口规范 |
| [design/BACKEND.md](design/BACKEND.md) | 后端架构 + 集成协议 |
| [design/AI-API.md](design/AI-API.md) | 22 AI 触点协议 |
| [design/DESIGN-TOKENS.md](design/DESIGN-TOKENS.md) | 设计令牌（颜色/圆角/阴影） |
| [design/OCR-选型.md](design/OCR-选型.md) | OCR 选型分析 |
| [design/E2E-TESTING.md](design/E2E-TESTING.md) | E2E 测试指南 |
| [design/ROADMAP.md](design/ROADMAP.md) | 项目路线图 |
| `design/*.html` | 33 个静态设计稿（1:1 复刻 source of truth） |
| `design/assets/common.css` | 公共 CSS 令牌（与 design system 1:1 对齐） |

### 3.3 代码目录

```
frontend/                              # Vue 3 + Vite + Element Plus + TS
├── src/
│   ├── views/                         # 38 业务页 + admin + error + notice
│   │   ├── auth/Login.vue
│   │   ├── contract/  (4 vue)         # List/Detail/Create/Template
│   │   ├── project/   (3 vue)         # List/Detail/Create
│   │   ├── expense/   (3 vue)         # List/Detail/Create
│   │   ├── receivable/(3 vue)         # List/Detail/Create
│   │   ├── invoice/   (8 vue)         # OCR/List/Detail/Template + Edit
│   │   ├── ai/        (10 vue)        # 22 触点 + 4 drawer
│   │   ├── admin/     (4 vue)         # User/Role/Dept/Dict
│   │   ├── client/    (2 vue)         # List/Create
│   │   ├── dashboard/ (1 vue)         # Dashboard
│   │   ├── notice/    (1 vue)
│   │   └── error/     (4 vue)         # 403/404/500/network
│   ├── components/                    # 通用组件
│   │   ├── common/  (8 vue)           # PageHeader/StatCard/FormField/TagPill/...
│   │   ├── ai/      (8 vue)           # AIConfidence/AIRiskChip/AIAlertBar/...
│   │   ├── PWAInstallPrompt.vue       # R14C 新增
│   │   ├── AiDrawer.vue
│   │   └── StatGrid.vue
│   ├── stores/                        # Pinia 状态
│   ├── api/                           # API 客户端
│   ├── layouts/AppLayout.vue          # 主布局（含暗色切换 + PWA 组件）
│   ├── router/                        # 路由
│   ├── directives/permission.ts       # R11B v-permission 指令
│   ├── assets/styles/                 # design tokens + ai.scss（暗色覆写）
│   └── auto-imports.d.ts
├── public/                            # 静态资源
│   ├── pwa-192x192.png                # R14C PWA icon
│   ├── pwa-512x512.png
│   ├── pwa-icon.svg
│   ├── apple-touch-icon.png
│   ├── favicon-32x32.png
│   └── offline.html                   # R14C 离线降级页
├── e2e/                               # Playwright + dark-mode
│   ├── dark-mode-playwright.spec.js   # R14A
│   └── test-01 ~ test-14.js
├── vite.config.ts                     # 含 VitePWA plugin
├── package.json
└── perf/                              # R14B 压测
    ├── scenarios/
    │   ├── scenario-1-login-dashboard.js
    │   ├── scenario-2-business-core.js
    │   └── scenario-3-ai-mock.js
    ├── scripts/gen_report.py
    └── reports/
        ├── scenario-{1,2,3}-report.md
        └── scenario-{1,2,3}-summary.json

backend/                               # Python 3.11 + FastAPI
├── app/
│   ├── main.py                        # FastAPI 入口（含 /health 聚合）
│   ├── config.py                      # pydantic-settings（env_prefix=SHUZHI_）
│   ├── core/                          # 核心工具
│   │   ├── security.py                # JWT + 权限（含 data_scope）
│   │   ├── data_scope.py              # R11B 5 档过滤
│   │   ├── cache.py                   # R11A @cache 装饰器
│   │   ├── metrics.py                 # prometheus 50+ 指标
│   │   └── database.py                # SQLAlchemy + R11A 慢查询监听
│   ├── modules/                       # 13 业务模块
│   │   ├── contract/ (router/service/schemas)
│   │   ├── project/
│   │   ├── expense/
│   │   ├── receivable/
│   │   ├── invoice_ocr/
│   │   ├── invoice_template/
│   │   ├── invoice_verify/
│   │   ├── admin/  (含 4 处 Redis 缓存)
│   │   ├── ai/     (22 触点)
│   │   ├── dashboard/
│   │   ├── auth/   (JWT + SSO)
│   │   ├── common/ (dict/users/upload)
│   │   └── cron/   (定时任务)
│   └── integrations/                  # 真实集成
│       ├── ocr_client.py              # PaddleOCR（已切真）
│       ├── nuonuo.py                  # 诺诺发票云（mock）
│       ├── wechat_work.py             # 企业微信 SSO（mock）
│       └── storage.py
├── alembic/                           # DB migration
├── tests/
└── requirements.txt

deploy/                                # 部署
├── docker-compose.yml                 # 主 compose
├── docker-compose.integration.yml     # 集成测试 compose
├── frontend/nginx.conf                # 前端 nginx 配置
├── backend/Dockerfile
├── ocr-service/Dockerfile             # PaddleOCR 容器
├── monitoring/
│   ├── prometheus.yml                 # 抓取配置
│   ├── alerts.yml                     # 告警规则（含 3 套集成 fallback 告警）
│   ├── alertmanager.yml
│   ├── grafana-provisioning/
│   │   ├── datasources/prometheus.yml
│   │   └── dashboards/shuzhi.yml
│   └── grafana-dashboard.json
├── scripts/
│   └── cutover-real-integrations.sh   # R13 一键切真（410+ 行）
├── initdb.d/                          # DB 初始化 SQL
└── fake-services/                     # 集成测试用的 fake 服务

docs/screenshots/compare/              # 截图库（116 张）
├── 1-design-*.png    (31 张)          # 设计稿基线
├── 2-real-*.png      (73 张)          # 真实渲染（按 R 阶段拆）
├── 3-real-r14a-*     (10 张)          # R14A 暗色 / 浅色对比
└── 4-real-r14c-*     (2 张)           # R14C PWA manifest + icon
```

### 3.4 截图索引（按 R 阶段）

| 阶段 | 数量 | 路径 |
|---|---|---|
| **设计稿基线** | 31 张 | `docs/screenshots/compare/1-design-*.png` |
| **R9 真实渲染** | ~50 张 | `docs/screenshots/compare/2-real-{p5c,p7a,p7b,p7c,p8}-*.png` |
| **R10A 性能** | 5 张 | `docs/screenshots/compare/2-real-r10a-*.png` |
| **R10B 权限** | 5 张 | `docs/screenshots/compare/2-real-r10b-*.png` |
| **R10C 集成** | 5 张 | `docs/screenshots/compare/2-real-r10c-*.png` |
| **R11A 性能** | 4 张 | `docs/screenshots/compare/2-real-r11a-*.png` |
| **R11B 权限** | 5 张 | `docs/screenshots/compare/2-real-r11b-*.png` |
| **R11C 切真** | 5 张 | `docs/screenshots/compare/2-real-r11c-*.png` |
| **R12 PaddleOCR** | 1 张 | `docs/screenshots/compare/2-real-r12-01-health-ocr-real.png` |
| **R13 SOP 演练** | 1 张 | `docs/screenshots/compare/2-real-r13-01-cutover-ocr-real.png` |
| **R14A 暗色/浅色** | 10 张 | `docs/screenshots/compare/3-real-r14a-{light,dark}-*.png` |
| **R14C PWA** | 2 张 | `docs/screenshots/compare/4-real-r14c-pwa-{manifest,icon}.png` |
| **总计** | **116 张** | |

### 3.5 关键配置

| 配置 | 路径 | 说明 |
|---|---|---|
| Docker Compose | `deploy/docker-compose.yml` | 9 容器（postgres/redis/backend/frontend/ocr/nginx/sse/prom/grafana） |
| 集成测试 Compose | `deploy/docker-compose.integration.yml` | R12/R13 用 |
| 前端 nginx | `deploy/frontend/nginx.conf` | SPA history 路由 + 静态资源 |
| Prometheus | `deploy/monitoring/prometheus.yml` | 抓 /metrics 端点 |
| 告警规则 | `deploy/monitoring/alerts.yml` | 含 3 套集成 fallback 告警 |
| Grafana Dashboard | `deploy/monitoring/grafana-dashboard.json` | 业务大盘 |
| 后端 Settings | `backend/app/config.py` | pydantic-settings（env_prefix=SHUZHI_） |
| 前端 vite | `frontend/vite.config.ts` | 含 VitePWA + manualChunks |

---

## 4. 真实集成切真指南

### 4.1 当前状态

| 集成 | 代码 | 文档 | 切真状态 | 资质等待 |
|---|---|---|---|---|
| **PaddleOCR** | ✅ | ✅ | ✅ **已切真** | — |
| **诺诺发票云** | ✅ | ✅ | ⏳ mock | 企业营业执照（1-3 工作日审核） |
| **企业微信 SSO** | ✅ | ✅ | ⏳ mock | 公网域名 + SSL（1-2 周 IT 申请） |

### 4.2 已切真的 PaddleOCR 演练证据

- `/health` 返回 `integrations.ocr.status = ok`（ch_PP-OCRv4）
- E2E test-08 真发票 7/7 字段 confidence 0.941
- Prometheus `shuzhi_business_ocr_total{mode="real",status="success"} 1.0`
- 截图：`2-real-r12-01-health-ocr-real.png` / `2-real-r13-01-cutover-ocr-real.png`

### 4.3 切真操作（一键脚本）

```bash
# 切 PaddleOCR（已切，仅演练）
cd /Users/trisome/Desktop/开发/数智化系统new
./deploy/scripts/cutover-real-integrations.sh ocr --dry-run     # 演练
./deploy/scripts/cutover-real-integrations.sh ocr              # 真切
./deploy/scripts/cutover-real-integrations.sh ocr --no-restart  # 只写 env

# 切诺诺（等凭证后 5 分钟）
export SHUZHI_NUONUO_API_KEY=...
export SHUZHI_NUONUO_API_SECRET=...
export SHUZHI_NUONUO_API_TOKEN=...
./deploy/scripts/cutover-real-integrations.sh nuonuo

# 切企微（等域名+凭证后 5 分钟）
export SHUZHI_WECHAT_WORK_CORP_ID=ww...
export SHUZHI_WECHAT_WORK_CORP_SECRET=...
export SHUZHI_WECHAT_WORK_AGENT_ID=1000002
export SHUZHI_WECHAT_WORK_REDIRECT_URI=https://yourdomain.com/api/v1/auth/sso/wechat-work/callback
./deploy/scripts/cutover-real-integrations.sh wechat-work

# 3 套一起切
./deploy/scripts/cutover-real-integrations.sh all
```

### 4.4 自动 fallback 机制（永不挂）

每套集成代码都有 **real → mock 自动降级**：
- **PaddleOCR**：连不上 → mock（业务不停）
- **诺诺**：签名错 / 配额耗尽 / 网络断 → mock
- **企微**：corpsecret 改 / 回调域失效 → 用户操作失败（前端跳"登录失败"）

监控告警（已配置）：
- `rate(shuzhi_business_ocr_total{mode="real→mock_fallback"}[5m]) > 0` → OCR 服务挂了
- `rate(shuzhi_business_verify_total{mode="real→mock_fallback"}[5m]) > 0` → 诺诺挂了

### 4.5 完整 SOP 文档

- 📄 [CUTOVER_SOP.md](CUTOVER_SOP.md) — 5 段流程（410 行）
- 📄 [INTEGRATION_DEPLOY.md](INTEGRATION_DEPLOY.md) — 3 套集成架构 + 切真步骤
- 📄 [INTEGRATION_CHECKLIST.md](INTEGRATION_CHECKLIST.md) — 资质等待清单

---

## 5. 后续工作清单（不影响当前使用）

### 5.1 P0 阻塞（资质等待）

| 项 | 负责人 | 预估 | 阻塞点 |
|---|---|---|---|
| 诺诺开放平台账号 | 业务部 | 1-3 工作日 | 企业营业执照 |
| 诺诺自用应用审批 | 业务部 | 1-3 工作日 | 应用审核 |
| 企业微信企业认证 | 行政/IT | 3-5 工作日 | 营业执照 + 法人微信 |
| **公网域名 + SSL** | **IT** | **1-2 周** | **企业微信硬阻塞** |

### 5.2 P1 性能优化（基线已知，扩 worker）

| 项 | 当前 | 目标 | 行动 |
|---|---|---|---|
| 后端 worker 数 | 4 | 8-16 | 改 uvicorn --workers 8 |
| Redis 缓存覆盖 | admin 4 处 | 业务 12 接口 | R11A 套路复用 |
| 前端 domain chunk | 24-88KB | 进一步 tree-shake | 分析各 chunk 内容 |
| 慢 SQL 优化 | 50+ 慢查询已记录 | 索引 + 重写 | 看 prom `db_slow_queries_total` |

### 5.3 P1 PWA 真机验证

| 项 | 状态 | 行动 |
|---|---|---|
| 浏览器 PWA 检测 | ✅ dev tools 验证 | 已注册 + manifest OK |
| iOS Safari 安装 | ⏳ 未测 | 需真机 HTTPS |
| Android Chrome 安装 | ⏳ 未测 | 需真机 HTTPS |
| 离线降级实测 | ⏳ 未测 | DevTools 切 offline |
| PWA 提示弹窗 | ⏳ 真机未测 | 7 天冷却逻辑需真机触发 |

### 5.4 P2 暗色模式完善

| 项 | 状态 | 行动 |
|---|---|---|
| 38 业务页 1:1 暗色视觉验收 | R14A 已 5 页验证 | 剩余 33 页逐页扫 |
| 设计稿 1:1 复刻破坏感 | 渐变降饱和可能不完美 | 截图比对 → 微调 |
| 暗色模式持久化 | ✅ localStorage | 跨标签页同步可加 |

### 5.5 P2 其他

- **告警通知渠道**：Alertmanager 已配置，需接 Slack / 飞书 / 邮件
- **审计日志查询 UI**：后端审计已记，无可视化页
- **数据导入**：现有 mock 数据，可加 Excel 导入
- **API 限流**：128 接口无 rate limit（防刷）
- **CI/CD**：当前手工 docker 三连，可加 GitHub Actions

---

## 6. 演示路径（5 分钟给客户看）

### 6.1 推荐演示顺序

1. **登录** → 展示 SSO 按钮（账号密码 + 企业微信/钉钉 + 记住我）
2. **Dashboard** → 展示 6 大模块数据 + AI 智能建议
3. **合同管理** → 列表 → 详情（渐变 Hero + 审批流可视化 + 业绩进度条）
4. **AI 中心** → 22 触点全景 → 单触点详情（风险扫描 11 区块）
5. **发票识别** → 上传真实发票 → 7/7 字段自动识别（confidence 0.94）
6. **暗色模式** → 一键切换 → 演示沉浸式
7. **离线/移动** → DevTools 切 offline → 离线降级页

### 6.2 关键演示数据

- **合同** HT-2026-994（金额测试）100,000 元
- **项目** 北辰实业集团数智化转型项目
- **发票** INV-2026-06-15-8DC（茶馆 248 元，invoiceNo 26112000001961698396）
- **AI** 22 触点全景，置信度 0.6-0.95 区间

### 6.3 演示账号

- `admin / admin123`（超级管理员，27 权限，* 通配符）
- `zhangming / test123`（部门主管，19 数据）
- `liuyang / test123`（普通员工，4 数据）
- `wangfang / test123`（部门经理，9 数据）

---

## 7. 容器与命令速查

```bash
# === 查看所有容器 ===
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# === 关键服务 ===
shuzhi-frontend     80  :8088    前端
shuzhi-backend      8000:8000    后端（4 workers）
shuzhi-postgres     5432         DB
shuzhi-redis        6379         缓存 + Pub/Sub
shuzhi-ocr-service  8001         PaddleOCR（已切真）
shuzhi-prometheus   9090         监控
shuzhi-grafana      3000         大盘
shuzhi-nginx        80           反代

# === 关键命令 ===
curl http://localhost:8000/health                       # 聚合健康
curl http://localhost:8000/openapi.json | python3 -m json.tool  # 128 接口
curl http://localhost:8000/metrics                      # 50+ prom 指标
docker logs shuzhi-backend --tail 30                    # 后端日志
docker exec shuzhi-postgres psql -U shuzhi shuzhi        # 进 DB
docker exec shuzhi-redis redis-cli                       # 进 Redis

# === 重启服务 ===
docker restart shuzhi-backend
docker restart shuzhi-frontend
docker restart shuzhi-ocr-service

# === 切真集成 ===
./deploy/scripts/cutover-real-integrations.sh all
```

---

## 8. 变更记录

| 日期 | R | 变更 |
|---|---|---|
| 2026-06-14 上午 | R3-R4 | 项目基础 + 6 大业务模块 |
| 2026-06-14 下午 | R5-R7 | 详情页 + 设计系统 + 监控 |
| 2026-06-14 晚上 | R8-R9 | 38 vue 1:1 复刻完成 |
| 2026-06-15 上午 | R10 | 22 AI 触点 + 体验增强 |
| 2026-06-15 上午 | R11 | 性能 + 权限 + 切真文档深耕 |
| 2026-06-15 上午 | R12 | **PaddleOCR 真实切真成功** |
| 2026-06-15 上午 | R13 | 一键切真 SOP + 完整演练 |
| 2026-06-15 上午 | R14 | 暗色 + 压测 + PWA 三件套 |
| 2026-06-15 上午 | R15 | **本手册：R1-R14 全流程索引** |

---

## 9. 联系与交接

**当前状态**：开发完成，4 套生产集成中 1 套已切真（PaddleOCR），2 套等资质，1 套（监控告警）已配。  
**代码仓库**：`/Users/trisome/Desktop/开发/数智化系统new/`（暂未 git init）  
**接手建议**：运维先看 `GO-LIVE-REPORT.md` + 本文件 1-3 章节，业务先看 `R9-FINAL-REPORT.md`。

---

**手册版本**：v1.0 | 2026-06-15  
**维护**：R15 一次性整理，后续每 R 阶段更新一次
