<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { receivableApi, type Receivable } from '@/api/modules'
import StatGrid from '@/components/StatGrid.vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const statsLoading = ref(false)
const stats = ref<any[]>([])
const list = ref<Receivable[]>([])
const total = ref(0)
const query = reactive({
  page: 1, pageSize: 10, keyword: '',
  status: '', type: '',
})

async function loadStats() {
  statsLoading.value = true
  try {
    const r: any = await receivableApi.stats().catch(() => null)
    if (r) {
      const k = r.kpi || {}
      stats.value = [
        { key: 'month', label: '本月回款', value: k.thisMonthReceived ?? 0, unit: '元', icon: '✓', tone: 'success' },
        { key: 'pending', label: '待回款', value: k.pendingTotal ?? 0, unit: '元', icon: '⏱', tone: 'warning' },
        { key: 'rate', label: '完成率', value: Math.round((k.completionRate || 0) * 100), unit: '%', icon: '%', tone: 'primary' },
        { key: 'overdue', label: '逾期笔数', value: k.overdueCount ?? 0, unit: '笔', icon: '!', tone: 'danger' },
      ]
    }
  } finally { statsLoading.value = false }
}

const TYPE_LABELS: Record<string, string> = {
  prepayment: '预付款', progress: '进度款', final: '尾款', warranty: '质保金',
}
const STATUS_META: Record<string, { label: string; type: string }> = {
  pending:   { label: '待回款',   type: 'warning' },
  partial:   { label: '部分回款', type: 'info' },
  received:  { label: '已回款',   type: 'success' },
  overdue:   { label: '已逾期',   type: 'danger' },
  cancelled: { label: '已取消',   type: 'info' },
}
function statusLabel(s?: string) { return STATUS_META[s || ''] || { label: s || '—', type: 'info' } }

function fmtAmount(n?: number) {
  if (!n) return '¥ 0.00'
  return '¥ ' + Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtDate(s?: string) { return s ? s.slice(0, 10) : '—' }
function progressPct(r: any) {
  const plan = Number(r.planAmount) || 0
  const recv = Number(r.receivedAmount) || 0
  if (!plan) return 0
  return Math.min(100, Math.round((recv / plan) * 100))
}
function progressColor(pct: number) {
  if (pct >= 100) return 'var(--color-success)'
  if (pct >= 50) return 'var(--color-primary)'
  return 'var(--color-warning)'
}
function gotoDetail(row: any) { router.push(`/receivable/${row.receivableId}`) }

async function load() {
  loading.value = true
  try {
    const res = await receivableApi.list({ ...query }).catch(() => ({ list: [], total: 0, page: 1, pageSize: 10 }))
    list.value = res.list; total.value = res.total
  } finally { loading.value = false }
}
function handleSearch() { query.page = 1; load() }

onMounted(() => { load(); loadStats() })
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>回款管理</h2>
        <p class="page-desc">合同回款计划与到账跟踪 · 共 {{ total }} 条</p>
      </div>
      <el-button type="primary" :icon="'Plus'">新建回款</el-button>
    </div>
    <div class="page-card">
      <StatGrid :stats="stats" :loading="statsLoading" />
      <div class="filter-bar">
        <el-input v-model="query.keyword" placeholder="搜索回款编号 / 合同 / 客户" clearable style="width: 260px" @keyup.enter="handleSearch" />
        <el-select v-model="query.type" placeholder="回款类型" clearable style="width: 130px">
          <el-option v-for="(v, k) in TYPE_LABELS" :key="k" :label="v" :value="k" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 130px">
          <el-option v-for="(v, k) in STATUS_META" :key="k" :label="v.label" :value="k" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
        <el-button @click="query.keyword='';query.type='';query.status='';handleSearch()">重置</el-button>
      </div>
      <el-table v-loading="loading" :data="list" stripe @row-click="gotoDetail" row-class-name="clickable">
        <el-table-column prop="code" label="回款编号" width="150" />
        <el-table-column prop="contractCode" label="关联合同" width="150" show-overflow-tooltip />
        <el-table-column prop="clientName" label="客户" width="160" show-overflow-tooltip />
        <el-table-column label="回款金额" width="160" align="right">
          <template #default="{ row }">
            <span style="font-family: var(--font-mono); font-weight: 600; color: var(--color-primary);">
              {{ fmtAmount(row.planAmount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="180">
          <template #default="{ row }">
            <div class="progress-cell">
              <el-progress :percentage="progressPct(row)" :stroke-width="6" :color="progressColor(progressPct(row))" />
              <div class="progress-meta">
                <span>已收 {{ fmtAmount(row.receivedAmount) }}</span>
                <span v-if="row.pendingAmount && Number(row.pendingAmount) > 0" class="text-warning">
                  待收 {{ fmtAmount(row.pendingAmount) }}
                </span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="计划日期" width="120">
          <template #default="{ row }">{{ fmtDate(row.planDate) }}</template>
        </el-table-column>
        <el-table-column label="实际日期" width="120">
          <template #default="{ row }">
            <span v-if="row.actualDate">{{ fmtDate(row.actualDate) }}</span>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="managerName" label="负责人" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusLabel(row.status).type as any" size="small">
              {{ statusLabel(row.status).label }}
              <span v-if="row.overdueDays && Number(row.overdueDays) > 0" style="margin-left: 4px;">{{ row.overdueDays }}d</span>
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click.stop="gotoDetail(row)">查看</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无数据" /></template>
      </el-table>
      <el-pagination
        v-model:current-page="query.page"
        :page-size="query.pageSize"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        :page-sizes="[10, 20, 50]"
        class="pager"
        @current-change="(p: number) => { query.page = p; load() }"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.pager { margin-top: 16px; justify-content: flex-end; }
:deep(.clickable) { cursor: pointer; }
.progress-cell { display: flex; flex-direction: column; gap: 4px; }
.progress-meta { font-size: 11px; color: #94A3B8; display: flex; justify-content: space-between; }
.text-warning { color: var(--color-warning); }
.text-muted { color: #94A3B8; }
</style>
