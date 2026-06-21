<script setup lang="ts">
/**
 * NoticeCenter · 通知中心（无 design，按 R9 统一 list pattern 自造）
 * - 4 KPI（总数/未读/合同类/AI 类）
 * - 5 type-tabs（全部/合同/费用/回款/AI/系统）+ 2 read-tabs（全部/未读）
 * - 工具栏：全部已读 / 清空
 * - 通知列表（type tag + 标题 + 操作人 + 时间 + 未读圆点）
 * - SSE 实时接入（保留原 sse.connect 逻辑）
 * - localStorage 持久化（保留原 loadFromStorage/saveToStorage）
 */
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { sse } from '@/utils/sse'

interface Notice {
  id: string
  type: string
  action: string
  title: string
  operator?: string
  ts: number
  read: boolean
}

const STORAGE_KEY = 'shuzhi_notices'
const router = useRouter()

const notices = ref<Notice[]>([])
const filterType = ref<string>('all')
const filterRead = ref<'all' | 'unread'>('all')

// 4 KPI
const kpis = ref([
  { label: '通知总数', num: 28, color: 'info',    icon: '🔔', trend: '实时更新' },
  { label: '未读',     num: 5,  color: 'danger',  icon: '●',  trend: '需关注' },
  { label: '合同类',   num: 12, color: 'primary', icon: '📜', trend: '本周 +3' },
  { label: 'AI 类',    num: 6,  color: 'warning', icon: '✦',  trend: '智能分析' },
])

// 5 type-tabs
const typeTabs = ref([
  { key: 'all',      label: '全部',   count: 28 },
  { key: '合同',     label: '合同',   count: 12 },
  { key: '费用',     label: '费用',   count: 5 },
  { key: '回款',     label: '回款',   count: 3 },
  { key: 'AI',       label: 'AI',     count: 6 },
  { key: '系统',     label: '系统',   count: 2 },
])

const filteredNotices = computed(() => {
  return notices.value.filter(n => {
    if (filterType.value !== 'all' && n.type !== filterType.value) return false
    if (filterRead.value === 'unread' && n.read) return false
    return true
  })
})

const stats = computed(() => {
  // 实际数用 notices 动态覆盖
  const liveCounts: Record<string, number> = { all: notices.value.length }
  typeTabs.value.forEach(t => { liveCounts[t.key] = notices.value.filter(n => n.type === t.key).length })
  return { total: notices.value.length, unread: notices.value.filter(n => !n.read).length, liveCounts }
})

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) notices.value = JSON.parse(raw)
  } catch {}
}
function saveToStorage() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notices.value.slice(0, 200)))
  } catch {}
}
function addNotice(n: Omit<Notice, 'id' | 'read'>) {
  const item: Notice = { ...n, id: `${n.ts}_${Math.random().toString(36).slice(2, 8)}`, read: false }
  notices.value.unshift(item)
  if (notices.value.length > 200) notices.value = notices.value.slice(0, 200)
  saveToStorage()
}
function markRead(id: string) {
  const n = notices.value.find(x => x.id === id)
  if (n) { n.read = true; saveToStorage() }
}
function markAllRead() {
  notices.value.forEach(n => n.read = true)
  saveToStorage()
  ElMessage.success('已全部标为已读')
}
function clearAll() {
  notices.value = []
  saveToStorage()
  ElMessage.success('已清空')
}
function timeFmt(ts: number) {
  const d = new Date(ts)
  const now = Date.now()
  const diff = (now - ts) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const typeColor: Record<string, string> = {
  合同: 'primary',
  费用: 'warning',
  回款: 'success',
  AI: 'purple',
  系统: 'info',
}

let sseCleanup: (() => void) | null = null

onMounted(() => {
  loadFromStorage()
  sseCleanup = sse.connect('/sse/dashboard', {
    onEvent: (event, data) => {
      if (event === 'connected' || event === 'keepalive') return
      const item = (data as any) || {}
      addNotice({
        type: item.type || '系统',
        action: item.action || '',
        title: item.title || event,
        operator: item.operator,
        ts: Date.now(),
      })
    },
  })
})
onUnmounted(() => { sseCleanup?.() })
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>🔔 通知中心</h1>
        <p class="page-desc">实时业务动态 · SSE 长连接推送 · localStorage 持久化</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-outline btn-sm" @click="markAllRead">✓ 全部已读</button>
        <button class="btn btn-outline btn-sm danger" @click="clearAll">🗑 清空</button>
      </div>
    </div>

    <!-- 4 KPI -->
    <div class="kpi-row">
      <div v-for="k in kpis" :key="k.label" :class="['kpi-card', k.color]">
        <div class="kpi-head">
          <span class="kpi-label">{{ k.label }}</span>
          <span :class="['kpi-icon', k.color]">{{ k.icon }}</span>
        </div>
        <div class="kpi-num">{{ stats.liveCounts?.[kpiKey(k.label)] ?? k.num }}</div>
        <div class="kpi-trend">{{ k.trend }}</div>
      </div>
    </div>

    <!-- 5 type-tabs + 2 read-tabs -->
    <div class="tab-bar">
      <div class="type-tabs">
        <div v-for="t in typeTabs" :key="t.key" :class="['tab', { active: filterType === t.key }]" @click="filterType = t.key">
          {{ t.label }} <span class="cnt">{{ stats.liveCounts?.[t.key] ?? t.count }}</span>
        </div>
      </div>
      <div class="read-tabs">
        <div :class="['rt', { active: filterRead === 'all' }]" @click="filterRead = 'all'">全部</div>
        <div :class="['rt', { active: filterRead === 'unread' }]" @click="filterRead = 'unread'">未读 <span v-if="stats.unread" class="cnt-danger">{{ stats.unread }}</span></div>
      </div>
    </div>

    <!-- 通知列表 -->
    <div v-if="!filteredNotices.length" class="empty">
      <div class="empty-icon">📭</div>
      <div class="empty-text">{{ notices.length ? '没有符合条件的通知' : '暂无通知，业务操作后将自动出现' }}</div>
    </div>

    <div v-else class="notice-list">
      <div v-for="n in filteredNotices" :key="n.id" :class="['notice-item', { unread: !n.read }]" @click="markRead(n.id)">
        <span :class="['type-tag', typeColor[n.type] || 'info']">{{ n.type }}</span>
        <div class="notice-body">
          <div class="notice-title">{{ n.title }}</div>
          <div class="notice-meta">
            <span v-if="n.operator" class="op">{{ n.operator }}</span>
            <span v-if="n.action">· {{ n.action }}</span>
            <span>· {{ timeFmt(n.ts) }}</span>
          </div>
        </div>
        <div v-if="!n.read" class="unread-dot"></div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
function kpiKey(label: string): string {
  const m: Record<string, string> = { '通知总数': 'all', '未读': 'all', '合同类': '合同', 'AI 类': 'AI' }
  return m[label] || 'all'
}
export default { name: 'NoticeCenter' }
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.page-actions { display: flex; gap: 8px; }
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500; border-radius: $radius-md; transition: all 0.15s; border: 1px solid transparent; cursor: pointer; font-family: inherit; }
.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover:not(:disabled) { border-color: $color-primary; color: $color-primary; } &.danger:hover:not(:disabled) { border-color: $color-danger; color: $color-danger; } }
.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }

