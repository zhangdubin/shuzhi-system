<script setup lang="ts">
/**
 * ProjectKanban · 项目看板（按状态分列）
 * 5 列：规划中 / 进行中 / 即将完成 / 已完成 / 已暂停
 * 每张卡显示：项目名 / 编号 / 客户 / 负责人 / 进度条 / 截止日
 * 顶部：4 KPI（总项目数 / 进行中 / 即将完成 / 已逾期）+ 客户筛选 + 负责人筛选
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { projectApi } from '@/api/modules'

const router = useRouter()
const loading = ref(false)
const projects = ref<any[]>([])

const COLUMNS = [
  { key: 'planning',     label: '规划中',   icon: '💡', tone: 'gray' },
  { key: 'in_progress',  label: '进行中',   icon: '🚀', tone: 'primary' },
  { key: 'finishing',    label: '即将完成', icon: '⏳', tone: 'warning' },
  { key: 'completed',    label: '已完成',   icon: '✅', tone: 'success' },
  { key: 'paused',       label: '已暂停',   icon: '⏸',  tone: 'info' },
]

const clientFilter = ref<string>('')
const managerFilter = ref<string>('')

const filtered = computed(() => {
  return projects.value.filter(p => {
    if (clientFilter.value && p.clientName !== clientFilter.value) return false
    if (managerFilter.value && p.managerName !== managerFilter.value) return false
    return true
  })
})

function byCol(status: string) {
  return filtered.value.filter(p => (p.status || '').toLowerCase() === status)
}

const kpi = computed(() => {
  const total = filtered.value.length
  const inProgress = byCol('in_progress').length
  const finishing = byCol('finishing').length
  const overdue = filtered.value.filter(p => {
    if (!p.endDate) return false
    if ((p.status || '').toLowerCase() === 'completed') return false
    return new Date(p.endDate) < new Date()
  }).length
  return { total, inProgress, finishing, overdue }
})

const clientOptions = computed(() => {
  const set = new Set<string>()
  projects.value.forEach(p => p.clientName && set.add(p.clientName))
  return Array.from(set).sort()
})
const managerOptions = computed(() => {
  const set = new Set<string>()
  projects.value.forEach(p => p.managerName && set.add(p.managerName))
  return Array.from(set).sort()
})

function fmtAmount(n?: number) {
  if (n == null) return '¥ 0'
  if (n >= 10000) return '¥ ' + (n / 10000).toFixed(1) + '万'
  return '¥ ' + Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

function daysLeft(endDate?: string) {
  if (!endDate) return null
  const d = Math.ceil((new Date(endDate).getTime() - Date.now()) / 86400000)
  return d
}

function progressTone(p: number) {
  if (p >= 100) return 'success'
  if (p >= 60) return 'primary'
  if (p >= 30) return 'warning'
  return 'gray'
}

async function load() {
  loading.value = true
  try {
    // 后端 ProjectListRequest.pageSize 限制 le=100；分页拉全部
    const all: any[] = []
    const pageSize = 100
    for (let p = 1; p <= 50; p++) {
      const res: any = await projectApi.list({ page: p, pageSize } as any)
      const list = res?.list || []
      all.push(...list)
      const total = res?.total || 0
      if (list.length < pageSize || all.length >= total) break
    }
    projects.value = all.map((p: any) => ({
      ...p,
      // 兜底：有些后端 status 是中文 "进行中"，统一映射成英文 enum
      status: mapStatus(p.status),
    }))
  } catch (e: any) {
    ElMessage.error('项目列表加载失败：' + (e?.message || '未知错误'))
  } finally {
    loading.value = false
  }
}
function mapStatus(s: string): string {
  const m: Record<string, string> = {
    '规划中': 'planning', '新启动': 'planning', 'planning': 'planning',
    '进行中': 'in_progress', 'in_progress': 'in_progress',
    '即将完成': 'finishing', '即将到期': 'finishing', 'finishing': 'finishing',
    '已完成': 'completed', '完成': 'completed', 'completed': 'completed', 'done': 'completed',
    '已暂停': 'paused', '已停止': 'paused', 'paused': 'paused',
    '已取消': 'cancelled', 'cancelled': 'cancelled',
  }
  return m[s] || s || 'planning'
}

function gotoDetail(p: any) { router.push(`/project/${p.id}`) }
function gotoList() { router.push('/project/list') }
function gotoCreate() { router.push('/project/create') }
function resetFilter() { clientFilter.value = ''; managerFilter.value = '' }

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>项目看板</h1>
        <p class="page-desc">按状态分列查看项目全貌 · 当前 {{ kpi.total }} 个项目</p>
      </div>
      <div style="display:flex;gap:8px">
        <el-button @click="gotoList">← 返回列表</el-button>
        <el-button type="primary" @click="gotoCreate">+ 新建项目</el-button>
      </div>
    </div>

    <!-- KPI -->
    <div class="kpi-row">
      <div class="stat-card">
        <div class="stat-label">总项目数 <span class="stat-icon" style="background:rgba(79,107,255,0.12);color:#4F6BFF">▥</span></div>
        <div class="stat-value">{{ kpi.total }}<span class="unit">个</span></div>
        <div class="stat-delta">按当前筛选</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">进行中 <span class="stat-icon" style="background:rgba(79,107,255,0.12);color:#4F6BFF">🚀</span></div>
        <div class="stat-value">{{ kpi.inProgress }}<span class="unit">个</span></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">即将完成 <span class="stat-icon" style="background:rgba(245,158,11,0.12);color:#F59E0B">⏳</span></div>
        <div class="stat-value">{{ kpi.finishing }}<span class="unit">个</span></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">已逾期 <span class="stat-icon" style="background:rgba(239,68,68,0.12);color:#EF4444">!</span></div>
        <div class="stat-value" :class="{ 'text-danger': kpi.overdue > 0 }">{{ kpi.overdue }}<span class="unit">个</span></div>
        <div class="stat-delta">超过结束日未完成</div>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar" style="display:flex;gap:12px;align-items:center;margin-bottom:16px;flex-wrap:wrap">
      <el-select v-model="clientFilter" placeholder="按客户筛选" clearable style="width:200px">
        <el-option v-for="c in clientOptions" :key="c" :label="c" :value="c" />
      </el-select>
      <el-select v-model="managerFilter" placeholder="按负责人筛选" clearable style="width:200px">
        <el-option v-for="m in managerOptions" :key="m" :label="m" :value="m" />
      </el-select>
      <a v-if="clientFilter || managerFilter" class="reset-link" @click="resetFilter">清除筛选</a>
      <span style="color:#94A3B8;font-size:12px;margin-left:auto">
        💡 点击卡片查看详情
      </span>
    </div>

    <!-- 看板列 -->
    <div class="kanban-row" v-loading="loading">
      <div v-for="col in COLUMNS" :key="col.key" class="kanban-col">
        <div class="kanban-col-head" :class="`tone-${col.tone}`">
          <span class="col-icon">{{ col.icon }}</span>
          <span class="col-label">{{ col.label }}</span>
          <span class="col-count">{{ byCol(col.key).length }}</span>
        </div>
        <div class="kanban-col-body">
          <div
            v-for="p in byCol(col.key)"
            :key="p.id"
            class="kanban-card"
            @click="gotoDetail(p)"
          >
            <div class="card-top">
              <span class="card-code">{{ p.code }}</span>
              <span v-if="daysLeft(p.endDate) !== null && col.key !== 'completed'"
                    :class="['due-pill', daysLeft(p.endDate)! < 0 ? 'due-overdue' : (daysLeft(p.endDate)! < 7 ? 'due-soon' : 'due-ok')]">
                {{ daysLeft(p.endDate) < 0 ? `逾期 ${-daysLeft(p.endDate)!} 天` : `${daysLeft(p.endDate)} 天` }}
              </span>
            </div>
            <div class="card-name">{{ p.name }}</div>
            <div class="card-meta">
              <span>👤 {{ p.clientName || '—' }}</span>
              <span>📌 {{ p.managerName || '—' }}</span>
            </div>
            <div class="card-progress">
              <div class="progress-bar"><div class="progress-fill" :class="`tone-${progressTone(p.progress || 0)}`" :style="{ width: (p.progress || 0) + '%' }"></div></div>
              <span class="progress-text">{{ Math.round(p.progress || 0) }}%</span>
            </div>
            <div class="card-foot">
              <span class="card-budget">{{ fmtAmount(p.contractAmount) }}</span>
              <span v-if="p.endDate" class="card-date">📅 {{ p.endDate }}</span>
            </div>
          </div>
          <div v-if="byCol(col.key).length === 0" class="col-empty">— 暂无 —</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;
@use '@/assets/styles/mixins.scss' as *;

.page-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }
.page-header h1 { @include page-title-h1; margin:0; }
.page-desc { color: $color-text-secondary; font-size:13px; margin:4px 0 0 0; }

.kpi-row { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:16px; }
.stat-card { @include stat-card; }
.text-danger { color: #EF4444; }

.filter-bar .reset-link { font-size:12px; color:$color-primary; cursor:pointer; }

.kanban-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  align-items: flex-start;
}
.kanban-col {
  background: $color-bg;
  border-radius: $radius-md;
  padding: 0 0 8px 0;
  min-height: 200px;
}
.kanban-col-head {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 12px;
  font-size: 13px; font-weight: 600;
  border-radius: $radius-md $radius-md 0 0;
  color: $color-text-primary;
  &.tone-gray    { background: #F1F5F9; color: #64748B; }
  &.tone-primary { background: rgba(79,107,255,0.08);  color: #4F6BFF; }
  &.tone-warning { background: rgba(245,158,11,0.08); color: #F59E0B; }
  &.tone-success { background: rgba(16,185,129,0.08); color: #10B981; }
  &.tone-info    { background: rgba(124,58,237,0.08); color: #7C3AED; }
  .col-icon { font-size: 14px; }
  .col-count {
    margin-left: auto;
    background: #fff;
    color: $color-text-tertiary;
    border-radius: 999px;
    padding: 1px 8px;
    font-size: 11px;
    font-weight: 500;
  }
}
.kanban-col-body {
  padding: 8px;
  display: flex; flex-direction: column; gap: 8px;
}
.col-empty {
  text-align: center; padding: 24px 0; color: $color-text-tertiary; font-size: 12px;
}
.kanban-card {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-sm;
  padding: 10px 12px;
  cursor: pointer;
  transition: all 0.15s;
  &:hover { border-color: $color-primary; box-shadow: 0 4px 12px rgba(79,107,255,0.08); transform: translateY(-1px); }
}
.card-top { display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; }
.card-code { font-family: $font-family-mono; font-size: 11px; color: $color-text-tertiary; }
.due-pill {
  font-size: 10px; padding: 1px 6px; border-radius: 999px; font-weight: 500;
  &.due-ok      { background: rgba(16,185,129,0.10); color: #10B981; }
  &.due-soon    { background: rgba(245,158,11,0.15); color: #F59E0B; }
  &.due-overdue { background: rgba(239,68,68,0.15);  color: #EF4444; }
}
.card-name {
  font-size: 13px; font-weight: 600; color: $color-text-primary;
  margin-bottom: 6px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-meta {
  display: flex; gap: 8px; flex-wrap: wrap;
  font-size: 11px; color: $color-text-secondary;
  margin-bottom: 8px;
}
.card-progress { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.progress-bar {
  flex: 1; height: 4px; background: $color-border; border-radius: 2px; overflow: hidden;
}
.progress-fill { height: 100%; transition: width 0.3s; }
.progress-fill.tone-primary { background: #4F6BFF; }
.progress-fill.tone-warning { background: #F59E0B; }
.progress-fill.tone-success { background: #10B981; }
.progress-fill.tone-gray    { background: #94A3B8; }
.progress-text { font-size: 11px; color: $color-text-tertiary; min-width: 30px; text-align:right; }
.card-foot {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 11px; color: $color-text-tertiary;
}
.card-budget { font-weight: 600; color: $color-text-primary; }
</style>
