# AiRiskScanPanel · 使用指南

> **位置**：`src/components/ai/AiRiskScanPanel.vue`
> **类型**：`src/components/ai/types.ts`
> **Mock**：`src/components/ai/mock.ts`
> **依赖**：`aiApi`（已扩展） + `ai.scss`（已引入） + Element Plus

---

## 1. 5 分钟上手

### 1.1 在合同详情页用

```vue
<!-- src/views/contract/ContractDetail.vue -->
<template>
  <div class="page-container">
    <h1>合同详情 · {{ contract.code }}</h1>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="基本信息" name="basic">...</el-tab-pane>
      <el-tab-pane label="合同条款" name="clause">...</el-tab-pane>

      <!-- ✨ AI 体检 Tab（新增） -->
      <el-tab-pane name="ai">
        <template #label>
          ✨ AI 体检
          <el-badge
            v-if="aiWarnCount > 0"
            :value="aiWarnCount"
            style="margin-left:6px;"
          />
        </template>
        <AiRiskScanPanel
          object-type="contract"
          :object-id="contract.id"
          @loaded="onAiLoaded"
          @accept-suggestion="onAcceptSuggestion"
          @dismiss-warning="onDismissWarning"
          @feedback="onFeedback"
          @error="onAiError"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiRiskScanPanel from '@/components/ai/AiRiskScanPanel.vue'
import type { AiScanResult, AiSuggestion, AiWarning } from '@/components/ai/types'

const router = useRouter()
const contract = ref({ id: 123, code: 'HT-2026-031', /* ... */ })
const activeTab = ref('basic')
const aiWarnCount = ref(0)

function onAiLoaded(result: AiScanResult) {
  aiWarnCount.value = result.warnings.length
}

async function onAcceptSuggestion(s: AiSuggestion) {
  // 业务侧：跳到"编辑合同"页，把建议带入
  ElMessage.success(`已采纳：${s.title}`)
  // 可选：router.push(`/contract/${contract.value.id}/edit?suggestion=${s.id}`)
}

function onDismissWarning(w: AiWarning) {
  ElMessage.info(`已忽略：${w.title}`)
}

function onFeedback(payload: { rating: 'up' | 'down' }) {
  // 已通过组件内置的 aiApi.feedbackSubmit 上报
  console.log('[feedback]', payload)
}

function onAiError(err: Error) {
  ElMessage.error(`AI 体检失败：${err.message}`)
}
</script>
```

### 1.2 在项目详情页用（**几乎一样**）

```vue
<AiRiskScanPanel
  object-type="project"
  :object-id="project.id"
/>
```

### 1.3 在费用详情页用

```vue
<AiRiskScanPanel
  object-type="expense"
  :object-id="expense.id"
/>
```

**就这一行**。组件会根据 `objectType` 自动调整显示。

---

## 2. Props

```typescript
interface AiRiskScanPanelProps {
  /** 要扫描的对象类型（必填） */
  objectType: 'project' | 'contract' | 'expense' | 'voucher'

  /** 要扫描的对象 ID（必填） */
  objectId: number

  /** 是否自动加载（默认 true） */
  autoLoad?: boolean

  /** 相似对象数（默认 3） */
  similarLimit?: number

  /** 深度扫描（慢但准） */
  deepScan?: boolean
}
```

---

## 3. Emits

```typescript
interface AiRiskScanPanelEmits {
  /** 扫描完成 */
  (e: 'loaded', result: AiScanResult): void

  /** 扫描失败（非降级） */
  (e: 'error', err: Error): void

  /** 用户采纳了某条建议 */
  (e: 'accept-suggestion', suggestion: AiSuggestion): void

  /** 用户忽略了某条风险 */
  (e: 'dismiss-warning', warning: AiWarning): void

  /** 反馈（👍/👎） */
  (e: 'feedback', payload: { rating: 'up' | 'down'; comment?: string }): void
}
```

**降级（AI 不可用）时不发 `error`**，而是把内部 state 置为 `degraded` 并展示 alert，业务方**不需要处理**。

---

## 4. 暴露的方法（defineExpose）

通过 `ref` 可以调用：

