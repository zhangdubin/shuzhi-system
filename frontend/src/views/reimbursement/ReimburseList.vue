<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/expense/list')">业务</a>
          <span class="sep">/</span>
          <span class="current">报销中心</span>
        </div>
        <h1>🧾 报销中心</h1>
        <p class="page-desc">从销售费用生成报销单，打印 / 录入实际报销后自动回写费用状态</p>
      </div>
      <div class="page-actions">
        <el-button @click="loadData">↻ 刷新</el-button>
        <el-button type="primary" @click="router.push('/reimbursement/create')">+ 新建报销单</el-button>
      </div>
    </div>

    <!-- KPI -->
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">报销单数</div>
        <div class="kpi-value">{{ stats.total }}</div>
        <div class="kpi-delta">累计</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">草稿</div>
        <div class="kpi-value" style="color:#94A3B8">{{ stats.draft }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">已打印</div>
        <div class="kpi-value" style="color:#7C3AED">{{ stats.printed }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">已完成</div>
        <div class="kpi-value" style="color:#10B981">{{ stats.done }}</div>
      </div>
      <div class="kpi-card highlight">
        <div class="kpi-label">报销总金额</div>
        <div class="kpi-value">¥{{ fmtMoney(stats.totalAmount) }}</div>
        <div class="kpi-delta">实际报销</div>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="page-card filter-bar">
      <el-input v-model="filters.keyword" placeholder="搜索报销单号 / 标题" clearable style="width:260px" @keyup.enter="loadData" @clear="loadData" />
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width:140px" @change="loadData">
        <el-option label="草稿" value="draft" />
        <el-option label="已打印" value="printed" />
        <el-option label="已报销" value="reimbursed" />
        <el-option label="已完成" value="done" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-select v-model="filters.templateType" placeholder="全部模板" clearable style="width:160px" @change="loadData">
        <el-option v-for="t in templates" :key="t.code" :label="t.name" :value="t.code" />
      </el-select>
      <el-button @click="loadData">搜索</el-button>
    </div>

    <!-- 列表 -->
    <div class="page-card">
      <el-table :data="filtered" stripe>
        <el-table-column prop="formNo" label="报销单号" width="180">
          <template #default="{ row }">
            <a class="link" @click="gotoDetail(row)">{{ row.formNo }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="模板" width="120">
          <template #default="{ row }">{{ templateName(row.templateType) }}</template>
        </el-table-column>
        <el-table-column label="报销人" width="100">
          <template #default="{ row }">{{ row.applicant?.name || '—' }}</template>
        </el-table-column>
        <el-table-column label="费用笔数" width="80" align="center">
          <template #default="{ row }">{{ row.detailCount }}</template>
        </el-table-column>
        <el-table-column label="报销金额" width="120" align="right">
          <template #default="{ row }">
            <span class="money">¥{{ fmtMoney(row.totalAmount) }}</span>
            <div v-if="row.actualAmount > 0" class="actual">实报 ¥{{ fmtMoney(row.actualAmount) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="凭证号" width="140">
          <template #default="{ row }">{{ row.voucherNo || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span :class="['tag', statusClass(row.status)]">{{ row.statusLabel }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">{{ fmtDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <a class="act-link" @click="gotoDetail(row)">查看</a>
              <a v-if="row.status === 'draft'" class="act-link" @click="onEdit(row)">编辑</a>
              <a v-if="row.status !== 'done'" class="act-link act-danger" @click="onDelete(row)">删除</a>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!loading && filtered.length === 0" class="empty">
        暂无报销单，<a class="link" @click="router.push('/reimbursement/create')">立即创建</a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reimburseApi } from '@/api/modules'

const router = useRouter()
const loading = ref(false)
const list = ref<any[]>([])
const templates = ref<any[]>([])

const filters = reactive({
  keyword: '',
  status: '',
  templateType: '',
})

const filtered = computed(() => {
  // 已经在后端做分页，但前端也兜底筛
  return list.value
})

const stats = computed(() => {
  const draft = list.value.filter(x => x.status === 'draft').length
  const printed = list.value.filter(x => x.status === 'printed').length
  const done = list.value.filter(x => x.status === 'done').length
  const totalAmount = list.value.reduce((s, x) => s + (x.actualAmount || x.totalAmount || 0), 0)
  return { total: list.value.length, draft, printed, done, totalAmount }
})

function templateName(code: string) {
  return templates.value.find(t => t.code === code)?.name || code
}

function statusClass(s: string) {
  return {
    draft: 'tag-info', printed: 'tag-warning', reimbursed: 'tag-primary',
    done: 'tag-success', cancelled: 'tag-danger',
  }[s] || 'tag-info'
}

function fmtMoney(v: number) { return ((v || 0) / 100).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function fmtDate(s?: string) { return s ? s.substring(0, 16).replace('T', ' ') : '—' }

async function loadData() {
  loading.value = true
  try {
    const r: any = await reimburseApi.list({ page: 1, pageSize: 50, keyword: filters.keyword, filters: { status: filters.status, templateType: filters.templateType } })
    list.value = r?.list || r?.data?.list || []
  } catch (e: any) {
    ElMessage.error('加载失败：' + (e?.message || ''))
  } finally {
    loading.value = false
  }
}

async function loadTemplates() {
  try {
    const r: any = await reimburseApi.templates()
    templates.value = r || r?.data || []
  } catch (e) {
    console.warn('templates load failed', e)
  }
}

async function onDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除报销单「${row.formNo}」？删除后关联费用将恢复未报销状态。`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await reimburseApi.delete(row.formId)
    ElMessage.success('已删除')
    loadData()
  } catch (e: any) {
    ElMessage.error('删除失败：' + (e?.message || ''))
  }
}

function onEdit(row: any) {
  ElMessage.info('编辑功能请在详情页操作（暂未提供独立编辑页）')
  router.push(`/reimbursement/${row.formId}`)
}

function gotoDetail(row: any) {
  router.push(`/reimbursement/${row.formId}`)
}

onMounted(() => {
  loadTemplates()
  loadData()
})
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.page-header .breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-primary; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-header .page-actions { display: flex; gap: 8px; }
.row-actions { display: flex; align-items: center; gap: 10px; }
.row-actions .act-link { color: var(--brand-500, #4F6BFF); cursor: pointer; font-size: 13px; white-space: nowrap; }
.row-actions .act-link:hover { opacity: 0.75; }
.row-actions .act-link.act-danger { color: #EF4444; }

.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card {
  background: #fff; border: 1px solid $color-border; border-radius: $radius-lg;
  padding: 16px 20px;
  .kpi-label { font-size: 12px; color: $color-text-tertiary; }
  .kpi-value { font-size: 26px; font-weight: 700; color: $color-text-primary; margin: 4px 0 2px; }
  .kpi-delta { font-size: 11px; color: $color-text-tertiary; }
  &.highlight { background: linear-gradient(135deg, #4F6BFF08, #7C3AED08); border-color: rgba(79,107,255,0.2); }
}

.filter-bar { display: flex; gap: 8px; align-items: center; padding: 14px 16px; margin-bottom: 12px; }
.page-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: 16px; margin-bottom: 12px; }

.link { color: $color-primary; cursor: pointer; }
.link:hover { text-decoration: underline; }
.money { font-weight: 600; color: #DC2626; }
.actual { font-size: 11px; color: $color-text-tertiary; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.tag-success { background: rgba(16,185,129,0.1); color: #10B981; }
.tag-warning { background: rgba(245,158,11,0.1); color: #F59E0B; }
.tag-primary { background: rgba(79,107,255,0.1); color: #4F6BFF; }
.tag-info    { background: rgba(148,163,184,0.15); color: #64748B; }
.tag-danger  { background: rgba(239,68,68,0.1);  color: #EF4444; }
.empty { padding: 40px; text-align: center; color: $color-text-tertiary; }
</style>
