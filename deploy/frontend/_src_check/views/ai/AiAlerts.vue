<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { aiApi } from '@/api/ai'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const list = ref<any[]>([])
const stats = reactive({ total: 0, critical: 0, warning: 0, info: 0 })
const query = reactive({ level: '', type: '' })

const LEVEL_META: Record<string, { label: string; type: string; icon: string; bg: string; color: string }> = {
  critical: { label: '严重', type: 'danger',  icon: '🔴', bg: 'rgba(239,68,68,0.12)',  color: '#EF4444' },
  warning:  { label: '警告', type: 'warning', icon: '🟠', bg: 'rgba(245,158,11,0.12)', color: '#F59E0B' },
  info:     { label: '提示', type: 'info',    icon: '🔵', bg: 'rgba(79,107,255,0.12)', color: '#4F6BFF' },
}
function levelMeta(l?: string) { return LEVEL_META[l || ''] || LEVEL_META.info }

const TYPE_OPTIONS = [
  { value: 'risk', label: '风险' },
  { value: 'overdue', label: '逾期' },
  { value: 'anomaly', label: '异常' },
  { value: 'opportunity', label: '机会' },
  { value: 'system', label: '系统' },
]

const statCards = computed(() => [
  { key: 'total', label: '总提醒', value: stats.total, icon: '📋', tone: 'primary' },
  { key: 'critical', label: '严重', value: stats.critical, icon: '🔴', tone: 'danger' },
  { key: 'warning', label: '警告', value: stats.warning, icon: '🟠', tone: 'warning' },
  { key: 'info', label: '提示', value: stats.info, icon: '🔵', tone: 'info' },
])

async function load() {
  loading.value = true
  try {
    const res: any = await aiApi.alerts({ limit: 100 }).catch(() => [])
    const arr = Array.isArray(res) ? res : (res.list || [])
    list.value = arr
    // 统计
    stats.total = arr.length
    stats.critical = arr.filter((a: any) => a.level === 'critical').length
    stats.warning = arr.filter((a: any) => a.level === 'warning').length
    stats.info = arr.filter((a: any) => a.level === 'info').length
  } finally { loading.value = false }
}

function handleSearch() { load() }
function viewAlert(row: any) {
  if (row.actionUrl) router.push(row.actionUrl)
  else ElMessage.info('查看详情')
}
function ignoreAlert(row: any) {
  ElMessageBox.confirm(`忽略提醒：${row.title}？`, '忽略确认', { type: 'warning' })
    .then(() => {
      list.value = list.value.filter(x => x.id !== row.id)
      ElMessage.success('已忽略')
    })
    .catch(() => {})
}
function fmtTime(s?: string) { return s ? s.slice(0, 16).replace('T', ' ') : '—' }

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>智能预警 <span class="ai-badge">AI</span></h2>
        <p class="page-desc">AI 实时监测业务风险、异常、机会，自动推送至决策人</p>
      </div>
      <el-button :icon="'Refresh'" @click="load">刷新</el-button>
    </div>

    <!-- 4 KPI 卡 -->
    <div class="kpi-grid">
      <div v-for="s in statCards" :key="s.key" :class="['kpi-card', `tone-${s.tone}`]">
        <div class="ic">{{ s.icon }}</div>
        <div class="meta">
          <div class="l">{{ s.label }}</div>
          <div class="v">{{ s.value.toLocaleString() }}</div>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="filter-bar">
        <el-select v-model="query.level" placeholder="严重等级" clearable style="width: 140px">
          <el-option v-for="(v, k) in LEVEL_META" :key="k" :label="v.label" :value="k" />
        </el-select>
        <el-select v-model="query.type" placeholder="提醒类型" clearable style="width: 140px">
          <el-option v-for="t in TYPE_OPTIONS" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
        <el-button @click="query.level='';query.type='';handleSearch()">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column label="等级" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="levelMeta(row.level).type as any" size="small" effect="dark">
              {{ levelMeta(row.level).icon }} {{ levelMeta(row.level).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <span class="type-tag">{{ row.type || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column prop="summary" label="摘要" min-width="280" show-overflow-tooltip />
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ fmtTime(row.createdAt || row.time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.actionUrl" type="primary" link size="small" @click="viewAlert(row)">{{ row.actionLabel || '查看' }}</el-button>
            <el-button type="danger" link size="small" @click="ignoreAlert(row)">忽略</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无提醒" /></template>
      </el-table>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.ai-badge {
  display: inline-block; padding: 2px 8px; margin-left: 8px;
  background: linear-gradient(135deg, #4F6BFF, #7C3AED);
  color: #fff; font-size: 11px; font-weight: 600;
  border-radius: 10px; letter-spacing: 0.5px;
  vertical-align: middle;
}
.kpi-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px;
  @media (max-width: 1024px) { grid-template-columns: repeat(2, 1fr); }
}
.kpi-card {
  background: var(--color-bg-card); border: 1px solid var(--color-border);
  border-radius: var(--radius-lg); padding: 18px 20px;
  display: flex; align-items: center; gap: 14px;
  &.tone-primary .ic { background: var(--color-primary-bg); color: var(--color-primary); }
  &.tone-danger .ic { background: rgba(239,68,68,0.12); color: #EF4444; }
  &.tone-warning .ic { background: var(--color-warning-bg); color: var(--color-warning); }
  &.tone-info .ic { background: rgba(79,107,255,0.12); color: var(--color-primary); }
  .ic { width: 44px; height: 44px; border-radius: var(--radius-md); display: grid; place-items: center; font-size: 22px; }
  .meta .l { font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 4px; }
  .meta .v { font-size: 22px; font-weight: 700; color: var(--color-text-primary); font-family: var(--font-family-mono); }
}
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.type-tag { padding: 2px 8px; font-size: 11px; background: var(--color-bg); border-radius: 4px; color: var(--color-text-tertiary); }
</style>
