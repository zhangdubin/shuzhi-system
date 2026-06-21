<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { contractApi, type Contract } from '@/api/modules'
import StatGrid from '@/components/StatGrid.vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const list = ref<Contract[]>([])
const total = ref(0)
const query = reactive({
  page: 1, pageSize: 10, keyword: '',
  type: '', status: '',
})

// 合同类型 → 标签色
const TYPE_LABELS: Record<string, { label: string; type: string }> = {
  sales: { label: '销售', type: 'primary' },
  purchase: { label: '采购', type: 'success' },
  service: { label: '服务', type: 'info' },
  framework: { label: '框架', type: 'warning' },
}
function typeLabel(t?: string) { return TYPE_LABELS[t || ''] || { label: t || '—', type: 'info' } }

// 状态 → 标签色（后端英文 → design 中文 + 颜色）
const STATUS_LABELS: Record<string, { label: string; type: string }> = {
  draft:     { label: '草稿',     type: 'info' },
  pending:   { label: '待审批',   type: 'warning' },
  approving: { label: '审批中',   type: 'warning' },
  approved:  { label: '已签订',   type: 'success' },
  rejected:  { label: '已驳回',   type: 'danger' },
  signed:    { label: '已签订',   type: 'success' },
}
function statusLabel(s?: string) { return STATUS_LABELS[s || ''] || { label: s || '—', type: 'info' } }

async function loadList() {
  loading.value = true
  try {
    const res = await contractApi.list({ ...query }).catch(() => ({ list: [], total: 0, page: 1, pageSize: 10 }))
    list.value = res.list
    total.value = res.total
  } catch {
    ElMessage.error('加载合同列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() { query.page = 1; loadList() }
function handlePageChange(p: number) { query.page = p; loadList() }
function gotoDetail(row: any) { router.push(`/contract/${row.contractId}`) }
function gotoAiPanel() { router.push('/ai/panel/contract') }
function fmtAmount(n?: number) {
  if (!n) return '¥ 0.00'
  return '¥ ' + Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtDate(s?: string) { return s ? s.slice(0, 10) : '—' }

// 4 KPI 统计
const stats = ref<any[]>([])
const statsLoading = ref(false)
async function loadStats() {
  statsLoading.value = true
  try {
    const r: any = await contractApi.stats().catch(() => null)
    if (r) {
      stats.value = [
        { key: 'total', label: '合同总数', value: r.total ?? 0, unit: '份', icon: '▦', tone: 'primary' },
        { key: 'amount', label: '合同总金额', value: r.totalAmount ?? 0, unit: '元', icon: '¥', tone: 'success' },
        { key: 'pending', label: '待审批', value: r.pendingApproval ?? 0, unit: '份', icon: '⏱', tone: 'warning' },
        { key: 'expiring', label: '即将到期', value: r.expiringSoon ?? 0, unit: '份', icon: '!', tone: 'danger' },
      ]
    }
  } finally { statsLoading.value = false }
}

onMounted(() => { loadList(); loadStats() })
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>合同列表</h2>
        <p class="page-desc">合同全生命周期管理 · {{ total }} 份合同</p>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="gotoAiPanel">🤖 AI 体检</el-button>
        <el-button type="primary" :icon="'Plus'">新建合同</el-button>
      </div>
    </div>

    <div class="page-card">
      <!-- 4 KPI 统计卡（与 design 对齐） -->
      <StatGrid :stats="stats" :loading="statsLoading" />

      <!-- 筛选栏（与 design 对齐） -->
      <div class="filter-bar">
        <el-input v-model="query.keyword" placeholder="搜索合同名称 / 编号 / 客户" clearable style="width: 260px" @keyup.enter="handleSearch" />
        <el-select v-model="query.type" placeholder="合同类型" clearable style="width: 140px">
          <el-option v-for="(v, k) in TYPE_LABELS" :key="k" :label="v.label" :value="k" />
        </el-select>
        <el-select v-model="query.status" placeholder="审批状态" clearable style="width: 140px">
          <el-option v-for="(v, k) in STATUS_LABELS" :key="k" :label="v.label" :value="k" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
        <el-button @click="query.keyword='';query.type='';query.status='';handleSearch()">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="list" stripe @row-click="gotoDetail" row-class-name="clickable">
        <el-table-column prop="code" label="合同编号" width="150" />
        <el-table-column prop="name" label="合同名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="clientName" label="客户" width="160" show-overflow-tooltip />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="typeLabel(row.type).type as any" size="small">{{ typeLabel(row.type).label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" width="160" align="right">
          <template #default="{ row }">
            <span style="font-family: var(--font-mono); font-weight: 600; color: var(--color-primary);">
              {{ fmtAmount(row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="签订日期" width="120">
          <template #default="{ row }">{{ fmtDate(row.signDate) }}</template>
        </el-table-column>
        <el-table-column label="到期日期" width="120">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.expireDate && new Date(row.expireDate) < new Date() }">
              {{ fmtDate(row.expireDate) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="审批状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusLabel(row.status).type as any" size="small">{{ statusLabel(row.status).label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="电子签" width="80" align="center">
          <template #default="{ row }">
            <span v-if="row.status === 'approved' || row.status === 'signed'" class="sign-done">✓ 已签</span>
            <span v-else class="sign-none">! 未签</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click.stop="gotoDetail(row)">查看</el-button>
            <el-button type="primary" link size="small" @click.stop="ElMessage.info('催办：' + row.code)">催办</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无合同数据" /></template>
      </el-table>

      <el-pagination
        v-model:current-page="query.page"
        :page-size="query.pageSize"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        :page-sizes="[10, 20, 50]"
        class="pager"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.pager { margin-top: 16px; justify-content: flex-end; }
:deep(.clickable) { cursor: pointer; }
.text-danger { color: var(--color-danger); }
.sign-done { color: var(--color-success); font-weight: 600; }
.sign-none { color: var(--color-warning); font-weight: 600; }
</style>
