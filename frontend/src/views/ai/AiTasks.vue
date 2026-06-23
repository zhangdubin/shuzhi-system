<script setup lang="ts">
/**
 * AiTasks · AI 任务中心（真实接通版）
 * - 列表：POST /api/v1/ai/task/list
 * - 取消：POST /api/v1/ai/task/cancel
 * - KPI 从列表统计自动算
 * - 4 个 tab 过滤（全部/进行中/已完成/失败），queue 排队 = pending
 * - 详情抽屉：后端返回的 progress / doneCount / totalCount / startedAt / finishedAt
 * - 5s 轮询（仅在有 running/pending 任务时）
 */
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { aiApi } from '@/api/ai'
import dayjs from 'dayjs'

const router = useRouter()

type Task = {
  id: string
  type: string
  name?: string
  status: 'running' | 'done' | 'failed' | 'cancelled' | 'pending'
  progress: number
  doneCount: number
  totalCount: number
  startedAt?: string
  finishedAt?: string
  estimatedRemainingSec?: number
}

const tasks = ref<Task[]>([])
const total = ref(0)
const loading = ref(false)
const activeTab = ref<'all' | 'running' | 'done' | 'failed'>('all')
const selectedTask = ref<Task | null>(null)
const detail = ref<any>(null)
const detailLoading = ref(false)
const pollTimer = ref<any>(null)

// 任务名 fallback（后端 name=null 时）
function friendlyName(t: Task) {
  if (t.name && t.name.trim()) return t.name
  const m = typeMeta(t.type)
  const shortId = t.id.length > 12 ? t.id.slice(0, 12) + '…' : t.id
  return `${m.label} · ${shortId}`
}

// 显示用进度：done 强制 100
function displayProgress(t: Task) {
  if (t.status === 'done') return 100
  if (t.status === 'failed' || t.status === 'cancelled') return 0
  return Math.round(t.progress || 0)
}

// 类型 label/icon
const TYPE_META: Record<string, { label: string; icon: string; color: string }> = {
  extract: { label: '字段抽取', icon: '📷', color: '#7C3AED' },
  'extract.batch': { label: '批量抽取', icon: '📑', color: '#7C3AED' },
  'risk.scan': { label: '风险扫描', icon: '📄', color: '#F59E0B' },
  ask: { label: '智能问答', icon: '💬', color: '#4F6BFF' },
  generate: { label: '智能生成', icon: '✍️', color: '#10B981' },
  match: { label: '智能匹配', icon: '🔗', color: '#06B6D4' },
  ocr: { label: 'OCR 识别', icon: '🔍', color: '#7C3AED' },
}
function typeMeta(t: string) {
  return TYPE_META[t] || { label: t || '其他', icon: '✨', color: '#7C3AED' }
}
function statusLabel(s: string) {
  return s === 'running' ? '进行中' : s === 'done' ? '已完成' : s === 'failed' ? '失败' : s === 'cancelled' ? '已取消' : s === 'pending' ? '排队中' : s
}
function timeShort(iso?: string) {
  if (!iso) return '-'
  const d = dayjs(iso)
  const now = dayjs()
  if (d.isSame(now, 'day')) return d.format('HH:mm')
  if (d.isSame(now.subtract(1, 'day'), 'day')) return '昨天'
  if (d.isSame(now, 'year')) return d.format('M/D HH:mm')
  return d.format('YYYY/M/D')
}
function etaText(t: Task) {
  if (t.status === 'running' && t.estimatedRemainingSec != null) {
    if (t.estimatedRemainingSec < 60) return `${t.estimatedRemainingSec} 秒`
    return `${Math.ceil(t.estimatedRemainingSec / 60)} 分钟`
  }
  return '-'
}

// KPI：从前端当前已加载的列表算（不依赖后端额外接口）
const kpi = computed(() => {
  const all = tasks.value
  return {
    total: total.value || all.length,
    running: all.filter((t) => t.status === 'running').length,
    done: all.filter((t) => t.status === 'done').length,
    failed: all.filter((t) => t.status === 'failed' || t.status === 'cancelled').length,
  }
})

// 过滤后任务列表
const filteredTasks = computed(() => {
  if (activeTab.value === 'all') return tasks.value
  if (activeTab.value === 'failed') return tasks.value.filter((t) => t.status === 'failed' || t.status === 'cancelled')
  return tasks.value.filter((t) => t.status === activeTab.value)
})

