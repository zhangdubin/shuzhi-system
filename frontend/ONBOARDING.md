# 前端工程师进场指引（Onboarding）

> **目标读者**：新加入的前端工程师
> **目标**：1 小时内把项目跑起来，2 小时内改一个页面，1 周内交付第一个 AI 触点
> **技术栈**：Vue 3.4 + TypeScript + Vite 5 + Element Plus 2.6 + Pinia 2 + Vue Router 4 + Axios + ECharts + Sass

---

## 0. 必读文档（30 分钟）

| 文档 | 必看章节 | 时间 |
|------|---------|------|
| `../README.md` | 整个项目总览 | 5 分钟 |
| `../FRONTEND-API-CONTRACT.md` | 全部 | 15 分钟（**最重要**） |
| `../FRONTEND-AI-INTEGRATION.md` | §0-§3 + 你要做的触点 | 10 分钟 |
| `../design/DESIGN-TOKENS.md` | 颜色/间距/圆角（看一遍） | 5 分钟 |
| **不读** `design/*.html` | 那是设计稿，已转为 .vue | 0 |

**配套代码资源**：
- `src/views/**/*.vue` — 43 个页面（设计稿已转 Vue）
- `src/api/**/*.ts` — 6 个 API 模块
- `src/stores/ai.ts` — AI 状态（已实现）
- `src/utils/sse.ts` — SSE 客户端（已实现）
- `src/assets/styles/ai.scss` — AI 14 类样式（已实现）

---

## 1. 5 分钟把项目跑起来

```bash
# 1. 进入前端目录
cd frontend

# 2. 装依赖（已有 node_modules 可跳过）
npm install

# 3. 启动 dev server
npm run dev
# 浏览器打开 http://localhost:5173
# Vite 会代理 /api/v1/* → 后端 http://localhost:8000
```

**预期看到**：
- 自动跳到 `/login`
- 账号 `admin` / 密码 `admin123`
- 登录后跳到 `/dashboard`
- 4 个统计卡 + 6 个模块入口

**如果后端没起**：
- Dashboard 统计会显示 `-`（用 `.catch(() => ...)` 容错）
- 列表页可能为空
- 不会崩溃

---

## 2. 项目结构

```
frontend/
├── public/                  # 静态资源
├── src/
│   ├── api/                 # API 封装（统一调用后端的入口）
│   │   ├── auth.ts          # 认证（login/logout/me/refresh）
│   │   ├── modules.ts       # 业务模块（dashboard/project/contract/...）
│   │   ├── client.ts        # 客户（RESTful 风格）
│   │   ├── admin.ts         # 后台管理（用户/角色/部门/字典）
│   │   └── ai.ts            # AI 平台（22 接口）
│   ├── assets/
│   │   └── styles/
│   │       ├── variables.scss    # 设计 token（颜色/字体/圆角/阴影）
│   │       ├── global.scss       # 全局样式（重置 + 工具类）
│   │       ├── detail.scss       # 详情页样式
│   │       └── ai.scss           # ⭐ AI 14 类样式（新）
│   ├── components/          # 通用组件
│   │   └── AiDrawer.vue     # AI 抽屉（合同/项目详情用）
│   ├── config/
│   │   └── menu.ts          # 侧栏菜单配置
│   ├── layouts/
│   │   └── AppLayout.vue    # 主布局（侧栏 + 顶栏 + 主内容）
│   ├── router/
│   │   └── index.ts         # 路由表 + 守卫
│   ├── stores/
│   │   ├── user.ts          # 用户/认证状态
│   │   └── ai.ts            # ⭐ AI 状态（任务/提醒/反馈，新）
│   ├── types/
│   │   └── api.ts           # TypeScript 类型
│   ├── utils/
│   │   ├── request.ts       # Axios 封装（拦截器 + 错误码映射）
│   │   └── sse.ts           # ⭐ SSE 客户端（新）
│   ├── views/               # 43 个页面
│   │   ├── auth/            # 登录
│   │   ├── dashboard/       # 工作台
│   │   ├── project/         # 项目（list/create/detail）
│   │   ├── contract/        # 合同（list/detail/template）
│   │   ├── expense/         # 销售费用
│   │   ├── receivable/      # 回款
│   │   ├── client/          # 客户
│   │   ├── invoice/         # 发票（OCR/template/verify）
│   │   ├── ai/              # ⭐ AI 中心（extract/tasks/alerts/panel）
│   │   ├── admin/           # 后台管理
│   │   └── error/           # 错误页
│   ├── App.vue
│   ├── main.ts              # 入口
│   └── auto-imports.d.ts    # 自动生成的类型（unplugin-auto-import）
├── index.html               # 入口 HTML
├── vite.config.ts           # Vite 配置
├── tsconfig.json
├── package.json
├── .env                     # VITE_API_PROXY
├── Dockerfile               # Docker 镜像
├── README.md
└── ONBOARDING.md            # 你正在看这个
```

