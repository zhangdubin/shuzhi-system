# AI 数智化能力 · 前端集成清单（22 触点）

> **目的**：把"AI 能力"映射到 `frontend/src/` 下的具体 .vue 文件，**前端工程师照单实现**
> **配套**：`FRONTEND-API-CONTRACT.md` / `design/AI-API.md` / `design/ai-*.html`
> **样式源**：`frontend/src/assets/styles/ai.scss`（已引入）
> **状态/Pinia**：`frontend/src/stores/ai.ts`（已引入）
> **SSE 客户端**：`frontend/src/utils/sse.ts`（已引入）

---

## 0. 通用约定

### 0.1 用得到的工具

```typescript
// 1. AI 状态（Pinia）
import { useAiStore } from '@/stores/ai'
const aiStore = useAiStore()

// 2. SSE 订阅
import { sse, watchTask } from '@/utils/sse'

// 3. AI API
import { aiApi } from '@/api/ai'
```

### 0.2 用得到的样式类

| 类名 | 用途 |
|------|------|
| `.ai-badge` | AI 角标（紫渐变小标签） |
| `.ai-card` `.ai-card.elevated` | AI 专属卡片（带左侧紫条） |
| `.ai-suggestion` | AI 建议项（紫色/黄/红变体） |
| `.ai-confidence` `.high/.mid/.low` | 置信度 chip |
| `.ai-risk-chip` `.high/.medium/.low` | 风险评级 chip |
| `.ai-tag` `.danger/.warning/.success` | 智能标签 |
| `.ai-loading` | AI 加载态（紫旋转圈） |
| `.ai-thinking-dots` | AI 思考动画（3 个跳点） |
| `.ai-task-progress` | AI 任务进度条 |
| `.ai-alert-bar` | Dashboard 顶部提醒条 |
| `.ai-summary` | 智能摘要块 |
| `.ai-timeline` | AI 事件时间线 |
| `.ai-citation` | 引用链接 |
| `.ai-feedback` | 👍👎 反馈组 |

### 0.3 通用模式：AI 降级

```typescript
// 任何 AI 调用都包 try/catch，5001/5101-5104 → 隐藏 AI 入口
try {
  const res = await aiApi.feedback(...)
} catch (e: any) {
  if ([5001, 5101, 5102, 5103, 5104].includes(e.code)) {
    // AI 不可用，隐藏该处 AI 入口
    showAi.value = false
  }
}
```

---

## 1. 5 个 P0 触点（MVP 1 周必出）

### 1.1 触点 #1：发票识别主页 · 一键 AI 抽取

**文件**：`src/views/invoice/InvoiceOcr.vue`

**位置**：上传区下方

**新增**：
```vue
<template>
  <!-- 原上传区保留 -->
  <el-upload>...</el-upload>

  <!-- 新增：AI 抽取结果区 -->
  <el-card v-if="aiResult" class="ai-card elevated" style="margin-top:16px;">
    <div class="ai-card-head">
      <h4>
        <span class="ai-badge">AI 抽取结果</span>
        <span>用时 {{ aiResult.meta.durationMs }}ms · 准确度 {{ aiResult.meta.confidence }}</span>
      </h4>
      <el-button text @click="aiResult = null">重新上传</el-button>
    </div>
    <div class="ai-card-body">
      <el-form :model="form" label-width="100px">
        <el-form-item label="发票号">
          <el-input v-model="form.invoiceNo" class="ai-extracted">
            <template #suffix>
              <span class="ai-extracted-tooltip">AI <span class="ai-conf-mini">{{ confidenceOf('invoiceNo') }}</span></span>
            </template>
          </el-input>
        </el-form-item>
        <!-- ... 其他字段同款结构 ... -->
      </el-form>

      <!-- 智能关联建议 -->
      <div v-if="aiResult.suggestions?.linkToContract" class="ai-suggestion success">
        <div class="ai-s-icon">🔗</div>
        <div class="ai-s-body">
          <div class="ai-s-title">智能关联建议</div>
          <div class="ai-s-desc">检测到备注"合同号 {{ aiResult.suggestions.linkToContract }}"</div>
          <div class="ai-s-actions">
            <el-button type="primary" size="small" @click="linkContract">采纳关联</el-button>
            <el-button size="small" @click="manualSelect">手动选择</el-button>
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { aiApi } from '@/api/ai'
import { ElMessage } from 'element-plus'
import { ElNotification } from 'element-plus'

const aiResult = ref<any>(null)
const form = ref<any>({})

async function extractWithAI(fileUrl: string, fileId: string) {
  try {
    const res = await aiApi.extractInvoice({ fileId, fileName: fileUrl.split('/').pop()! })
    aiResult.value = res.result
    // 把字段填到表单
    form.value = { ...form.value, ...res.result.fields }
  } catch (e: any) {
    if (e.code === 5102) {
      ElMessage.warning('AI 抽取超时，请稍后重试')
    } else if (e.code >= 5100) {
      ElMessage.warning('AI 服务暂不可用，已切换到手动录入')
    } else {
      throw e
    }
  }
}

function confidenceOf(field: string): number {
  return aiResult.value?.fields?.[field]?.confidence ?? 0
}
</script>
```