```vue
<template>
  <AiRiskScanPanel ref="aiPanel" object-type="contract" :object-id="id" />
  <el-button @click="refresh">🔄 重新扫描</el-button>
</template>

<script setup lang="ts">
const aiPanel = ref()

function refresh() {
  aiPanel.value?.reload()  // 强制重新扫描
}

// 拿当前结果
function getResult() {
  return aiPanel.value?.result()
}
</script>
```

---

## 5. 11 个区块对照

| # | 区块 | 来自 | 错误时 |
|---|------|------|-------|
| 1 | Loading 骨架 | state='loading' | 灰底骨架 4 块 |
| 2 | Error + 重试 | state='error' | 友好空状态 + 重试按钮 + 降级链接 |
| 3 | 降级提示 | state='degraded' | ElAlert 警告（AI 不可用） |
| 4 | 综合评分 + 智能摘要 | result.overallScore + summaryText 计算属性 | 隐藏 |
| 5 | 5 维健康度 | result.dimensions | 空数据不显示 |
| 6 | 风险预警 | result.warnings | 空显示 el-empty |
| 7 | AI 智能建议 | result.suggestions | 空显示 el-empty |
| 8 | 采纳回执条 | acceptReceipts 数组 | 数组为空不显示 |
| 9 | 相似对象对比表 | result.similarObjects | 空不显示 |
| 10 | AI 异常时间线 | result.timeline | 空不显示 |
| 11 | 反馈条 | feedback 状态 | 总显示 |

---

## 6. 完整工程模式（**这是这个组件的最大价值**）

### 6.1 四态管理（state machine）

```
        ┌─────────────┐
        │  loading    │ ← 进入组件 / autoLoad=true
        └──────┬──────┘
               ↓ load()
        ┌─────────────┐
        │  success    │ ← API 200 + 正常数据
        └──────┬──────┘
               ↓ 出错
        ┌─────────────┐
        │  error      │ ← HTTP 500 / 业务 4xxx
        └──────┬──────┘
               ↓ 用户点重试
               ↓
        ┌─────────────┐
        │  loading    │ (回到 loading)
        └─────────────┘

  任何状态下都可能跳到：
        ┌─────────────┐
        │  degraded   │ ← AI 错误码 5001/5101-5104
        └─────────────┘
        （不阻塞，用户可继续用普通流程）
```

### 6.2 降级策略（**关键**）

```typescript
// src/api/ai.ts 已定义
const aiDegradeCodes = [5001, 5101, 5102, 5103, 5104]
if (aiDegradeCodes.includes(e?.code)) {
  state.value = 'degraded'  // 切到降级态
  // 业务侧 setFallback() 自动配老路径
}
```

**降级不抛错**——业务继续运转，AI 入口隐藏。

### 6.3 数据回流（采纳/忽略/反馈）

| 用户操作 | 调用的接口 | 用途 |
|---------|----------|------|
| 采纳建议 | `POST /ai/feedback/submit` (rating=up) | 模型学习："这条建议有用" |
| 忽略风险 | `POST /ai/risk/dismiss` (action=dismiss) | 标记该风险已处理，下次不展示 |
| 👍 | `POST /ai/feedback/submit` (rating=up) | "这次扫描有用" |
| 👎 | `POST /ai/feedback/submit` (rating=down) | "这次扫描没用" |

**所有 AI 输出都有反馈路径**——数据回流是模型迭代的基础。

### 6.4 TypeScript 严格模式

- 所有 Props / Emits 用 `withDefaults` + `defineEmits<...>()` 强类型
- 业务对象用 `interface` 显式定义（`AiScanResult` / `AiWarning` 等）
- 不使用 `any`，所有字段类型明确
- 字段名错误会编译失败

### 6.5 容错 + 防御

- 任何字段缺失（如 `dimensions` 为 undefined）→ 模板用 `v-if` 隐藏对应区块
- 任何 API 失败 → 降级或错误态，**不抛白屏**
- 任何用户操作失败 → `ElMessage` 提示，**不静默**
- 任何异步操作 → `onUnmounted` 清理（虽然此组件无 setTimeout，但模式可复用）