---

## 3. 30 分钟改一个页面（练习）

任务：给 `views/dashboard/Dashboard.vue` 加一个"🤖 AI 解读"小链接。

### 3.1 改 Dashboard.vue
```vue
<template>
  <div class="page-container">
    <!-- 原 4 个统计卡 -->
    <el-row :gutter="16" class="stats-row">...</el-row>

    <!-- 新增：AI 解读链接 -->
    <div style="text-align:right;margin-bottom:12px;">
      <el-link type="primary" @click="askAI">
        ✦ AI 解读本月数据 →
      </el-link>
    </div>

    <!-- 原 6 个模块入口 -->
    <el-row :gutter="16" class="modules-row">...</el-row>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()

function askAI() {
  router.push('/ai/extract?from=dashboard&question=本月数据')
}
</script>
```

### 3.2 跑测试
```bash
npm run dev
# 浏览器打开 http://localhost:5173/dashboard
# 看到 "✦ AI 解读本月数据 →" 链接
# 点击会跳到 /ai/extract 页
```

搞定。

---

## 4. 60 分钟创建一个新页面

新页面：`/ai/feedback`（AI 反馈中心）

```bash
# 1. 创建 .vue 文件
touch src/views/ai/AiFeedback.vue
```

```vue
<template>
  <div class="page-container">
    <h2>AI 反馈中心</h2>

    <el-table :data="feedbacks" v-loading="loading">
      <el-table-column prop="createdAt" label="时间" width="160" />
      <el-table-column prop="targetType" label="类型" width="100" />
      <el-table-column prop="rating" label="评价" width="80">
        <template #default="{ row }">
          <span :class="row.rating === 'up' ? 'text-success' : 'text-danger'">
            {{ row.rating === 'up' ? '👍' : '👎' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="comment" label="反馈内容" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { aiApi } from '@/api/ai'
import { ElMessage } from 'element-plus'

const feedbacks = ref<any[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    // 复用 aiApi.feedback 的反向（用 list 接口，Phase 1 可选）
    feedbacks.value = []
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
```

```typescript
// 2. 加路由 src/router/index.ts
{
  path: '/ai/feedback',
  name: 'AiFeedback',
  component: () => import('@/views/ai/AiFeedback.vue'),
  meta: { title: 'AI 反馈' },
}
```

```bash
# 3. 跑测试
npm run dev
# 浏览器打开 http://localhost:5173/ai/feedback
```

---

## 5. AI 触点开发（**最常做的事**）

### 5.1 触点开发的 5 步标准流程

每个 AI 触点（22 个）都按这个流程开发：

```
① 读 FRONTEND-AI-INTEGRATION.md 对应章节
② 用 @/utils/sse 或 aiApi
③ 引入 @/assets/styles/ai.scss 的 .ai-* 类
④ 错误码 5101-5104 → catch 降级
⑤ 移动端 < 640px 适配
```

### 5.2 通用 AI 组件

```vue
<!-- 在 src/components/ai/ 下创建通用组件 -->
<template>
  <span :class="['ai-confidence', level]">
    {{ value }}{{ suffix }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  value: number
  suffix?: string
}>(), { suffix: '%' })

const level = computed(() =>
  props.value >= 90 ? 'high' : props.value >= 70 ? 'mid' : 'low'
)
</script>
```

**用法**：
```vue
<AiConfidence :value="row.confidence" />
<!-- 输出: <span class="ai-confidence high">99%</span> -->
```

### 5.3 SSE 长任务的标准模式

```typescript
import { watchTask } from '@/utils/sse'
import { onUnmounted, ref } from 'vue'

const progress = ref(0)
const doneCount = ref(0)
const totalCount = ref(0)
let closeSSE: (() => void) | null = null

async function startTask(fileIds: string[]) {
  const { taskId } = await aiApi.extractInvoice({ fileId: fileIds[0], fileName: 'batch' })
  closeSSE?.()  // 清理上一个订阅
  closeSSE = watchTask(taskId, {
    onProgress: (p) => {
      progress.value = p.percent
      doneCount.value = p.done
      totalCount.value = p.total
    },
    onItem: (item) => { /* 追加单条结果 */ },
    onCompleted: (summary) => { ElMessage.success('完成') },
    onError: (e) => { ElMessage.error('失败') },
  })
}

onUnmounted(() => closeSSE?.())  // 组件卸载时关闭
```

---

## 6. 必须知道的"坑"