**接的接口**：`POST /ai/extract/upload`（同步）→ 如果改成异步任务，调用 `watchTask(taskId, { onItem, onCompleted })`

---

### 1.2 触点 #2：发票识别 · 批量上传 · AI 抽取开关

**文件**：`src/views/invoice/InvoiceOcr.vue`（或 `views/invoice/InvoiceBatch.vue`，如已有）

**位置**：进度条区域

**新增**：
```vue
<template>
  <el-card>
    <div class="batch-header">
      <h3>批量识别</h3>
      <el-switch v-model="aiEnabled" active-text="✦ AI 智能抽取" />
    </div>

    <!-- 进度条（保留老的） -->
    <el-progress :percentage="progress" :status="progressStatus" />
    <div class="progress-stage">{{ stage }} · {{ doneCount }} / {{ totalCount }}</div>

    <!-- 单条结果实时追加 -->
    <el-table :data="items" v-loading="loading">
      <el-table-column label="文件名" prop="fileName" />
      <el-table-column label="发票号" prop="invoiceNo" />
      <el-table-column label="AI 置信度" width="120">
        <template #default="{ row }">
          <span v-if="row.confidence !== undefined"
                :class="['ai-confidence', row.confidence >= 90 ? 'high' : row.confidence >= 70 ? 'mid' : 'low']">
            {{ row.confidence }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column label="状态">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'done'" type="success">完成</el-tag>
          <el-tag v-else-if="row.status === 'review'" type="warning">需复核</el-tag>
          <el-tag v-else-if="row.status === 'failed'" type="danger">失败</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { aiApi } from '@/api/ai'
import { watchTask } from '@/utils/sse'

const aiEnabled = ref(true)
const progress = ref(0)
const stage = ref('准备中')
const doneCount = ref(0)
const totalCount = ref(0)
const items = ref<any[]>([])
const loading = ref(false)
let closeSSE: (() => void) | null = null

async function startBatchExtract(fileIds: string[]) {
  loading.value = true
  try {
    // 1. 创建批量任务
    const { taskId } = await aiApi.extractInvoice({
      fileId: fileIds[0],  // 实际 API 应该是 batch
      fileName: 'batch'
    })

    // 2. 订阅 SSE
    closeSSE?.()
    closeSSE = watchTask(taskId, {
      onProgress: (p) => {
        progress.value = p.percent
        doneCount.value = p.done
        totalCount.value = p.total
        stage.value = p.stage || '识别中'
      },
      onItem: (item) => {
        items.value.push(item)
      },
      onCompleted: (summary) => {
        ElMessage.success(`批量识别完成 · ${summary.success}/${summary.total}`)
        loading.value = false
      },
      onError: (e) => {
        ElMessage.error('识别失败')
        loading.value = false
      },
    })
  } catch (e) {
    loading.value = false
    throw e
  }
}

onUnmounted(() => closeSSE?.())
</script>
```

