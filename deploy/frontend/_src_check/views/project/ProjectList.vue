<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { projectApi, type Project } from '@/api/modules'
import StatGrid from '@/components/StatGrid.vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const list = ref<Project[]>([])
const total = ref(0)
const query = reactive({
  page: 1, pageSize: 12, keyword: '',
  type: '', status: '',
})

// 状态 → design 标签 + 卡片左边色条
const STATUS_META: Record<string, { label: string; tag: string; cardClass: string }> = {
  planning:    { label: '规划中', tag: 'info',    cardClass: '' },
  in_progress: { label: '进行中', tag: 'primary', cardClass: '' },
  active:      { label: '进行中', tag: 'primary', cardClass: '' },
  completed:   { label: '已完成', tag: 'success', cardClass: 'success' },
  paused:      { label: '已暂停', tag: 'warning', cardClass: 'paused' },
  cancelled:   { label: '已取消', tag: 'danger',  cardClass: 'paused' },
  draft:       { label: '草稿',   tag: 'info',    cardClass: '' },
}
function statusMeta(s?: string) { return STATUS_META[s || ''] || { label: s || '—', tag: 'info', cardClass: '' } }

const TYPE_LABELS: Record<string, string> = {
  '数智化转型': '数智化转型', 'SaaS 实施': 'SaaS 实施',
  '系统集成': '系统集成', '定制开发': '定制开发',
  '运维支持': '运维支持', '咨询服务': '咨询服务',
}

