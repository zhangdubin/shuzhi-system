<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { expenseApi, type Expense } from '@/api/modules'
import StatGrid from '@/components/StatGrid.vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const statsLoading = ref(false)
const stats = ref<any[]>([])
const list = ref<Expense[]>([])
const total = ref(0)
const query = reactive({
  page: 1, pageSize: 10, keyword: '',
  category: '', status: '',
})

async function loadStats() {
  statsLoading.value = true
  try {
    const r: any = await expenseApi.stats().catch(() => null)
    if (r) {
      const k = r.kpi || {}
      stats.value = [
        { key: 'total', label: '本期费用总额', value: k.totalAmount ?? 0, unit: '元', icon: '¥', tone: 'primary' },
        { key: 'pending', label: '待审批', value: k.pendingCount ?? 0, unit: '笔', icon: '⏱', tone: 'warning' },
        { key: 'approved', label: '已通过', value: k.approvedCount ?? 0, unit: '笔', icon: '✓', tone: 'success' },
        { key: 'rejected', label: '已驳回', value: k.rejectedCount ?? 0, unit: '笔', icon: '✕', tone: 'danger' },
      ]
    }
  } finally { statsLoading.value = false }
}

const CAT_LABELS: Record<string, { label: string; type: string }> = {
  差旅: { label: '差旅', type: 'primary' },
  招待: { label: '招待', type: 'danger' },
  办公: { label: '办公', type: 'success' },
  推广: { label: '推广', type: 'warning' },
  培训: { label: '培训', type: 'info' },
  其他: { label: '其他', type: 'info' },
}
function catLabel(c?: string) { return CAT_LABELS[c || ''] || { label: c || '—', type: 'info' } }

const STATUS_META: Record<string, { label: string; type: string }> = {
  draft:     { label: '草稿',     type: 'info' },
  pending:   { label: '待审批',   type: 'warning' },
  approving: { label: '审批中',   type: 'warning' },
  approved:  { label: '已批准',   type: 'success' },
  rejected:  { label: '已驳回',   type: 'danger' },
  paid:      { label: '已支付',   type: 'success' },
}
function statusLabel(s?: string) { return STATUS_META[s || ''] || { label: s || '—', type: 'info' } }

async function load() {
  loading.value = true
  try {
    const res = await expenseApi.list({ ...query }).catch(() => ({ list: [], total: 0, page: 1, pageSize: 10 }))
    list.value = res.list
    total.value = res.total
  } finally { loading.value = false }
}
function handleSearch() { query.page = 1; load() }
function gotoDetail(row: any) { router.push(`/expense/${row.expenseId}`) }
function fmtAmount(n?: number) {
  if (!n) return '¥ 0.00'
  return '¥ ' + Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtDate(s?: string) { return s ? s.slice(0, 16).replace('T', ' ') : '—' }

onMounted(() => { load(); loadStats() })
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>销售费用</h2>
        <p class="page-desc">差旅 / 招待 / 业务费等报销管理 · 共 {{ total }} 条</p>
      </div>
      <el-button type="primary" :icon="'Plus'">新建报销</el-button>
    </div>
    <div class="page-card">
      <StatGrid :stats="stats" :loading="statsLoading" />
      <div class="filter-bar">
        <el-input v-model="query.keyword" placeholder="搜索单号 / 事由" clearable style="width: 240px" @keyup.enter="handleSearch" />
        <el-select v-model="query.category" placeholder="类型" clearable style="width: 120px">
          <el-option v-for="(v, k) in CAT_LABELS" :key="k" :label="v.label" :value="k" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 120px">
          <el-option v-for="(v, k) in STATUS_META" :key="k" :label="v.label" :value="k" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
        <el-button @click="query.keyword='';query.category='';query.status='';handleSearch()">重置</el-button>
      </div>
      <el-table v-loading="loading" :data="list" stripe @row-click="gotoDetail" row-class-name="clickable">
        <el-table-column prop="code" label="申请单号" width="150" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag :type="catLabel(row.category).type as any" size="small">{{ catLabel(row.category).label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="事由" min-width="220" show-overflow-tooltip />
        <el-table-column prop="applicantName" label="申请人" width="100" />
        <el-table-column prop="departmentName" label="部门" width="120" />
        <el-table-column label="提交时间" width="160">
          <template #default="{ row }">{{ fmtDate(row.submitAt || row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="金额" width="140" align="right">
          <template #default="{ row }">
            <span style="font-family: var(--font-mono); font-weight: 600; color: var(--color-primary);">
              {{ fmtAmount(row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusLabel(row.status).type as any" size="small">{{ statusLabel(row.status).label }}</el-tag>
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
</style>