**接的接口**：`POST /ai/extract/batch/upload` + `GET /ai/extract/batch/stream` (SSE)

---

### 1.3 触点 #3：项目列表 · AI 风险评级列

**文件**：`src/views/project/ProjectList.vue`

**位置**：`<el-table>` 加一列

**新增**：
```vue
<el-table :data="projects">
  <!-- 原列保留 -->
  <el-table-column prop="name" label="项目名" />
  <el-table-column prop="manager" label="负责人" />
  <el-table-column prop="amount" label="金额" />

  <!-- 新增：AI 风险评级 -->
  <el-table-column label="🤖 AI 风险" width="120">
    <template #default="{ row }">
      <span :class="['ai-risk-chip', row.aiRiskLevel || 'unknown']">
        <span class="dot"></span>
        {{ riskLabel(row.aiRiskLevel) }}
      </span>
    </template>
  </el-table-column>

  <!-- 新增：AI 摘要 -->
  <el-table-column label="🤖 AI 摘要" min-width="200">
    <template #default="{ row }">
      <div v-if="row.aiSummary" class="ai-summary" style="font-size:11.5px;padding:6px 10px;">
        {{ row.aiSummary }}
      </div>
    </template>
  </el-table-column>
</el-table>

<script setup lang="ts">
function riskLabel(level: string) {
  return { high: '高风险', medium: '中风险', low: '低风险', unknown: '未评估' }[level] || '未评估'
}
</script>
```

**接的接口**：
- 后端在 `project/list` 响应里加 `aiRiskLevel` / `aiSummary` 字段（无 AI 调用，前端直接展示）
- 如果后端没字段，前端可以另起一个批量 `/ai/risk/warnings?objectType=project&objectIds=...` 调用

---

### 1.4 触点 #4：项目详情 · 新增 ✨ AI 分析 Tab

**文件**：`src/views/project/ProjectDetail.vue`

**位置**：在 `<el-tabs>` 末尾追加一个 Tab

**新增**：
```vue
<el-tabs v-model="activeTab">
  <el-tab-pane label="基本信息" name="basic">...</el-tab-pane>
  <el-tab-pane label="里程碑" name="milestone">...</el-tab-pane>
  <el-tab-pane label="任务" name="task">...</el-tab-pane>
  <el-tab-pane label="文件" name="file">...</el-tab-pane>
  <el-tab-pane label="动态" name="activity">...</el-tab-pane>
  <el-tab-pane name="ai">
    <template #label>
      ✨ AI 分析
      <el-badge v-if="aiWarnCount > 0" :value="aiWarnCount" class="ai-badge" style="margin-left:4px;" />
    </template>
    <AiPanelProject :projectId="projectId" @warn-count="aiWarnCount = $event" />
  </el-tab-pane>
</el-tabs>
```

**新文件**：`src/components/AiPanelProject.vue`

**完整组件**：（参考 `design/ai-panel-project.html`）
- 健康度雷达图（5 维评分）
- 3 个风险预警
- 智能摘要
- 3 条 AI 建议
- 相似项目对比表
- AI 异常时间线
- 👍👎 反馈条

**接的接口**：`POST /ai/risk/scan` body: `{objectType: 'project', objectId: <id>}`

---

### 1.5 触点 #5：Dashboard · 今日 AI 提醒条

**文件**：`src/views/dashboard/Dashboard.vue`

**位置**：第一个统计卡之前

