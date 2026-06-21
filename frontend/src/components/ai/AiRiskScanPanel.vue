<!--
  AiRiskScanPanel.vue
  ============================================================
  AI 风险扫描面板 · 工程级样板组件
  2026-05-21

  这是 22 触点中"详情页 AI Tab"的标准实现。
  业务价值：合同/项目/费用详情页 4 处复用。

  覆盖 11 个区块：
    1. Loading 骨架
    2. Error + 重试
    3. 降级提示（AI 不可用）
    4. 综合评分 + 智能摘要
    5. 5 维健康度
    6. 风险预警（3 个，按严重度排序）
    7. AI 智能建议（采纳/发草稿/发法务）
    8. 采纳回执条（"已采纳"反馈）
    9. 相似对象对比表
    10. AI 异常事件时间线
    11. 反馈条（👍👎）

  用法：
    <AiRiskScanPanel
      object-type="contract"
      :object-id="contract.id"
      @loaded="onLoaded"
      @accept-suggestion="onAcceptSuggestion"
      @dismiss-warning="onDismissWarning"
    />
-->
<template>
  <div class="ai-risk-scan-panel">
    <!-- ============ 1. Loading 骨架 ============ -->
    <template v-if="state === 'loading' && !result">
      <div class="ai-overview loading-skel">
        <div class="ai-score-big">
          <div class="ai-skeleton" style="width:80px;height:60px;margin:0 auto;"></div>
          <div class="ai-skeleton" style="width:60px;height:12px;margin:8px auto 0;"></div>
        </div>
        <div class="ai-summary-area">
          <div class="ai-skeleton" style="width:100px;height:14px;margin-bottom:12px;"></div>
          <div class="ai-skeleton" style="width:100%;height:12px;margin-bottom:6px;"></div>
          <div class="ai-skeleton" style="width:90%;height:12px;margin-bottom:6px;"></div>
          <div class="ai-skeleton" style="width:75%;height:12px;"></div>
        </div>
      </div>
      <el-card v-for="i in 3" :key="i" style="margin-bottom:16px;">
        <div class="ai-skeleton" style="width:40%;height:14px;margin-bottom:12px;"></div>
        <div class="ai-skeleton" style="width:100%;height:12px;margin-bottom:6px;"></div>
        <div class="ai-skeleton" style="width:80%;height:12px;"></div>
      </el-card>
    </template>

    <!-- ============ 2. Error + 重试 ============ -->
    <el-empty
      v-else-if="state === 'error'"
      :description="errorMsg"
      style="padding:60px 0;"
    >
      <el-button type="primary" @click="load(true)">🔄 重新扫描</el-button>
      <div style="margin-top:12px;font-size:12px;color:var(--color-text-tertiary);">
        如多次失败，可使用普通流程：<el-link type="primary" @click="goFallback">{{ fallbackLabel }}</el-link>
      </div>
    </el-empty>

    <!-- ============ 3. 降级提示（AI 不可用时） ============ -->
    <el-alert
      v-else-if="state === 'degraded' && !result"
      type="warning"
      :closable="false"
      show-icon
      title="AI 服务暂不可用"
      description="已切换到普通流程。所有数据均可正常查看，仅 AI 风险扫描功能暂不可用。"
      style="margin-bottom:16px;"
    />

    <!-- ============ 4. 正常结果 ============ -->
    <template v-else-if="result">
      <!-- 4. 综合评分 + 智能摘要 -->
      <div class="ai-overview">
        <div class="ai-score-big">
          <div class="num">{{ result.overallScore }}</div>
          <div class="label">综合健康分</div>
          <div :class="['risk-tag', result.riskLevel]">
            <span class="dot"></span>
            {{ riskLabel(result.riskLevel) }}
            <span v-if="warningCount > 0"> · {{ warningCount }} 风险</span>
          </div>
        </div>
        <div class="ai-summary-area">
          <div class="h">
            <span class="ai-badge" style="font-size:10.5px;">AI 摘要</span>
            <span>扫描耗时 {{ result.meta.durationMs }}ms · 准确度 {{ result.meta.confidence }}%</span>
          </div>
          <div class="text" v-html="summaryText"></div>
        </div>
      </div>

      <!-- 5. 5 维健康度 -->
      <el-card v-if="result.dimensions?.length" style="margin-bottom:16px;">
        <template #header>
          <div class="card-head-inline">
            <h4>5 维健康度</h4>
            <span class="text-tertiary" style="font-size:11px;">AI 评分 · 0-100</span>
          </div>
        </template>
        <div v-for="dim in result.dimensions" :key="dim.name" class="ai-dim-bar">
          <span class="name">{{ dim.name }}</span>
          <div class="bar">
            <div
              :class="['fill', dim.score < 70 ? 'warn' : '']"
              :style="{ width: dim.score + '%' }"
            ></div>
          </div>
          <span class="score">{{ dim.score }}</span>
        </div>
      </el-card>

      <!-- 6 + 7. 风险预警 + AI 建议（双栏） -->
      <el-row :gutter="16" style="margin-bottom:16px;">
        <!-- 左：风险预警 -->
        <el-col :xs="24" :md="12">
          <el-card>
            <template #header>
              <div class="card-head-inline">
                <h4>⚠️ 风险预警 <span class="ai-badge" :style="{background: 'var(--color-danger)', fontSize: '10px', padding: '2px 8px'}">{{ result.warnings.length }}</span></h4>
                <span class="text-tertiary" style="font-size:11px;">按严重度排序</span>
              </div>
            </template>
            <div
              v-for="w in result.warnings"
              :key="w.id"
              :class="['ai-warn', w.level === 'high' ? 'high' : w.level === 'low' ? 'info' : '']"
            >
              <div class="ico">{{ w.level === 'high' ? '!' : '⚠' }}</div>
              <div class="body">
                <div class="head">
                  <div class="title">{{ w.title }}</div>
                  <span :class="['ai-risk-chip', w.level]">
                    <span class="dot"></span>
                    {{ riskLabel(w.level) }}
                  </span>
                </div>
                <div class="desc">{{ w.description }}</div>
                <div v-if="w.suggestion" class="ai-suggestion-inline">
                  💡 <strong>AI 建议：</strong>{{ w.suggestion }}
                </div>
                <div class="actions">
                  <el-button
                    v-for="act in getWarningActions(w)"
                    :key="act.label"
                    :type="act.primary ? 'primary' : 'default'"
                    size="small"
                    @click="act.handler(w)"
                  >
                    {{ act.label }}
                  </el-button>
                  <el-button
                    size="small"
                    text
                    style="margin-left:auto;"
                    @click="onDismiss(w)"
                  >
                    忽略
                  </el-button>
                </div>
              </div>
            </div>
            <el-empty v-if="!result.warnings.length" description="暂无风险" :image-size="60" />
          </el-card>
        </el-col>

        <!-- 右：AI 建议 + 采纳回执 -->
        <el-col :xs="24" :md="12">
          <!-- 采纳回执条 -->
          <transition-group name="accept" tag="div">
            <div
              v-for="r in acceptReceipts"
              :key="r.id"
              class="ai-accept-bar"
            >
              <div class="ico">✓</div>
              <div>
                <strong>已采纳：</strong>{{ r.title }}
                <span v-if="r.assignee"> · 已发送至 <strong>{{ r.assignee }}</strong> 复核</span>
                <span class="undo" @click="undoAccept(r)">撤销</span>
              </div>
            </div>
          </transition-group>

          <el-card>
            <template #header>
              <div class="card-head-inline">
                <h4>💡 AI 给你的 {{ result.suggestions.length }} 条建议</h4>
                <span class="ai-confidence high" v-if="result.suggestions[0]">
                  置信度 {{ result.suggestions[0].confidence }}%
                </span>
              </div>
            </template>
            <div
              v-for="(s, i) in result.suggestions"
              :key="s.id"
              :class="['ai-suggestion', getSuggestionClass(i, s)]"
            >
              <div class="ai-s-icon">{{ i + 1 }}</div>
              <div class="ai-s-body">
                <div class="ai-s-title">{{ s.title }}</div>
                <div class="ai-s-desc" v-html="s.description"></div>
                <div class="ai-s-actions">
                  <el-button
                    type="primary"
                    size="small"
                    @click="onAcceptSuggestion(s)"
                  >
                    ✓ 采纳
                  </el-button>
                  <el-button
                    v-if="s.action?.type"
                    size="small"
                    @click="executeAction(s)"
                  >
                    {{ actionLabel(s.action.type) }}
                  </el-button>
                </div>
              </div>
            </div>
            <el-empty v-if="!result.suggestions.length" description="暂无建议" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>

      <!-- 8. 采纳回执条（保留外部 emit 触发） -->
      <!-- 已合并到 7 右侧 -->

      <!-- 9. 相似对象对比表 -->
      <el-card v-if="result.similarObjects?.length" style="margin-bottom:16px;">
        <template #header>
          <div class="card-head-inline">
            <h4>📊 相似对象参考</h4>
            <span class="text-tertiary" style="font-size:11px;">基于对象特征匹配 {{ result.similarObjects.length }} 个</span>
          </div>
        </template>
        <el-table :data="result.similarObjects" size="small">
          <el-table-column label="对象" min-width="180">
            <template #default="{ row }">
              <span :style="{ fontWeight: row.isCurrent ? 600 : 400, color: row.isCurrent ? 'var(--color-ai)' : 'inherit' }">
                {{ row.isCurrent ? '📌 ' : '' }}{{ row.name }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="健康分" width="100" align="right">
            <template #default="{ row }">
              <span :style="{ fontFamily: 'var(--font-family-mono)', color: getScoreColor(row.healthScore) }">
                {{ row.healthScore }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="延期天数" width="110" align="right">
            <template #default="{ row }">
              <span :style="{ fontFamily: 'var(--font-family-mono)', color: (row.delayDays ?? 0) > 0 ? 'var(--color-warning)' : 'var(--color-success)' }">
                {{ formatDelay(row.delayDays) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="超支率" width="100" align="right">
            <template #default="{ row }">
              <span :style="{ fontFamily: 'var(--font-family-mono)', color: (row.overBudget ?? 0) > 0 ? 'var(--color-warning)' : 'var(--color-success)' }">
                {{ formatPercent(row.overBudget) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 10. AI 异常事件时间线 -->
      <el-card v-if="result.timeline?.length" style="margin-bottom:16px;">
        <template #header>
          <div class="card-head-inline">
            <h4>📅 AI 异常事件时间线</h4>
            <span class="text-tertiary" style="font-size:11px;">最近 30 天</span>
          </div>
        </template>
        <div class="ai-timeline">
          <div v-for="(e, i) in result.timeline" :key="i" class="at-item">
            <div class="at-time">{{ e.time }}</div>
            <div class="at-text" v-html="e.text"></div>
          </div>
        </div>
      </el-card>

      <!-- 11. 反馈条 -->
      <div class="ai-feedback-bar">
        <span>这次 AI 体检对你有帮助吗？</span>
        <div style="display:flex;align-items:center;gap:10px;">
          <div class="ai-feedback">
            <button
              :class="{ up: true, active: feedback === 'up' }"
              title="有用"
              @click="onFeedback('up')"
            >👍</button>
            <button
              :class="{ down: true, active: feedback === 'down' }"
              title="没用"
              @click="onFeedback('down')"
            >👎</button>
          </div>
          <el-button text type="primary" size="small" @click="downloadReport">
            📥 完整报告
          </el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * AiRiskScanPanel.vue
 * AI 风险扫描面板 · 工程级样板
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { aiApi } from '@/api/ai'
import type {
  AiScanResult,
  AiWarning,
  AiSuggestion,
  AiRiskScanPanelProps,
  AiRiskScanPanelEmits,
  RiskLevel,
} from './types'

// ============ Props / Emits ============
const props = withDefaults(defineProps<AiRiskScanPanelProps>(), {
  autoLoad: true,
  similarLimit: 3,
  deepScan: false,
})

const emit = defineEmits<AiRiskScanPanelEmits>()

const router = useRouter()

// ============ 状态 ============
/** 4 个状态：loading / success / error / degraded */
const state = ref<'loading' | 'success' | 'error' | 'degraded'>('loading')
const errorMsg = ref('扫描失败')
const result = ref<AiScanResult | null>(null)

/** 采纳回执（成功采纳的 suggestion 列表） */
const acceptReceipts = ref<Array<{ id: string; title: string; assignee?: string }>>([])

/** 反馈状态（null / up / down） */
const feedback = ref<null | 'up' | 'down'>(null)

/** Fallback 路径（业务降级） */
const fallbackPath = ref<string>('/')
const fallbackLabel = ref<string>('返回列表')

// ============ 计算属性 ============
const warningCount = computed(() => result.value?.warnings.length ?? 0)

/** 智能摘要（用 AI 摘要 + 风险统计生成） */
const summaryText = computed(() => {
  if (!result.value) return ''
  const r = result.value
  const highCount = r.warnings.filter((w) => w.level === 'high').length
  const midCount = r.warnings.filter((w) => w.level === 'medium').length
  if (r.warnings.length === 0) {
    return `本对象 <strong>整体健康</strong>，无明显风险点。建议继续保持监控。`
  }
  return `本对象共发现 <strong>${r.warnings.length} 个风险点</strong>（${highCount} 高 ${midCount} 中），综合健康分 ${r.overallScore}。建议优先处理 <strong>${r.warnings[0]?.title}</strong>。`
})

// ============ 工具函数 ============
function riskLabel(level: RiskLevel): string {
  return { high: '高风险', medium: '中风险', low: '低风险' }[level]
}

function getScoreColor(score: number): string {
  if (score >= 85) return 'var(--color-success)'
  if (score >= 70) return 'var(--color-warning)'
  return 'var(--color-danger)'
}

function formatDelay(days?: number): string {
  if (days === undefined || days === null) return '-'
  if (days === 0) return '0'
  return days > 0 ? `+${days}` : `${days}`
}

function formatPercent(p?: number): string {
  if (p === undefined || p === null) return '-'
  const pct = (p * 100).toFixed(1)
  return p > 0 ? `+${pct}%` : `${pct}%`
}

function getSuggestionClass(index: number, s: AiSuggestion): string {
  if (index === 0) return 'warning'
  if (s.confidence >= 90) return 'success'
  return ''
}

function actionLabel(type: string): string {
  return (
    {
      'create-meeting': '📅 创建会议',
      'send-email': '✉️ 起草邮件',
      'update-status': '✓ 更新状态',
    }[type] || '执行'
  )
}

function getWarningActions(w: AiWarning): Array<{ label: string; primary?: boolean; handler: (w: AiWarning) => void }> {
  // 默认动作（可被业务覆盖）
  return [
    { label: '📝 查看详情', primary: true, handler: (warn) => ElMessage.info(`查看风险详情：${warn.title}`) },
  ]
}

// ============ 加载 / 重试 / 降级 ============

async function load(isManualRetry = false) {
  state.value = 'loading'
  errorMsg.value = '扫描失败'

  try {
    const data = await aiApi.riskScan<AiScanResult>({
      objectType: props.objectType,
      objectId: props.objectId,
      similarLimit: props.similarLimit,
      deepScan: props.deepScan,
    })
    result.value = data
    state.value = 'success'
    emit('loaded', data)
  } catch (e: any) {
    // AI 错误码 → 降级（5001 / 5101-5104）
    const aiDegradeCodes = [5001, 5101, 5102, 5103, 5104]
    if (aiDegradeCodes.includes(e?.code)) {
      state.value = 'degraded'
      ElMessage.warning('AI 服务暂不可用，已切换到普通流程')
      // 设置 fallback 路径
      setFallback()
      return
    }

    // 其他错误
    state.value = 'error'
    errorMsg.value = e?.message || '扫描失败，请稍后重试'
    if (isManualRetry) {
      ElMessage.error(errorMsg.value)
    }
    emit('error', e instanceof Error ? e : new Error(errorMsg.value))
  }
}

function setFallback() {
  // 业务降级：跳到老流程
  const map: Record<string, { path: string; label: string }> = {
    project: { path: '/project/list', label: '返回项目列表' },
    contract: { path: '/contract/list', label: '返回合同列表' },
    expense: { path: '/expense/list', label: '返回费用列表' },
    voucher: { path: '/dashboard', label: '返回工作台' },
  }
  const f = map[props.objectType] ?? { path: '/dashboard', label: '返回工作台' }
  fallbackPath.value = f.path
  fallbackLabel.value = f.label
}

function goFallback() {
  router.push(fallbackPath.value)
}

// ============ 用户操作 ============

async function onAcceptSuggestion(s: AiSuggestion) {
  try {
    // 1. 后端记录采纳
    await aiApi.feedbackSubmit({
      targetType: 'risk',
      targetId: s.id,
      rating: 'up',
      category: 'accurate',
    })

    // 2. 加入回执条
    acceptReceipts.value.push({
      id: s.id,
      title: s.title,
      assignee: s.action?.params?.assignee as string | undefined,
    })

    ElMessage.success('已采纳建议')
    emit('accept-suggestion', s)
  } catch (e: any) {
    ElMessage.error('采纳失败：' + (e?.message || '未知错误'))
  }
}

function undoAccept(r: { id: string; title: string }) {
  acceptReceipts.value = acceptReceipts.value.filter((x) => x.id !== r.id)
  ElMessage.info('已撤销')
}

function executeAction(s: AiSuggestion) {
  if (!s.action) return
  // 业务侧实现：调用各模块对应的 action
  // 这里只做演示跳转
  const type = s.action.type
  ElMessage.info(`执行动作：${actionLabel(type)}`)
  // 业务方可在父组件监听 'accept-suggestion' 后实现具体动作
  emit('accept-suggestion', s)
}

async function onDismiss(w: AiWarning) {
  try {
    await ElMessageBox.confirm(
      `确认忽略"${w.title}"？AI 将不再提醒此风险。`,
      '忽略风险',
      { type: 'warning', confirmButtonText: '确认忽略', cancelButtonText: '取消' }
    )

    await aiApi.riskDismiss({
      warningId: w.id,
      action: 'dismiss',
    })

    // 从本地列表移除
    if (result.value) {
      result.value.warnings = result.value.warnings.filter((x) => x.id !== w.id)
    }
    ElMessage.success('已忽略')
    emit('dismiss-warning', w)
  } catch (e: any) {
    if (e === 'cancel') return
    ElMessage.error('操作失败：' + (e?.message || '未知错误'))
  }
}

async function onFeedback(rating: 'up' | 'down') {
  feedback.value = rating
  try {
    await aiApi.feedbackSubmit({
      targetType: 'risk',
      targetId: String(props.objectId),
      rating,
      category: rating === 'up' ? 'accurate' : 'not-helpful',
    })
  } catch {
    // 静默失败，不打扰
  }
  emit('feedback', { rating })
  ElMessage.success(rating === 'up' ? '感谢你的反馈 👍' : '我们会改进 👎')
}

function downloadReport() {
  ElMessage.info('报告生成中...（Phase 1 占位，Phase 2 接入 PDF 服务）')
}

// ============ 生命周期 ============
onMounted(() => {
  if (props.autoLoad) load()
})

// 监听 props 变化，重新加载
watch(
  () => [props.objectType, props.objectId],
  () => {
    if (props.autoLoad) load()
  }
)

// 暴露方法给父组件
defineExpose({
  reload: () => load(true),
  result: () => result.value,
})
</script>

<style lang="scss" scoped>
.ai-risk-scan-panel {
  /* 容器 */
}

// ============ 卡片头横排 ============
.card-head-inline {
  display: flex;
  justify-content: space-between;
  align-items: center;

  h4 {
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

// ============ 综合评分 + 智能摘要 ============
.ai-overview {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 24px;
  background: linear-gradient(135deg, #F5F3FF 0%, #fff 100%);
  border: 1px solid var(--color-ai-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 20px;
  align-items: center;
  position: relative;
  overflow: hidden;
}
.ai-overview::before {
  content: '✦';
  position: absolute;
  right: -10px; bottom: -30px;
  font-size: 140px;
  color: rgba(124,58,237,0.06);
  font-weight: 700;
  pointer-events: none;
}
.ai-score-big {
  text-align: center;
  padding: 0 24px;
  border-right: 1px solid var(--color-ai-border);
}
.ai-score-big .num {
  font-size: 56px;
  font-weight: 700;
  background: var(--gradient-ai);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-family: var(--font-family-mono);
  line-height: 1;
}
.ai-score-big .label {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-top: 4px;
}
.ai-score-big .risk-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 10px;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
}
.ai-score-big .risk-tag.high { background: var(--color-danger-bg); color: var(--color-danger); }
.ai-score-big .risk-tag.medium { background: var(--color-warning-bg); color: var(--color-warning); }
.ai-score-big .risk-tag.low { background: var(--color-success-bg); color: var(--color-success); }
.ai-score-big .risk-tag .dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.ai-summary-area .h {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.ai-summary-area .text {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.75;
}
.ai-summary-area .text :deep(strong) { color: var(--color-ai); }

// ============ 5 维评分条 ============
.ai-dim-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  font-size: 12.5px;
}
.ai-dim-bar .name {
  width: 70px;
  color: var(--color-text-secondary);
}
.ai-dim-bar .bar {
  flex: 1;
  height: 8px;
  background: #F1F5F9;
  border-radius: var(--radius-full);
  overflow: hidden;
}
.ai-dim-bar .bar .fill {
  height: 100%;
  background: var(--gradient-ai);
  border-radius: var(--radius-full);
  transition: width 0.6s ease;
}
.ai-dim-bar .bar .fill.warn { background: var(--color-warning); }
.ai-dim-bar .score {
  width: 38px;
  text-align: right;
  font-family: var(--font-family-mono);
  font-weight: 600;
  color: var(--color-text-primary);
}

// ============ 风险预警（与 common.css 兼容） ============
.ai-warn {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  background: var(--color-warning-bg);
  border-left: 3px solid var(--color-warning);
  border-radius: var(--radius-md);
  margin-bottom: 10px;
  transition: all 0.2s;
}
.ai-warn:hover { transform: translateX(2px); }
.ai-warn.high { background: var(--color-danger-bg); border-left-color: var(--color-danger); }
.ai-warn.info { background: var(--color-info-bg); border-left-color: var(--color-info); }
.ai-warn .ico {
  width: 32px; height: 32px;
  background: var(--color-warning);
  color: #fff;
  border-radius: var(--radius-sm);
  display: grid; place-items: center;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}
.ai-warn.high .ico { background: var(--color-danger); }
.ai-warn.info .ico { background: var(--color-info); }
.ai-warn .body { flex: 1; min-width: 0; }
.ai-warn .head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  gap: 8px;
}
.ai-warn .title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.ai-warn .desc {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: 8px;
}
.ai-suggestion-inline {
  font-size: 12px;
  color: var(--color-text-secondary);
  background: rgba(255,255,255,0.6);
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  line-height: 1.5;
}
.ai-suggestion-inline strong { color: var(--color-ai); }
.ai-warn .actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

// ============ 采纳回执条 ============
.ai-accept-bar {
  background: var(--color-success-bg);
  border: 1px solid var(--color-success);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #047857;
}
.ai-accept-bar .ico {
  width: 24px; height: 24px;
  background: var(--color-success);
  color: #fff;
  border-radius: 50%;
  display: grid; place-items: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}
.ai-accept-bar .undo {
  margin-left: auto;
  color: var(--color-success);
  text-decoration: underline;
  cursor: pointer;
  font-size: 12px;
}

// 采纳过渡动画
.accept-enter-active, .accept-leave-active { transition: all 0.3s ease; }
.accept-enter-from { opacity: 0; transform: translateY(-8px); }
.accept-leave-to { opacity: 0; transform: translateX(8px); }

// ============ 移动端适配 ============
@media (max-width: 768px) {
  .ai-overview {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  .ai-score-big {
    border-right: none;
    border-bottom: 1px solid var(--color-ai-border);
    padding: 0 0 16px;
  }
  .ai-warn .head { flex-direction: column; align-items: flex-start; }
  .ai-warn .actions { flex-wrap: wrap; }
}
</style>
