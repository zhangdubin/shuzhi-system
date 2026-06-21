# 数智化管理系统 · 前端（Vue 3 + Element Plus + Pinia）

## 技术栈

- **Vue 3.4** + **TypeScript** + **Vite 5**
- **Element Plus 2.6**（中文 locale、auto-import）
- **Pinia 2**（用户/权限状态）
- **Vue Router 4**（路由守卫）
- **Axios**（拦截器 + token + 错误码映射）
- **Sass**（深色侧栏 + 蓝紫渐变设计系统）
- **ECharts**（Dashboard 图表备用）

## 目录

```
frontend/
├── src/
│   ├── api/          # API 封装（auth / modules / ai）
│   ├── assets/styles # 设计 token（variables.scss）+ global.scss
│   ├── components/   # 通用组件
│   ├── config/       # 侧栏菜单配置
│   ├── layouts/      # AppLayout（侧栏 + 顶栏 + 主内容）
│   ├── router/       # 路由 + 守卫
│   ├── stores/       # Pinia stores（user / auth）
│   ├── types/        # TS 类型（api.ts 等）
│   ├── utils/        # request.ts（axios 封装）
│   ├── views/        # 页面（auth / dashboard / project / contract / ...）
│   ├── App.vue
│   └── main.ts
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
├── .env              # VITE_API_PROXY=http://localhost:8000
└── .dockerignore
```

## 设计系统

- 风格：**科技金融**（深色侧栏 `#0B1220 → #111A2E` 渐变 + 蓝紫品牌 `#4F6BFF → #7C3AED` 渐变）
- 浅色卡片背景 `#FFFFFF`，主背景 `#F1F5F9`
- 圆角 6/10/14/20px，阴影 sm/md/lg + glow
- 完整 token 见 `src/assets/styles/variables.scss`
- 与 `design/assets/common.css` 视觉一致

## 本地开发

```bash
cd frontend
npm install
npm run dev
# 浏览器打开 http://localhost:5173
# Vite 会代理 /api/v1/* → http://localhost:8000
```

## 生产构建

```bash
npm run build
# 输出 dist/（含 JS/CSS 拆分）
```

## Docker

```bash
# 一键起前端（含后端/PG/Redis/OCR/诺诺）
cd deploy
DOCKER_BUILDKIT=0 docker compose -f docker-compose.integration.yml up -d --build
# 浏览器打开 http://localhost
```

nginx 配置 (`deploy/frontend/nginx.conf`)：
- 80 端口入口
- `/api/*` 代理到 `backend:8000/v1/*`
- `/sse/*` 保留长连接（24h）+ 禁缓冲（AI 流式响应）
- SPA fallback：`location /` → `try_files ... /index.html`
- 静态资源 1 年缓存，HTML 不缓存

## 凭据

```
账号：admin
密码：admin123
```

## 已实现页面

- ✅ 登录页（深色渐变背景 + 玻璃拟态卡片）
- ✅ 工作台 Dashboard（4 个统计卡 + 4 个快捷入口 + 系统状态）
- ✅ 项目列表（搜索 + 分页 + 状态标签 + 进度条）
- ✅ 合同列表
- ✅ 销售费用列表
- ✅ 回款列表
- ✅ 发票模板列表
- ✅ 发票识别（上传 + 真实调 `/api/v1/invoice/ocr/upload`）
- ✅ 发票查验（4 种 result 颜色化展示）
- ✅ AI 抽取（提交任务 + 步骤进度 + 轮询结果）
- ✅ AI 任务中心
- ✅ AI 智能预警
- ✅ 用户管理（含 admin 占位）
- ✅ 错误页 403/404
- ⏳ 各模块详情页 / 编辑器（占位中）

## 下一轮（待补）

1. 项目/合同/费用详情页（Drawer + 关联数据）
2. 编辑器（新建/编辑项目、合同、费用、回款、模板）
3. 权限管理（基于 hasPerm 渲染菜单/按钮）
4. SSE 流式响应（AI 抽取实时进度）
5. ECharts 图表（Dashboard 趋势）
6. Admin 4 子模块完整实现

## 与后端约定

| 前端 | 后端 | 说明 |
|------|------|------|
| `/api/v1/auth/login` | `POST` | 登录（直返业务对象，无 code 包装） |
| `/api/v1/auth/me` | `GET` | 当前用户 |
| `/api/v1/auth/logout` | `POST` | 登出 |
| `/api/v1/dashboard/stats` | `GET` | Dashboard 统计 |
| `/api/v1/project/list` | `GET` | 项目列表（page/pageSize/keyword） |
| `/api/v1/contract/list` | `GET` | 合同列表 |
| `/api/v1/expense/list` | `GET` | 费用列表 |
| `/api/v1/receivable/list` | `GET` | 回款列表 |
| `/api/v1/invoice-template/list` | `GET` | 发票模板列表 |
| `/api/v1/invoice/ocr/upload` | `POST` multipart | OCR 上传识别 |
| `/api/v1/invoice/verify/single` | `POST` | 验真 |
| `/api/v1/ai/extract/invoice` | `POST` | AI 抽取（异步） |
| `/api/v1/ai/tasks/:id` | `GET` | 任务详情 |
| `/api/v1/ai/tasks` | `GET` | 任务列表 |
| `/api/v1/ai/alerts` | `GET` | 预警列表 |

**响应统一格式**：
- 列表接口：`{ list: T[], total, page, pageSize }`
- 业务对象接口：直返 T（如登录、详情）
- 包装接口：`{ code: 0, data: T, message, traceId }`（code=0 成功，失败时统一拦截器弹 ElMessage）

**错误码**：
- 3001 业务限流
- 5101 AI 模型
- 5102 AI 超时
- 5103 AI 安全
- 5104 AI 格式