**新增**：
```vue
<template>
  <div class="dashboard">
    <!-- 顶部 AI 提醒条 -->
    <div v-if="aiStore.alerts.length > 0" class="ai-alert-bar">
      <div class="ai-icon">✦</div>
      <div class="ai-body">
        <div class="title">
          <span class="ai-badge">AI 提醒</span>
          <span>今日 <strong>{{ aiStore.unreadCount }}</strong> 条需要关注</span>
        </div>
        <div class="summary">
          <span v-for="a in aiStore.alerts.slice(0, 2)" :key="a.id" style="margin-right:14px;">
            <span :class="['ai-risk-chip', a.level]"><span class="dot"></span></span>
            {{ a.title }}
          </span>
        </div>
      </div>
      <div class="ai-actions">
        <el-button size="small" @click="goToAlerts">查看全部</el-button>
      </div>
    </div>

    <!-- 原有 4 个统计卡 + 6 个模块入口 -->
    ...
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAiStore } from '@/stores/ai'

const aiStore = useAiStore()
const router = useRouter()

onMounted(() => {
  aiStore.loadAlerts()
})

function goToAlerts() {
  router.push('/ai/alerts')
}
</script>
```

**接的接口**：`GET /ai/alert/today`

---

## 2. 8 个 P1 触点（第 2 周）

| # | 文件 | 新增 | 接的接口 |
|---|------|------|---------|
| **6** | `views/contract/ContractCreate.vue` | 表单顶部"✦ AI 一键起草"按钮 → 弹 Drawer | `POST /ai/generate/draft` |
| **7** | `views/contract/ContractList.vue` | 列表加 "AI 风险标签" 列 | 后端字段 / `POST /ai/risk/warnings` |
| **8** | `views/contract/ContractDetail.vue` | 顶栏右侧"AI 合同体检"按钮 → 唤起 `AiDrawer` | `POST /ai/risk/scan` |
| **9** | `views/receivable/ReceivableList.vue` | 筛选抽屉加 "AI 智能匹配" 区块 | `POST /ai/match/run` |
| **10** | `views/expense/ExpenseCreate.vue` | 顶部 "✦ AI 拍照识别" 按钮 | `POST /ai/extract/upload` (type: receipt) |
| **11** | `views/expense/ExpenseList.vue` | 审核流位置加 "AI 建议" 标签 | 后端字段 |
| **12** | `views/receivable/ReceivableCreate.vue` | "✦ AI 智能提醒日期" 建议 | `POST /ai/generate/draft` |
| **13** | `views/invoice/InvoiceTemplateEdit.vue` | 字段配置加 "AI 自动识别此字段" 开关 | `POST /ai/extract/upload` |

---

## 3. 9 个 P2 触点（第 3 周）

| # | 文件 | 新增 | 接的接口 |
|---|------|------|---------|
| **14** | `layouts/AppLayout.vue` | 顶栏搜索框旁加 🤖 按钮 → 全局命令面板 | `POST /ai/ask/ask` (流式 SSE) |
| **15** | `views/dashboard/Dashboard.vue` | 数据卡旁 "AI 解读" 小链接 | `POST /ai/ask/ask` |
| **16** | `views/dashboard/Dashboard.vue` | 快速新建按钮旁 "✦ AI 建议" | `GET /ai/alert/today` |
| **17** | `views/auth/Login.vue` | 登录按钮旁 "🤖 智能问数" 入口 | `POST /ai/ask/ask` (无 token) |
| **18** | 4 个 `*Detail.vue` | 右上角"操作"下拉加 "AI 分析" | 同 #4 |
| **19** | `views/invoice/InvoiceDetail.vue` | 票面右上 "🤖 AI 复核" | `POST /ai/risk/scan` |
| **20** | `views/client/ClientCreate.vue` | "AI 自动识别名片" 按钮 | `POST /ai/extract/upload` (type: business-card) |
| **21** | `views/error/Error500.vue` | 文案 "AI 助手已记录..." | `POST /ai/feedback/submit` |
| **22** | 5 个 `*List.vue` | 工具栏 "🤖 AI 智能筛选" 按钮 | 复用列表接口 + `ai:tags` 字段 |

---

## 4. 通用组件提取（**做一次，多处用**）