// KPI
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card { background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-border; border-radius: $radius-md; padding: 14px 18px; }
.kpi-card.primary { border-left-color: $color-primary; }
.kpi-card.info    { border-left-color: #64748B; }
.kpi-card.success { border-left-color: $color-success; }
.kpi-card.warning { border-left-color: #F59E0B; }
.kpi-card.danger  { border-left-color: $color-danger; }
.kpi-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.kpi-label { font-size: 12.5px; color: $color-text-secondary; }
.kpi-icon { width: 22px; height: 22px; border-radius: $radius-sm; display: grid; place-items: center; font-size: 12px; font-weight: 700; }
.kpi-icon.primary { background: $color-primary-bg; color: $color-primary; }
.kpi-icon.info    { background: rgba(148, 163, 184, 0.15); color: #64748B; }
.kpi-icon.success { background: $color-success-bg; color: $color-success; }
.kpi-icon.warning { background: rgba(245, 158, 11, 0.12); color: #F59E0B; }
.kpi-icon.danger  { background: $color-danger-bg; color: $color-danger; }
.kpi-num { font-size: 24px; font-weight: 700; line-height: 1.2; color: $color-text-primary; }
.kpi-trend { font-size: 11px; color: $color-text-tertiary; margin-top: 4px; }

// tab-bar
.tab-bar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.type-tabs { display: flex; gap: 4px; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 4px; flex-wrap: wrap; }
.tab { padding: 6px 14px; border-radius: $radius-sm; font-size: 12.5px; color: $color-text-secondary; cursor: pointer; transition: all 0.15s; white-space: nowrap; .cnt { color: $color-text-tertiary; font-size: 11px; margin-left: 4px; } &:hover { background: $color-bg; } &.active { background: $gradient-brand; color: #fff; .cnt { color: rgba(255, 255, 255, 0.85); } } }
.read-tabs { display: flex; gap: 4px; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; padding: 4px; }
.rt { padding: 6px 14px; border-radius: $radius-sm; font-size: 12.5px; color: $color-text-secondary; cursor: pointer; transition: all 0.15s; .cnt-danger { display: inline-block; margin-left: 4px; padding: 0 5px; background: $color-danger; color: #fff; border-radius: 9999px; font-size: 10px; font-weight: 600; } &:hover { background: $color-bg; } &.active { background: $color-primary-bg; color: $color-primary; } }

// empty
.empty { text-align: center; padding: 80px 20px; background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; }
.empty-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.5; }
.empty-text { font-size: 13px; color: $color-text-tertiary; }

// notice-list
.notice-list { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; }
.notice-item { display: flex; align-items: center; gap: 12px; padding: 14px 18px; border-bottom: 1px solid #F1F5F9; cursor: pointer; transition: background 0.15s; position: relative; &:hover { background: #FAFBFC; } &.unread { background: $color-primary-bg; } &.unread:hover { background: rgba(79, 107, 255, 0.12); } &:last-child { border-bottom: none; } }
.type-tag { display: inline-block; font-size: 10.5px; padding: 2px 8px; border-radius: 9999px; font-weight: 600; flex-shrink: 0; min-width: 36px; text-align: center; }
.type-tag.primary { background: $color-primary-bg; color: $color-primary; }
.type-tag.success { background: $color-success-bg; color: $color-success; }
.type-tag.warning { background: rgba(245, 158, 11, 0.1); color: #B45309; }
.type-tag.info    { background: rgba(148, 163, 184, 0.15); color: #64748B; }
.type-tag.purple  { background: rgba(124, 58, 237, 0.12); color: #7C3AED; }
.notice-body { flex: 1; min-width: 0; .notice-title { font-size: 13.5px; color: $color-text-primary; font-weight: 500; } .notice-meta { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; .op { color: $color-primary; font-weight: 500; } } }
.unread-dot { width: 8px; height: 8px; border-radius: 50%; background: $color-primary; flex-shrink: 0; }
</style>