// 加载列表
async function loadTasks(silent = false) {
  if (!silent) loading.value = true
  try {
    const resp = await aiApi.tasks({ page: 1, pageSize: 50 })
    tasks.value = resp.list || []
    total.value = resp.total || 0
  } catch (e: any) {
    ElMessage.error('任务列表加载失败：' + (e?.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 启动/停止轮询：只有有 running/pending 才轮询
function ensurePolling() {
  if (pollTimer.value) return
  pollTimer.value = setInterval(() => {
    if (tasks.value.some((t) => t.status === 'running' || t.status === 'pending')) {
      loadTasks(true)
    } else {
      stopPolling()
    }
  }, 5000)
}
function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}
watch(
  () => tasks.value.map((t) => t.status).join(','),
  () => {
    if (tasks.value.some((t) => t.status === 'running' || t.status === 'pending')) {
      ensurePolling()
    } else {
      stopPolling()
    }
  }
)

// 详情：直接用列表里这一行（后端无 detail 接口）
function selectTask(t: Task) {
  selectedTask.value = t
  detail.value = null
  detailLoading.value = false
}
function closeDetail() {
  selectedTask.value = null
  detail.value = null
}

// 操作
async function cancelTask(t: Task, evt?: Event) {
  evt?.stopPropagation()
  try {
    await ElMessageBox.confirm(`确定要取消任务「${t.name || t.id}」？`, '取消任务', {
      type: 'warning',
      confirmButtonText: '确认取消',
      cancelButtonText: '再想想',
    })
  } catch {
    return
  }
  try {
    const r = await aiApi.taskCancel(t.id)
    if ((r as any).cancelled) {
      ElMessage.success('已取消')
      loadTasks(true)
    } else {
      ElMessage.warning((r as any).reason || '任务已结束，无需取消')
      loadTasks(true)
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '取消失败')
  }
}

function refresh() {
  loadTasks()
  ElMessage.success('已刷新')
}

onMounted(() => {
  loadTasks()
})
onBeforeUnmount(() => stopPolling())
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/dashboard')">首页</a>
          <span class="sep">/</span>
          <a @click="router.push('/ai/center')">数智（AI）</a>
          <span class="sep">/</span>
          <span class="current">任务中心</span>
        </div>
        <h1>⚡ AI 任务中心</h1>
        <p class="page-desc">查看所有 AI 任务运行状态，支持查看/取消/详情</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="router.push('/ai/center')">← 返回</button>
        <button class="btn btn-primary btn-sm" @click="refresh">↻ 刷新</button>
      </div>
    </div>

    <!-- 4 KPI（实时计算） -->
    <div class="kpi-row">
      <div class="kpi-card info">
        <div class="kpi-num">{{ kpi.total }}</div>
        <div class="kpi-label">总任务</div>
      </div>
      <div class="kpi-card ai">
        <div class="kpi-num">{{ kpi.running }}</div>
        <div class="kpi-label">进行中</div>
      </div>
      <div class="kpi-card success">
        <div class="kpi-num">{{ kpi.done }}</div>
        <div class="kpi-label">已完成</div>
      </div>
      <div class="kpi-card danger">
        <div class="kpi-num">{{ kpi.failed }}</div>
        <div class="kpi-label">失败 / 已取消</div>
      </div>
    </div>

    <!-- 4 status-tabs -->
    <div class="status-tabs">
      <div :class="['tab', { active: activeTab === 'all' }]" @click="activeTab = 'all'">全部 <span class="cnt">{{ kpi.total }}</span></div>
      <div :class="['tab', { active: activeTab === 'running' }]" @click="activeTab = 'running'">进行中 <span class="cnt">{{ kpi.running }}</span></div>
      <div :class="['tab', { active: activeTab === 'done' }]" @click="activeTab = 'done'">已完成 <span class="cnt">{{ kpi.done }}</span></div>
      <div :class="['tab', { active: activeTab === 'failed' }]" @click="activeTab = 'failed'">失败 <span class="cnt">{{ kpi.failed }}</span></div>
    </div>

    <!-- 任务表格 -->
    <div class="task-card">
      <table class="tpl-table">
        <thead>
          <tr>
            <th style="width: 40px;"></th>
            <th>任务</th>
            <th style="width: 110px;">类型</th>
            <th style="width: 220px;">进度</th>
            <th style="width: 90px;">状态</th>
            <th style="width: 110px;">开始时间</th>
            <th style="width: 90px;">预计剩余</th>
            <th style="width: 140px;">操作</th>
          </tr>
        </thead>
        <tbody v-if="!loading && filteredTasks.length">
          <tr
            v-for="t in filteredTasks"
            :key="t.id"
            :class="{ active: selectedTask?.id === t.id }"
            @click="selectTask(t)"
          >
            <td>
              <span class="t-icon" :style="{ background: typeMeta(t.type).color + '22', color: typeMeta(t.type).color }">{{ typeMeta(t.type).icon }}</span>
            </td>
            <td>
              <div class="t-name">{{ friendlyName(t) }}</div>
              <div class="t-desc mono">{{ t.id }}</div>
            </td>
            <td>
              <span class="t-type" :style="{ color: typeMeta(t.type).color, background: typeMeta(t.type).color + '15' }">{{ typeMeta(t.type).label }}</span>
            </td>
            <td>
              <div class="progress">
                <div class="progress-bg">
                  <div :class="['progress-fill', t.status]" :style="{ width: displayProgress(t) + '%' }"></div>
                </div>
                <span class="progress-num">{{ displayProgress(t) }}%</span>
                <span v-if="t.totalCount" class="progress-sub">{{ t.doneCount }}/{{ t.totalCount }}</span>
              </div>
            </td>
            <td>
              <span :class="['tag', t.status]">
                <span v-if="t.status === 'running'" class="dots"><span></span><span></span><span></span></span>
                {{ statusLabel(t.status) }}
              </span>
            </td>
            <td><span class="mono">{{ timeShort(t.startedAt) }}</span></td>
            <td><span class="mono">{{ etaText(t) }}</span></td>
            <td>
              <div class="t-actions">
                <button v-if="t.status === 'running' || t.status === 'pending'" class="ta-btn" @click.stop="cancelTask(t)">取消</button>
                <button class="ta-btn" @click.stop="selectTask(t)">详情</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="loading" class="empty"><span class="spinner"></span>加载中...</div>
      <div v-else-if="!filteredTasks.length" class="empty">
        <div class="empty-icon">📋</div>
        <div class="empty-text">{{ activeTab === 'all' ? '暂无任务记录' : '该状态下没有任务' }}</div>
        <div class="empty-hint">到 <a @click="router.push('/ai/center')">AI 中心</a> 体验 AI 抽取/问答/风险扫描后会自动出现在这里</div>
      </div>
    </div>

    <!-- 详情抽屉 -->
    <div v-if="selectedTask" class="detail-mask" @click="closeDetail">
      <div class="detail-drawer" @click.stop>
        <div class="drawer-head">
          <div>
            <h3>{{ friendlyName(selectedTask) }}</h3>
            <div class="dh-sub mono">{{ selectedTask.id }}</div>
          </div>
          <button class="drawer-close" @click="closeDetail">×</button>
        </div>
        <div class="drawer-body">
          <div v-if="detailLoading" class="d-loading">加载详情...</div>
          <template v-else>
            <div class="d-meta">
              <span :class="['tag', selectedTask.status]">{{ statusLabel(selectedTask.status) }}</span>
              <span class="t-type" :style="{ color: typeMeta(selectedTask.type).color, background: typeMeta(selectedTask.type).color + '15' }">{{ typeMeta(selectedTask.type).label }}</span>
              <span class="mono">开始 {{ timeShort(selectedTask.startedAt) }}</span>
              <span v-if="selectedTask.finishedAt" class="mono">结束 {{ timeShort(selectedTask.finishedAt) }}</span>
            </div>

            <div class="d-progress">
              <div class="dp-bar">
                <div :class="['dp-fill', selectedTask.status]" :style="{ width: displayProgress(selectedTask) + '%' }"></div>
              </div>
              <span class="dp-num">{{ displayProgress(selectedTask) }}%</span>
            </div>
            <div v-if="selectedTask.totalCount" class="d-progress-sub">
              已处理 <b>{{ selectedTask.doneCount }}</b> / 共 <b>{{ selectedTask.totalCount }}</b>
              <span v-if="etaText(selectedTask) !== '-'" class="d-eta">预计剩余 <b>{{ etaText(selectedTask) }}</b></span>
            </div>

            <h4 class="sub-title">任务信息</h4>
            <div class="param-list">
              <div class="param"><span>任务 ID</span><span class="mono">{{ selectedTask.id }}</span></div>
              <div class="param"><span>类型</span><span>{{ typeMeta(selectedTask.type).label }}（{{ selectedTask.type }}）</span></div>
              <div class="param"><span>状态</span><span>{{ statusLabel(selectedTask.status) }}</span></div>
              <div class="param"><span>进度</span><span>{{ displayProgress(selectedTask) }}%</span></div>
              <div v-if="selectedTask.totalCount" class="param"><span>计数</span><span>{{ selectedTask.doneCount }} / {{ selectedTask.totalCount }}</span></div>
              <div v-if="selectedTask.startedAt" class="param"><span>开始时间</span><span class="mono">{{ dayjs(selectedTask.startedAt).format('YYYY-MM-DD HH:mm:ss') }}</span></div>
              <div v-if="selectedTask.finishedAt" class="param"><span>结束时间</span><span class="mono">{{ dayjs(selectedTask.finishedAt).format('YYYY-MM-DD HH:mm:ss') }}</span></div>
              <div v-if="detail?.error" class="param"><span>错误</span><span class="err-text">{{ detail.error }}</span></div>
              <div v-if="detail?.result" class="param"><span>结果</span><span class="mono">已生成</span></div>
            </div>
          </template>
        </div>
        <div class="drawer-foot">
          <button class="btn-s" @click="closeDetail">关闭</button>
          <button v-if="selectedTask.status === 'running' || selectedTask.status === 'pending'" class="btn-s danger" @click="cancelTask(selectedTask)">取消任务</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

$color-ai: #7C3AED;
$gradient-ai: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
$color-ai-bg: rgba(124, 58, 237, 0.08);
$color-ai-border: rgba(124, 58, 237, 0.25);

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-ai; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-actions { display: flex; gap: 8px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500; border-radius: $radius-md; transition: all 0.15s; border: 1px solid transparent; cursor: pointer; font-family: inherit; }
.btn-primary { background: $gradient-ai; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4); } }
.btn-ghost { background: transparent; color: $color-text-secondary; &:hover { background: $color-ai-bg; color: $color-ai; } }
.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }

// KPI
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card { background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-border; border-radius: $radius-md; padding: 16px 18px; }
.kpi-card.info { border-left-color: #64748B; .kpi-num { color: #64748B; } }
.kpi-card.ai { border-left-color: $color-ai; .kpi-num { color: $color-ai; } }
.kpi-card.success { border-left-color: $color-success; .kpi-num { color: $color-success; } }
.kpi-card.danger { border-left-color: $color-danger; .kpi-num { color: $color-danger; } }
.kpi-num { font-size: 26px; font-weight: 700; line-height: 1.2; }
.kpi-label { font-size: 12.5px; color: $color-text-secondary; margin-top: 4px; }

// status tabs
.status-tabs { display: flex; gap: 4px; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 4px; margin-bottom: 16px; overflow-x: auto; }
.tab { padding: 6px 14px; border-radius: $radius-sm; font-size: 12.5px; color: $color-text-secondary; cursor: pointer; transition: all 0.15s; white-space: nowrap; .cnt { color: $color-text-tertiary; font-size: 11px; margin-left: 4px; } &:hover { background: $color-bg; } &.active { background: $gradient-ai; color: #fff; .cnt { color: rgba(255, 255, 255, 0.85); } } }

// task table
.task-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; min-height: 200px; }
.tpl-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.tpl-table th { text-align: left; padding: 10px 12px; background: #FAFBFF; color: $color-text-tertiary; font-weight: 500; font-size: 11.5px; border-bottom: 1px solid $color-border; }
.tpl-table td { padding: 12px; border-bottom: 1px solid $color-border; }
.tpl-table tr { cursor: pointer; transition: background 0.1s; &:hover { background: #FAFBFF; } &.active { background: $color-ai-bg; } &.active td { border-bottom-color: $color-ai-border; } }
.t-icon { display: inline-grid; place-items: center; width: 28px; height: 28px; border-radius: 8px; font-size: 14px; }
.t-name { font-size: 13px; color: $color-text-primary; font-weight: 500; }
.t-desc { font-size: 11px; color: $color-text-tertiary; margin-top: 2px; }
.t-type { display: inline-block; font-size: 11.5px; padding: 2px 8px; border-radius: 9999px; font-weight: 500; }

.progress { display: flex; align-items: center; gap: 8px; }
.progress-bg { flex: 1; height: 6px; background: $color-bg; border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.progress-fill.running { background: $gradient-ai; }
.progress-fill.done { background: $color-success; }
.progress-fill.failed { background: $color-danger; }
.progress-fill.cancelled { background: #94A3B8; }
.progress-fill.pending { background: #94A3B8; }
.progress-num { font-size: 11px; font-family: $font-family-mono; color: $color-text-secondary; min-width: 32px; text-align: right; }
.progress-sub { font-size: 10.5px; color: $color-text-tertiary; font-family: $font-family-mono; }

.tag { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; padding: 2px 8px; border-radius: 9999px; font-weight: 500; }
.tag.running { background: $color-ai-bg; color: $color-ai; }
.tag.done { background: $color-success-bg; color: $color-success; }
.tag.failed { background: $color-danger-bg; color: $color-danger; }
.tag.cancelled { background: rgba(148, 163, 184, 0.15); color: #64748B; }
.tag.pending { background: rgba(148, 163, 184, 0.15); color: #64748B; }
.dots { display: inline-flex; gap: 2px; }
.dots span { width: 4px; height: 4px; background: $color-ai; border-radius: 50%; animation: bounce 1.4s infinite; }
.dots span:nth-child(2) { animation-delay: 0.2s; }
.dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }

.t-actions { display: flex; gap: 4px; }
.ta-btn { padding: 3px 8px; font-size: 11.5px; background: #fff; border: 1px solid $color-border; color: $color-text-secondary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } }
.mono { font-family: $font-family-mono; color: $color-text-secondary; }

// empty
.empty { text-align: center; padding: 60px 20px; color: $color-text-tertiary; font-size: 13px; }
.empty-icon { font-size: 48px; margin-bottom: 8px; opacity: 0.4; }
.empty-text { font-size: 14px; color: $color-text-secondary; margin-bottom: 4px; }
.empty-hint { font-size: 12px; a { color: $color-ai; cursor: pointer; } }
.spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid $color-border; border-top-color: $color-ai; border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 8px; vertical-align: middle; }
@keyframes spin { to { transform: rotate(360deg); } }

// drawer
.detail-mask { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.4); z-index: 100; display: flex; justify-content: flex-end; animation: fadeIn 0.2s; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.detail-drawer { width: 480px; max-width: 90%; background: #fff; height: 100vh; display: flex; flex-direction: column; box-shadow: -4px 0 24px rgba(15, 23, 42, 0.15); animation: slideIn 0.25s; }
@keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
.drawer-head { display: flex; justify-content: space-between; align-items: flex-start; padding: 16px 20px; border-bottom: 1px solid $color-border; background: #FAFBFF; h3 { font-size: 15px; font-weight: 600; margin: 0; } .dh-sub { font-size: 11px; color: $color-text-tertiary; margin-top: 4px; } }
.drawer-close { width: 28px; height: 28px; border-radius: 50%; background: transparent; border: none; font-size: 20px; color: $color-text-tertiary; cursor: pointer; &:hover { background: $color-bg; color: $color-text-primary; } }
.drawer-body { flex: 1; padding: 18px 20px; overflow-y: auto; }
.d-loading { text-align: center; padding: 40px; color: $color-text-tertiary; }
.drawer-foot { padding: 12px 20px; border-top: 1px solid $color-border; display: flex; justify-content: flex-end; gap: 8px; background: #FAFBFF; }
.btn-s { padding: 6px 12px; font-size: 12.5px; background: #fff; border: 1px solid $color-border; color: $color-text-primary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } &.primary { background: $gradient-ai; color: #fff; border-color: transparent; } &.danger { color: $color-danger; border-color: $color-danger; &:hover { background: $color-danger; color: #fff; } } }
.d-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; color: $color-text-secondary; margin-bottom: 12px; }
.d-progress { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; .dp-bar { flex: 1; height: 8px; background: $color-bg; border-radius: 4px; overflow: hidden; } .dp-fill { height: 100%; border-radius: 4px; transition: width 0.3s; } .dp-fill.running { background: $gradient-ai; } .dp-fill.done { background: $color-success; } .dp-fill.failed { background: $color-danger; } .dp-fill.cancelled { background: #94A3B8; } .dp-num { font-size: 13px; font-weight: 600; font-family: $font-family-mono; } }
.d-progress-sub { font-size: 11.5px; color: $color-text-tertiary; margin-bottom: 16px; b { color: $color-text-primary; font-weight: 600; } .d-eta { margin-left: 12px; } }
.sub-title { font-size: 12.5px; font-weight: 600; color: $color-text-primary; margin: 16px 0 10px 0; }
.param-list { background: $color-bg; border-radius: $radius-md; padding: 10px 14px; }
.param { display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px; .mono { font-family: $font-family-mono; } > span:first-child { color: $color-text-tertiary; } > span:last-child { color: $color-text-primary; text-align: right; max-width: 65%; word-break: break-all; } .err-text { color: $color-danger; } }
</style>