> 避免每个页面重复写 AI 组件，**抽到 `src/components/ai/` 下**。

### 4.1 建议组件清单

```
src/components/ai/
├── AiBadge.vue              # AI 角标
├── AiConfidence.vue         # 置信度（自动判断 high/mid/low）
├── AiRiskChip.vue           # 风险评级 chip
├── AiTag.vue                # 智能标签
├── AiSuggestion.vue         # 建议项（普通/警告/危险变体）
├── AiWarning.vue            # 风险预警（带采纳/忽略按钮）
├── AiTaskProgress.vue       # 任务进度条
├── AiSkeleton.vue           # 骨架屏
├── AiFeedback.vue           # 👍👎 反馈组
├── AiAlertBar.vue           # 提醒条（Dashboard 顶部）
├── AiSummary.vue            # 智能摘要块
├── AiCitation.vue           # 引用链接
├── AiTimeline.vue           # 时间线
├── AiHealthRadar.vue        # 5 维健康度雷达图（ECharts）
├── AiDrawer.vue             # AI 抽屉（合同/项目详情唤起）
├── AiPanelProject.vue       # 项目 AI 分析面板（详情页用）
└── AiPanelContract.vue      # 合同 AI 体检面板（详情页用）
```

### 4.2 组件示例：`AiConfidence.vue`

```vue
<template>
  <span :class="['ai-confidence', level]">
    {{ value }}{{ suffix }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  value: number        // 0-100
  suffix?: string      // 默认 '%'
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

---

## 5. 路由新增（**AI 独立页面**）

```typescript
// src/router/index.ts 已实现（如未实现，参考以下）
const aiRoutes = [
  { path: '/ai/extract',       component: () => import('@/views/ai/AiExtract.vue') },
  { path: '/ai/tasks',         component: () => import('@/views/ai/AiTasks.vue') },
  { path: '/ai/alerts',        component: () => import('@/views/ai/AiAlerts.vue') },
  { path: '/ai/panel/project', component: () => import('@/views/ai/AiPanelProject.vue') },
  { path: '/ai/panel/contract',component: () => import('@/views/ai/AiPanelContract.vue') },
]
```

---

## 6. 侧栏菜单新增

```typescript
// src/config/menu.ts
{
  group: '数智（AI）',
  icon: '✦',
  items: [
    { path: '/ai/extract', label: 'AI 抽取', icon: '📷' },
    { path: '/ai/tasks',   label: '任务中心', icon: '⚡' },
    { path: '/ai/alerts',  label: '智能预警', icon: '🔔' },
  ],
}
```

---

## 7. 全局命令面板（触点 #14）

**新文件**：`src/components/GlobalAskDialog.vue`

```vue
<template>
  <el-dialog v-model="visible" width="640px" :show-close="false" top="10vh" align-center>
    <template #header>
      <div class="ask-header">
        <span class="ai-badge">✦</span>
        <span style="font-size:16px;font-weight:600;">问点什么？</span>
      </div>
    </template>
    <el-input
      v-model="question"
      type="textarea"
      :rows="3"
      placeholder="试试：'本月回款逾期了哪些？'"
      @keydown.ctrl.enter="ask"
    />
    <div class="ask-suggestions">
      <el-tag v-for="s in suggestions" :key="s" effect="plain" @click="question = s; ask()">
        {{ s }}
      </el-tag>
    </div>
    <div v-if="answer" class="ask-answer">
      <div v-html="answer"></div>
      <div v-if="sources.length" class="ask-sources">
        <span class="text-tertiary">引用：</span>
        <a v-for="src in sources" :key="src.id" class="ai-citation" :href="src.url">
          {{ src.title }}
        </a>
      </div>
      <div class="ai-feedback">
        <button :class="{ 'up active': feedback === 'up' }" @click="feedback = 'up'">👍</button>
        <button :class="{ 'down active': feedback === 'down' }" @click="feedback = 'down'">👎</button>
      </div>
    </div>
    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="primary" :loading="loading" @click="ask">提问 (⌘↵)</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { aiApi } from '@/api/ai'