### 6.6 移动端适配

```scss
@media (max-width: 768px) {
  .ai-overview { grid-template-columns: 1fr; }  // 双列 → 单列
  .ai-score-big { border-right: none; }         // 移除竖线
}
```

`< 768px` 自动切换布局，已在样式里。

---

## 7. Mock 调试（**前端独立可跑**）

后端没起时，前端也能看到完整效果：

```typescript
// src/api/ai.ts 临时改：
import { mockRiskScanResult } from '@/components/ai/mock'

// 临时替换
riskScan: async () => {
  await new Promise((r) => setTimeout(r, 800))  // 模拟网络延迟
  return mockRiskScanResult
}
```

刷新页面就能看到完整 UI，包括：
- 综合评分 72（中风险）
- 5 维评分（其中付款/法务是黄色）
- 3 个风险预警（2 高 1 中）
- 3 条建议
- 4 个相似对象对比（含本对象高亮）
- 5 个时间线事件

---

## 8. 复用到其他对象（3 步搞定）

### 8.1 项目详情页

```vue
<!-- 在 ProjectDetail.vue 的某个 tab 里 -->
<AiRiskScanPanel
  object-type="project"
  :object-id="project.id"
  @accept-suggestion="onProjectAiAccept"
/>
```

### 8.2 销售费用详情页

```vue
<AiRiskScanPanel
  object-type="expense"
  :object-id="expense.id"
/>
```

### 8.3 凭证详情页（Phase 2）

```vue
<AiRiskScanPanel
  object-type="voucher"
  :object-id="voucher.id"
/>
```

---

## 9. 自定义业务回调（高级）

### 9.1 采纳建议后跳到编辑页

```vue
<template>
  <AiRiskScanPanel
    object-type="contract"
    :object-id="contract.id"
    @accept-suggestion="goEdit"
  />
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()

function goEdit(s: AiSuggestion) {
  // 把建议 ID 带到编辑页
  router.push(`/contract/${contract.value.id}/edit?suggestion=${s.id}`)
}
</script>
```

### 9.2 关闭后自动跳转

```vue
<AiRiskScanPanel
  object-type="contract"
  :object-id="contract.id"
  @dismiss-warning="(w) => dismissed.push(w)"
/>

<script setup lang="ts">
import { watch } from 'vue'
import { useRouter } from 'vue-router'
const router = useRouter()
const dismissed = ref<string[]>([])

watch(dismissed, (list) => {
  if (list.length >= 3) {
    ElMessage.success('已忽略 3 条风险，跳转列表')
    router.push('/contract/list')
  }
})
</script>
```

---

## 10. 测试清单（接入后必测）

- [ ] 正常流程：扫描成功 → 11 个区块全部展示
- [ ] AI 不可用：模拟 5101 → 显示降级 alert
- [ ] 网络错误：模拟 500 → 显示重试按钮
- [ ] 采纳建议：回执条 + 列表移除 + 调 feedback
- [ ] 忽略风险：列表移除 + 调 risk/dismiss
- [ ] 反馈：👍 / 👎 切换 + 调 feedback
- [ ] props 变化：objectId 变化 → 重新扫描
- [ ] 移动端：< 768px 布局切换
- [ ] 暗色模式：color variable 全部用 CSS var

---

## 11. 不要做的事

- ❌ **不要修改 `aiApi.riskScan` 的接口签名**——它和后端契约绑定，改了就要前后端一起改
- ❌ **不要在父组件里 mock 整个 result**——会绕过 loading/error 状态机
- ❌ **不要把 component 放在 `<script setup>` 外**——Vue 3 setup 模式下无效
- ❌ **不要忘了 import `mock.ts`**——否则 dev 模式会因 API 未实现报 404

---

## 12. 相关文档

- `../design/AI-API.md` §6.2 风险扫描接口契约
- `../design/ai-panel-contract.html` 设计稿（视觉对照）
- `../FRONTEND-AI-INTEGRATION.md` 22 触点清单（本组件是 #4 / #8 / #18 / #19 的实现）
- `../FRONTEND-API-CONTRACT.md` 前后端契约对齐