| 坑 | 现象 | 怎么避免 |
|------|------|---------|
| **路径单数/复数** | 之前 `modules.ts` 用了 `/projects/`，已统一改为 `/project/` | 写新模块 API 用**单数**（与 `design/API.md` 一致） |
| **SSE 不能传 header** | token 必须走 query string | 用 `sse.connect(path, handlers)` 自动处理 |
| **AI 调用失败要降级** | 5001/5101-5104 → 隐藏 AI 入口 | 任何 aiApi 调用都包 try/catch |
| **响应格式有两种** | 单对象（登录）vs 包装（列表） | `request.ts` 已处理，调用方不用管 |
| **金额单位** | API 返回元（Decimal），前端不要 ×100 | 直接展示 `¥ 1,234.56` |
| **状态码 + ElMessage** | 1001/2001/2002 会被自动弹错误 | 业务层不用再 `try/catch` |
| **EP 主题色覆盖** | 用 `$el-color-primary: $color-primary;` | 改 variables.scss 即可全 EP 同步 |
| **移动端 < 640px** | 侧栏变抽屉 + AI 提醒条垂直排列 | 样式已写在 ai.scss 末尾 |
| **AI 4 个列表字段** | `aiRiskLevel` / `aiSummary` / `aiTags` / `aiHealthScore` | 后端 Project/Contract 已有，前端直接展示 |
| **SSE 重连上限** | 5 次后报错 | 默认 3000ms 重连，可配 |

---

## 7. 常用命令速查

```bash
# 开发
npm run dev           # 启动 dev server
npm run type-check    # TS 类型检查（不编译）

# 构建
npm run build         # 生产构建（输出 dist/）
npm run preview       # 本地预览 dist/

# 代码质量
# （项目未配 ESLint，按团队规范走）

# 调试
# 在 .vue 里加：
console.log('[debug]', xxx)
// 或用 Vue Devtools
```

---

## 8. 与其他团队协作

| 团队 | 找谁 | 沟通什么 |
|------|------|---------|
| **后端** | 找后端 leader | API 字段不一致时（看 `FRONTEND-API-CONTRACT.md`） |
| **PM** | 找产品经理 | 需求变更、字段命名、状态流转 |
| **设计** | 看 `design/*.html` | 视觉细节、交互流程（设计稿 1:1 已在 .vue 中） |
| **AI 算法** | 找算法工程师 | AI 字段含义、置信度阈值、模型版本 |
| **QA** | 找测试 | 测试用例、bug 反馈 |

---

## 9. 上线前自检

新页面/触点上线前必须：

- [ ] TypeScript 编译通过（`npm run type-check`）
- [ ] `npm run build` 通过
- [ ] AI 失败时降级（5101-5104 → 隐藏入口）
- [ ] SSE 组件卸载时关闭
- [ ] 移动端 < 640px 样式不崩
- [ ] 反馈按钮调 `/ai/feedback/submit`（数据回流）
- [ ] 顶栏 ⌘K 能唤起全局问数
- [ ] 权限按 `useUserStore().hasPerm('xx:yy')` 校验

---

## 10. 找谁问问题

- **架构问题 / 整体设计** → 看 `FRONTEND-API-CONTRACT.md` + `README.md`
- **AI 接口字段** → 看 `../design/AI-API.md`
- **样式问题** → 看 `src/assets/styles/variables.scss`（设计 token）
- **AI 样式** → 看 `src/assets/styles/ai.scss`（14 类）
- **API 调用问题** → 看 `src/utils/request.ts`（拦截器 + 错误码）
- **SSE 问题** → 看 `src/utils/sse.ts`（已封装）

**不要在群里问"这个字段是什么意思"**——文档都有。找不到再问，**问的时候带具体文档名 + 链接**。

---

## 11. 开发期 vs 生产期

| 配置 | 开发 | 生产 |
|------|------|------|
| `npm run dev` | 启 dev server，HMR 热更新 | — |
| `npm run build` | — | 输出 `dist/` |
| VITE_API_BASE | `/api/v1`（用 Vite 代理） | `/api/v1`（用 nginx 代理） |
| 后端地址 | `http://localhost:8000` | `http://backend:8000`（docker compose） |
| 调试 | `console.log` + Vue Devtools | 关闭 `console.log` |
| Sourcemap | 启用 | 可关闭（减小体积） |

---

**第 1 周结束，你应该能交付：**
- ✅ 完整跑通项目（`npm run dev`）
- ✅ 完成 1-2 个 AI 触点（基于 `FRONTEND-AI-INTEGRATION.md`）
- ✅ 理解前后端契约（基于 `FRONTEND-API-CONTRACT.md`）
- ✅ 创建 1-2 个通用 AI 组件

**第 2-3 周**：完成 5 个 P0 + 8 个 P1 触点（共 13 个）

**第 4 周**：联调 + bug 修复

---

最后一句话：**遇到问题先查文档，文档没写才问。** 这套文档覆盖 90% 的常见问题。