import { ElMessage } from 'element-plus'

const visible = ref(false)
const question = ref('')
const answer = ref('')
const sources = ref<any[]>([])
const loading = ref(false)
const feedback = ref<'up' | 'down' | null>(null)

const suggestions = [
  '💰 本月回款逾期',
  '⚠️ 风险项目',
  '📊 上周销售费用',
  '🔄 待回款客户',
]

async function ask() {
  if (!question.value.trim()) return
  loading.value = true
  answer.value = ''
  sources.value = []
  feedback.value = null
  try {
    const res = await aiApi.ask({
      question: question.value,
      stream: false,
    })
    answer.value = res.answer
    sources.value = res.sources || []
  } catch (e: any) {
    if (e.code >= 5100) {
      ElMessage.warning('AI 服务暂不可用')
    } else {
      ElMessage.error('提问失败')
    }
  } finally {
    loading.value = false
  }
}

// 快捷键 ⌘K 唤起
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      visible.value = !visible.value
    }
  })
}
</script>
```

**接的接口**：`POST /ai/ask/ask`

---

## 8. 迁移 checklist（前端工程师参考）

### Phase 1（MVP 1 周）
- [ ] `src/utils/sse.ts` 已引入（**已就绪**）
- [ ] `src/stores/ai.ts` 已引入（**已就绪**）
- [ ] `src/assets/styles/ai.scss` 已引入（**已就绪**）
- [ ] 触点 #1（发票 AI 抽取）
- [ ] 触点 #2（批量 AI 抽取）
- [ ] 触点 #3（项目列表 AI 列）
- [ ] 触点 #4（项目详情 AI Tab）
- [ ] 触点 #5（Dashboard 提醒条）
- [ ] 创建 `src/components/ai/` 目录 + 5 个基础组件（Badge / Confidence / RiskChip / Suggestion / Warning）

### Phase 2（第 2 周）
- [ ] 触点 #6-#13（合同/费用/回款/客户/模板的 AI 入口）
- [ ] 创建 `AiPanelContract.vue` / `AiDrawer.vue`
- [ ] 创建 `AiHealthRadar.vue`（ECharts 雷达图）

### Phase 3（第 3 周）
- [ ] 触点 #14（全局命令面板 `GlobalAskDialog.vue`）
- [ ] 触点 #15-#22（Dashboard 解读、登录入口、错误页等）
- [ ] 侧栏菜单加 "数智（AI）" 分组
- [ ] 路由表加 5 个 AI 独立页

---

## 9. 验证清单（每个触点实现后必测）

- [ ] AI 调用失败时（5101-5104）→ 隐藏 AI 入口，业务流程不卡
- [ ] SSE 断线时 → 3 秒后自动重连，最多 5 次
- [ ] AI 置信度色阶正确（≥90 绿 / 70-89 黄 / <70 红）
- [ ] 采纳/忽略按钮反馈到后端 `/ai/feedback/submit`
- [ ] 移动端（< 640px）样式不崩（AI 提醒条垂直排列）
- [ ] 顶栏 🤖 按钮 + ⌘K 快捷键都能唤起全局问数

---

## 10. 完成度跟踪

| 触点 | 优先级 | 状态 | 实现人 | PR |
|------|--------|------|--------|-----|
| #1 发票 AI 抽取 | P0 | ⬜ | | |
| #2 批量 AI 抽取 | P0 | ⬜ | | |
| #3 项目列表 AI 列 | P0 | ⬜ | | |
| #4 项目 AI 分析 Tab | P0 | ⬜ | | |
| #5 Dashboard AI 提醒 | P0 | ⬜ | | |
| #6 合同 AI 起草 | P1 | ⬜ | | |
| ... | ... | ... | | |
| #22 列表 AI 筛选 | P2 | ⬜ | | |

**当前进度**：0/22。**目标**：1 周内完成 5 个 P0。