async function loadList() {
  loading.value = true
  try {
    const res = await projectApi.list({ ...query }).catch(() => ({ list: [], total: 0, page: 1, pageSize: 12 }))
    list.value = res.list
    total.value = res.total
  } catch {
    ElMessage.error('加载项目列表失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() { query.page = 1; loadList() }
function handlePageChange(p: number) { query.page = p; loadList() }
function gotoDetail(row: Project) { router.push(`/project/${row.id}`) }
function gotoAiPanel() { router.push('/ai/panel/project') }
function fmtAmount(n?: number) {
  if (!n) return '¥ 0'
  return '¥ ' + Number(n).toLocaleString('zh-CN')
}
function fmtDate(s?: string) { return s ? s.slice(0, 10) : '—' }
function daysLeft(endDate?: string) {
  if (!endDate) return null
  const diff = Math.ceil((new Date(endDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
  return diff
}

// 4 KPI 统计
const statsLoading = ref(false)
const stats = ref<any[]>([])
async function loadStats() {
  statsLoading.value = true
  try {
    const r: any = await projectApi.stats().catch(() => null)
    if (r) {
      stats.value = [
        { key: 'active', label: '在建项目', value: r.active ?? 0, unit: '个', icon: '▥', tone: 'primary' },
        { key: 'new', label: '本月新增', value: r.newThisMonth ?? 0, unit: '个', icon: '✦', tone: 'success' },
        { key: 'completed', label: '本月完成', value: r.completedThisMonth ?? 0, unit: '个', icon: '✓', tone: 'info' },
        { key: 'amount', label: '总合同金额', value: r.totalContractAmount ?? 0, unit: '元', icon: '¥', tone: 'warning' },
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
        <h2>项目列表</h2>
        <p class="page-desc">管理所有项目，关联合同 / 费用 / 回款 / 发票 · 共 {{ total }} 个项目</p>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="gotoAiPanel">🤖 AI 智能分析</el-button>
        <el-button type="primary" :icon="'Plus'">新建项目</el-button>
      </div>
    </div>

    <div class="page-card">
      <StatGrid :stats="stats" :loading="statsLoading" />
      <div class="filter-bar">
        <el-input v-model="query.keyword" placeholder="搜索项目名称 / 编号" clearable style="width: 260px" @keyup.enter="handleSearch" />
        <el-select v-model="query.type" placeholder="项目类型" clearable style="width: 140px">
          <el-option v-for="(v, k) in TYPE_LABELS" :key="k" :label="v" :value="k" />
        </el-select>
        <el-select v-model="query.status" placeholder="状态" clearable style="width: 140px">
          <el-option v-for="(v, k) in STATUS_META" :key="k" :label="v.label" :value="k" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="handleSearch">查询</el-button>
        <el-button @click="query.keyword='';query.type='';query.status='';handleSearch()">重置</el-button>
      </div>

      <!-- 卡片网格（与 design/project.html 一致） -->
      <div v-loading="loading" class="project-grid">
        <div
          v-for="row in list"
          :key="row.id"
          :class="['project-card', statusMeta(row.status).cardClass]"
          @click="gotoDetail(row)"
        >
          <div class="p-head">
            <div>
              <div class="p-id">{{ row.code }}</div>
              <h4 class="p-name">{{ row.name }}</h4>
            </div>
            <el-tag :type="statusMeta(row.status).tag as any" size="small">{{ statusMeta(row.status).label }}</el-tag>
          </div>
          <div class="p-client">
            <span class="lbl">客户：</span><strong>{{ row.clientName || '—' }}</strong>
          </div>
          <div class="p-type" v-if="row.type">
            <el-tag size="small" effect="plain">{{ row.type }}</el-tag>
            <span class="amount">{{ fmtAmount(row.contractAmount) }}</span>
          </div>
          <div class="progress-row">
            <div class="progress-label">
              <span>整体进度</span>
              <span class="pct">{{ row.progress || 0 }}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: (row.progress || 0) + '%' }"></div>
            </div>
          </div>
          <div class="p-dates">
            <div class="d"><div class="l">开始</div><div class="v">{{ fmtDate(row.startDate) }}</div></div>
            <div class="d"><div class="l">截止</div><div class="v">{{ fmtDate(row.endDate) }}</div></div>
            <div class="d">
              <div class="l">剩余</div>
              <div class="v" :class="{ 'danger': (daysLeft(row.endDate) || 0) < 30 && (daysLeft(row.endDate) || 0) > 0 }">
                {{ daysLeft(row.endDate) !== null ? daysLeft(row.endDate) + ' 天' : '—' }}
              </div>
            </div>
          </div>
          <div class="p-foot">
            <div class="p-manager">
              <el-avatar :size="22">{{ (row.managerName || '?').slice(0, 1) }}</el-avatar>
              <span style="margin-left: 6px; font-size: 12px;">{{ row.managerName || '未分配' }}</span>
            </div>
            <div class="p-actions">
              <el-button type="primary" link size="small" @click.stop="gotoDetail(row)">查看</el-button>
            </div>
          </div>
        </div>
        <el-empty v-if="!loading && list.length === 0" description="暂无项目数据" style="grid-column: 1 / -1;" />
      </div>

      <el-pagination
        v-model:current-page="query.page"
        :page-size="query.pageSize"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        :page-sizes="[6, 12, 24]"
        class="pager"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.pager { margin-top: 20px; justify-content: flex-end; }

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 18px;
}

.project-card {
  position: relative;
  background: #fff;
  border: 1px solid var(--color-border, #E4E7ED);
  border-radius: var(--radius-lg, 14px);
  padding: 22px 20px;
  cursor: pointer;
  transition: all 0.2s;
  overflow: hidden;
  &::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    background: linear-gradient(135deg, #4F6BFF, #7C3AED);
  }
  &.warning::before { background: linear-gradient(135deg, #F59E0B, #EF4444); }
  &.success::before { background: linear-gradient(135deg, #10B981, #059669); }
  &.paused::before { background: linear-gradient(135deg, #94A3B8, #64748B); }
  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
  }
}
.p-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.p-id {
  font-family: var(--font-mono, 'SF Mono', monospace);
  font-size: 11px;
  color: #94A3B8;
  margin-bottom: 2px;
}
.p-name { margin: 0; font-size: 16px; font-weight: 600; color: #1E293B; }
.p-client { font-size: 13px; color: #475569; margin-bottom: 8px; .lbl { color: #94A3B8; } }
.p-type { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; .amount { font-family: var(--font-mono); font-weight: 600; color: var(--color-primary); font-size: 14px; } }
.progress-row { margin-bottom: 12px; }
.progress-label { display: flex; justify-content: space-between; font-size: 12px; color: #64748B; margin-bottom: 6px; .pct { font-weight: 600; color: #1E293B; } }
.progress-bar { height: 6px; background: #F1F5F9; border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(135deg, #4F6BFF, #7C3AED); border-radius: 3px; transition: width 0.3s; }
.project-card.warning .progress-fill { background: linear-gradient(135deg, #F59E0B, #EF4444); }
.project-card.success .progress-fill { background: linear-gradient(135deg, #10B981, #059669); }

.p-dates {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
  padding: 10px 0; border-top: 1px solid #F1F5F9; border-bottom: 1px solid #F1F5F9;
  margin-bottom: 12px;
  .d { text-align: center; .l { font-size: 11px; color: #94A3B8; } .v { font-size: 13px; font-weight: 500; color: #1E293B; margin-top: 2px; &.danger { color: var(--color-danger); } } }
}
.p-foot { display: flex; justify-content: space-between; align-items: center; }
.p-manager { display: flex; align-items: center; }
</style>
