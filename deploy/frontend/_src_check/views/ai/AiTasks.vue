<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { aiApi } from '@/api/ai'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const stats = reactive({ total: 0, running: 0, success: 0, failed: 0, totalCost: 0 })
const query = reactive({ page: 1, pageSize: 10, status: '', type: '' })

// 4 KPI 统计（前端从列表算，避免后端加接口）
const statCards = computed(() => [
  { key: 'total', label: '总任务数', value: stats.total, icon: '📊', tone: 'primary' },
  { key: 'running', label: '进行中', value: stats.running, icon: '⚡', tone: 'warning' },
  { key: 'success', label: '已完成', value: stats.success, icon: '✓', tone: 'success' },
  { key: 'cost', label: '累计成本(分)', value: stats.totalCost, icon: '¥', tone: 'info' },
])

const TYPE_OPTIONS = [
  { value: 'extract', label: '智能抽取' },
  { value: 'risk_scan', label: '风险扫描' },
  { value: 'ask', label: '智能问答' },
  { value: 'classify', label: '智能分类' },
  { value: 'summarize', label: '智能摘要' },
]
const STATUS_OPTIONS = [
  { value: 'pending', label: '待处理', type: 'info' },
  { value: 'running', label: '进行中', type: 'warning' },
  { value: 'success', label: '已完成', type: 'success' },
  { value: 'failed', label: '失败', type: 'danger' },
  { value: 'cancelled', label: '已取消', type: 'info' },
]
function statusMeta(s?: string) { return STATUS_OPTIONS.find(x => x.value === s) || { label: s || '—', type: 'info' } }
function typeLabel(t?: string) { return TYPE_OPTIONS.find(x => x.value === t)?.label || t || '—' }

async function load() {
  loading.value = true
  try {
    const res: any = await aiApi.tasks(query).catch(() => ({ list: [], total: 0 }))
    list.value = res.list || []
    total.value = res.total || 0
    // 统计（从全量算）
    if (query.page === 1 && !query.status && !query.type) {
      const all: any = await aiApi.tasks({ page: 1, pageSize: 1000 }).catch(() => ({ list: [], total: 0 }))
      const arr = all.list || []
      stats.total = all.total || arr.length
      stats.running = arr.filter((t: any) => t.status === 'running' || t.status === 'pending').length
      stats.success = arr.filter((t: any) => t.status === 'success').length
      stats.failed = arr.filter((t: any) => t.status === 'failed').length
      stats.totalCost = arr.reduce((s: number, t: any) => s + (Number(t.cost) || 0), 0)
    }
  } finally { loading.value = false }
}

function handleSearch() { query.page = 1; load() }
function viewTask(row: any) { ElMessage.info(`任务详情：${row.taskId}（开发中）`) }
function retryTask(row: any) { ElMessage.success(`已重试任务：${row.taskId}（演示）`) }
function cancelTask(row: any) { ElMessage.warning(`已取消任务：${row.taskId}（演示）`) }
function fmtTime(s?: string) { return s ? s.slice(0, 19).replace('T', ' ') : '—' }

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>AI 任务中心</h2>
        <p class="page-desc">所有 AI 调用记录、用量、置信度、状态</p>
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
        <el-select v-model="query.type" placeholder="任务类型" clearable style="width: 160px">
          <el-option v-for="t in TYPE_OPTIONS" :key="t.value" :label="t.label" :value="t.value" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 140px">
          <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
        <el-button @click="query.type='';query.status='';handleSearch()">重置</el-button>
      </div>

      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="taskId" label="任务 ID" width="220">
          <template #default="{ row }">
            <span class="mono">{{ row.taskId || row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ typeLabel(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="(statusMeta(row.status).type as any)" size="small">
              <span v-if="row.status === 'running'">⚡ {{ statusMeta(row.status).label }}</span>
              <span v-else>{{ statusMeta(row.status).label }}</span>
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model" label="模型" width="160" />
        <el-table-column label="置信度" width="100">
          <template #default="{ row }">
            <el-progress
              v-if="row.confidence != null"
              :percentage="Math.round((row.confidence as number) * 100)"
              :stroke-width="6"
              :status="(row.confidence as number) >= 0.9 ? 'success' : (row.confidence as number) >= 0.7 ? 'warning' : 'exception'"
            />
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="100">
          <template #default="{ row }">{{ row.elapsed ? row.elapsed + 'ms' : '—' }}</template>
        </el-table-column>
        <el-table-column label="成本" width="100" align="right">
          <template #default="{ row }">
            <span class="mono">{{ row.cost || 0 }} 分</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewTask(row)">详情</el-button>
            <el-button v-if="row.status === 'failed'" type="warning" link size="small" @click="retryTask(row)">重试</el-button>
            <el-button v-if="row.status === 'running' || row.status === 'pending'" type="danger" link size="small" @click="cancelTask(row)">取消</el-button>
          </template>
        </el-table-column>
        <template #empty><el-empty description="暂无 AI 任务" /></template>
      </el-table>

      <el-pagination
        v-model:current-page="query.page"
        :page-size="query.pageSize"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        :page-sizes="[10, 20, 50]"
        class="pager"
        @current-change="load"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.kpi-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px;
  @media (max-width: 1024px) { grid-template-columns: repeat(2, 1fr); }
}
.kpi-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  display: flex; align-items: center; gap: 14px;
  position: relative; overflow: hidden;
  &::after {
    content: ''; position: absolute; right: -30px; top: -30px;
    width: 100px; height: 100px; border-radius: 50%; opacity: 0.12;
  }
  .ic {
    width: 44px; height: 44px; border-radius: var(--radius-md);
    display: grid; place-items: center; font-size: 22px; flex-shrink: 0;
  }
  .meta .l { font-size: 12px; color: var(--color-text-tertiary); margin-bottom: 4px; }
  .meta .v { font-size: 22px; font-weight: 700; color: var(--color-text-primary); line-height: 1.1; font-family: var(--font-family-mono); }
  &.tone-primary .ic { background: var(--color-primary-bg); color: var(--color-primary); }
  &.tone-primary::after { background: var(--color-primary); }
  &.tone-success .ic { background: var(--color-success-bg); color: var(--color-success); }
  &.tone-success::after { background: var(--color-success); }
  &.tone-warning .ic { background: var(--color-warning-bg); color: var(--color-warning); }
  &.tone-warning::after { background: var(--color-warning); }
  &.tone-info .ic { background: rgba(124, 58, 237, 0.12); color: #7C3AED; }
  &.tone-info::after { background: #7C3AED; }
}
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.pager { margin-top: 16px; justify-content: flex-end; }
.mono { font-family: var(--font-family-mono); }
.text-muted { color: var(--color-text-tertiary); }
</style>
