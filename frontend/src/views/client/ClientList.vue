<script setup lang="ts">
/**
 * ClientList · 客户管理（统一风格：4 KPI + filter-chip + 手写 table + 自定义分页 + 批量删除）
 * 数据全部来自后端 /api/v1/common/clients + /clients/stats
 */
import { ref, computed, onMounted, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiFilterDialog from '@/components/ai/AiFilterDialog.vue'
import { clientApi, type Client, type ClientListStats } from '@/api/client'
import { http } from '@/utils/request'
import { exportCsv } from '@/utils/export'

const router = useRouter()

// 触点 #22：AI 智能筛选
const aiFilterVisible = ref(false)

// 客户等级映射：A/B/C/D → VIP/金牌/银牌/普通
const LEVEL_META: Record<string, { label: string; tag: string }> = {
  A: { label: 'VIP',  tag: 'tag-warning' },
  B: { label: '金牌', tag: 'tag-warning' },
  C: { label: '银牌', tag: 'tag-info' },
  D: { label: '普通', tag: 'tag-gray' },
}
function levelLabel(level?: string) {
  return LEVEL_META[level || 'D']?.label || '普通'
}
function levelTag(level?: string) {
  return LEVEL_META[level || 'D']?.tag || 'tag-gray'
}

// 筛选 filter-chip
const activeLevel = ref<string>('all')
const query = reactive({ keyword: '' })
// 是否包含已停用客户（软删后 is_active=False）。默认不显示，避免"删不掉"的体感
const includeInactive = ref(false)

// 列表 / 统计 / 分页
const rows = ref<Client[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const stats = ref<ClientListStats>({
  total: 0, active: 0, vip: 0, newThisMonth: 0, contractAmount: 0, contractCount: 0,
})

// 多选 / 批量删除
const selectedIds = ref<Set<number>>(new Set())
const batchDeleting = ref(false)
const isAllSelected = computed(() => {
  const list = filtered.value
  return list.length > 0 && list.every(r => selectedIds.value.has(r.id))
})
const isPartialSelected = computed(() => {
  const list = filtered.value
  return list.some(r => selectedIds.value.has(r.id)) && !isAllSelected.value
})
function toggleSelectAll() {
  const list = filtered.value
  if (isAllSelected.value) {
    list.forEach(r => selectedIds.value.delete(r.id))
  } else {
    list.forEach(r => selectedIds.value.add(r.id))
  }
  // 触发响应式
  selectedIds.value = new Set(selectedIds.value)
}
function toggleSelectOne(id: number) {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
  selectedIds.value = new Set(selectedIds.value)
}

// 4 个等级 filter-chip（A/B/C/D + all）
const levels = computed(() => {
  const c = { A: 0, B: 0, C: 0, D: 0 }
  rows.value.forEach(r => { if (c[r.level as keyof typeof c] !== undefined) c[r.level as keyof typeof c]++ })
  return [
    { key: 'all', label: '全部', count: rows.value.length },
    { key: 'A',   label: 'VIP',  count: c.A },
    { key: 'B',   label: '金牌', count: c.B },
    { key: 'C',   label: '银牌', count: c.C },
    { key: 'D',   label: '普通', count: c.D },
  ]
})

// 过滤后的列表
const filtered = computed(() => {
  if (activeLevel.value === 'all') return rows.value
  return rows.value.filter(r => r.level === activeLevel.value)
})

// AI 筛选结果（接 AiFilterDialog 的 apply 事件）
const aiFilter = ref<{ keyword?: string; level?: string; industry?: string } | null>(null)

/** AI 筛选应用：把 payload 合并进查询参数并刷新 */
async function onAiFilterApply(payload: { keyword?: string; status?: string; type?: string; level?: string; industry?: string }) {
  aiFilter.value = {
    keyword: payload.keyword || undefined,
    level: payload.level || undefined,
    industry: payload.industry || undefined,
  }
  if (payload.keyword) query.keyword = payload.keyword
  page.value = 1
  await loadList()
  if (rows.value.length === 0) {
    ElMessage.warning('AI 筛选无结果，请调整条件')
  } else {
    ElMessage.success(`✨ AI 筛选已应用（命中 ${rows.value.length} 条）`)
  }
}

// ===== 导出 =====
const exporting = ref(false)
function levelLabelForExport(l?: string) {
  return { A: 'VIP 战略', B: '金牌', C: '银牌', D: '普通' }[l || 'D'] || '普通'
}

function buildExportRows(list: any[]): any[] {
  return list.map((r: any) => ({
    code: r.code,
    name: r.name,
    shortName: r.shortName || '',
    taxNo: r.taxNo || '',
    legalPerson: r.legalPerson || '',
    contactName: r.contactName || '',
    contactPhone: r.contactPhone || '',
    contactEmail: r.contactEmail || '',
    industry: r.industry || '',
    level: levelLabelForExport(r.level),
    levelCode: r.level || '',
    isActive: r.isActive ? '启用' : '停用',
    contractAmount: r.contractAmount ?? 0,
    contractCount: r.contractCount ?? 0,
    address: r.address || '',
    bankName: r.bankName || '',
    bankAccount: r.bankAccount || '',
    remark: r.remark || '',
    createdAt: (r.createdAt || '').slice(0, 19).replace('T', ' '),
  }))
}

const exportColumns = [
  { label: '客户编号',     key: 'code' },
  { label: '客户名称',     key: 'name' },
  { label: '客户简称',     key: 'shortName' },
  { label: '纳税人识别号', key: 'taxNo' },
  { label: '法定代表人',   key: 'legalPerson' },
  { label: '联系人',       key: 'contactName' },
  { label: '联系电话',     key: 'contactPhone' },
  { label: '邮箱',         key: 'contactEmail' },
  { label: '所属行业',     key: 'industry' },
  { label: '客户等级',     key: 'level' },
  { label: '等级编码',     key: 'levelCode' },
  { label: '状态',         key: 'isActive' },
  { label: '合同金额(元)', key: 'contractAmount' },
  { label: '合同数',       key: 'contractCount' },
  { label: '地址',         key: 'address' },
  { label: '开户银行',     key: 'bankName' },
  { label: '银行账号',     key: 'bankAccount' },
  { label: '备注',         key: 'remark' },
  { label: '创建时间',     key: 'createdAt' },
]

/** 当前显示条件（包含 AI 筛选 + 关键字 + 等级 chip + 停用开关） */
function currentQueryParams(): any {
  const params: any = {
    keyword: query.keyword,
    includeInactive: includeInactive.value,
  }
  if (aiFilter.value?.level) params.level = aiFilter.value.level
  if (aiFilter.value?.industry) params.industry = aiFilter.value.industry
  if (activeLevel.value !== 'all') params.level = activeLevel.value
  return params
}

async function exportCurrentPage() {
  if (exporting.value) return
  exporting.value = true
  try {
    const rows = buildExportRows(rows.value)
    if (rows.length === 0) { ElMessage.warning('当前页无数据可导出'); return }
    const stamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')
    exportCsv(`客户列表_当前页_${stamp}.csv`, rows, exportColumns)
    ElMessage.success(`已导出当前页 ${rows.length} 条`)
  } finally {
    exporting.value = false
  }
}

async function exportAll() {
  if (exporting.value) return
  exporting.value = true
  try {
    // 后端 pageSize 限 100（le=100），分页拉全部
    const baseParams = currentQueryParams()
    const pageSize = 100
    const all: any[] = []
    for (let p = 1; p <= 50; p++) {
      const res: any = await clientApi.list({ ...baseParams, page: p, pageSize })
      const list = res?.list || []
      all.push(...list)
      const total = res?.total || 0
      if (list.length < pageSize || all.length >= total) break
    }
    if (all.length === 0) { ElMessage.warning('当前条件下无数据可导出'); return }
    const rows = buildExportRows(all)
    const stamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')
    exportCsv(`客户列表_全部_${rows.length}条_${stamp}.csv`, rows, exportColumns)
    ElMessage.success(`已导出全部 ${rows.length} 条`)
  } catch (e: any) {
    ElMessage.error('导出失败：' + (e?.response?.data?.message || e?.message || '未知错误'))
  } finally {
    exporting.value = false
  }
}

// ===== KPI 口径切换 =====
/** 客户总数卡的统计口径：'all' = 全部客户（含停用），'active' = 仅启用 */
const kpiScope = ref<'all' | 'active'>('all')
function toggleKpiScope() { kpiScope.value = kpiScope.value === 'all' ? 'active' : 'all' }
const kpiTotal = computed(() => kpiScope.value === 'all' ? (stats.value.totalAll ?? stats.value.total) : (stats.value.totalActive ?? stats.value.active))
const kpiTotalLabel = computed(() => kpiScope.value === 'all' ? '全部客户' : '活跃客户')
const kpiTotalHint = computed(() => {
  const inactive = stats.value.inactive ?? 0
  if (kpiScope.value === 'all') {
    return inactive > 0 ? `含 ${inactive} 个已停用` : '全部启用'
  }
  return '仅启用客户'
})
const kpiVip = computed(() => {
  // 全部口径下展示"全部 VIP"= 包含停用；活跃口径下=stats.vip（已过滤）
  // 后端 stats.vip 是 level='A' AND is_active=True，所以两个口径都只算启用的
  // 我们这里不去重查 DB，沿用后端 stats.vip 即可
  return stats.value.vip
})
const kpiVipHint = computed(() => {
  return kpiScope.value === 'all'
    ? (stats.value.inactive && stats.value.inactive > 0 ? '含 A 级已停用请看详情' : 'A 级战略合作')
    : 'A 级且启用'
})
const kpiActive = computed(() => stats.value.active)
const kpiActiveHint = computed(() => {
  const inactive = stats.value.inactive ?? 0
  if (kpiScope.value === 'all') {
    return inactive > 0 ? `${stats.value.active} 启用 / ${inactive} 停用` : '全部启用'
  }
  return '已启用档案'
})

function clearAiFilter() {
  aiFilter.value = null
  page.value = 1
  loadList()
  ElMessage.info('已清除 AI 筛选')
}

// 加载列表
async function loadList() {
  loading.value = true
  try {
    const params: any = {
      page: page.value,
      pageSize: pageSize.value,
      keyword: query.keyword,
      includeInactive: includeInactive.value,
    }
    if (aiFilter.value?.level) params.level = aiFilter.value.level
    if (aiFilter.value?.industry) params.industry = aiFilter.value.industry
    const res = await clientApi.list(params)
    rows.value = res.list || []
    total.value = res.total || 0
    // 清掉已不存在于新列表中的选中项
    const validIds = new Set(rows.value.map(r => r.id))
    const newSelected = new Set<number>()
    selectedIds.value.forEach(id => { if (validIds.has(id)) newSelected.add(id) })
    selectedIds.value = newSelected
  } catch (e: any) {
    ElMessage.error('客户列表加载失败：' + (e?.message || '未知错误'))
    rows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// 加载统计
async function loadStats() {
  try {
    stats.value = await clientApi.stats()
  } catch (e: any) {
    console.warn('统计卡加载失败', e)
  }
}

function fmtAmount(n: number) {
  if (!n) return '¥ 0'
  if (n >= 10000) return '¥ ' + (n / 10000).toFixed(1) + '万'
  return '¥ ' + Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function gotoDetail(r: Client) {
  router.push({ path: `/client/${r.id}` })
}

function gotoCreate(editId?: number) {
  if (editId) {
    router.push({ path: '/client/create', query: { id: String(editId) } })
  } else {
    router.push({ path: '/client/create' })
  }
}

/** 单条删除：inline 二次确认（不依赖 window.confirm/ElMessageBox） */
const pendingDelete = ref<Client | null>(null)
function askDelete(r: Client) {
  if (!r || !r.id) {
    ElMessage.error('客户 ID 缺失，无法删除')
    return
  }
  pendingDelete.value = r
}
function cancelDelete() {
  pendingDelete.value = null
}
async function confirmDelete() {
  const r = pendingDelete.value
  if (!r) return
  pendingDelete.value = null
  try {
    const res: any = await http.post(
      '/common/clients/delete',
      {},
      { params: { clientId: r.id }, silent: true }
    )
    console.log('[ClientList] delete response', res)
    ElMessage.success(`已删除「${r.name}」`)
    await Promise.all([loadList(), loadStats()])
  } catch (e: any) {
    console.error('[ClientList] delete error', e)
    const msg = e?.response?.data?.message || e?.message || '未知错误'
    ElMessage.error('删除失败：' + msg)
  }
}

/** 批量删除：inline 二次确认 */
const pendingBatchDelete = ref(false)
function askBatchDelete() {
  const ids = Array.from(selectedIds.value)
  if (ids.length === 0) {
    ElMessage.warning('请先勾选要删除的客户')
    return
  }
  pendingBatchDelete.value = true
}
function cancelBatchDelete() {
  pendingBatchDelete.value = false
}
async function confirmBatchDelete() {
  const ids = Array.from(selectedIds.value)
  pendingBatchDelete.value = false
  if (ids.length === 0) return
  batchDeleting.value = true
  let success = 0
  const failed: { id: number; name: string; reason: string }[] = []
  for (const id of ids) {
    const r = rows.value.find(x => x.id === id)
    try {
      await http.post(
        '/common/clients/delete',
        {},
        { params: { clientId: id }, silent: true }
      )
      success++
    } catch (e: any) {
      const reason = e?.response?.data?.message || e?.message || '未知错误'
      failed.push({ id, name: r?.name || `#${id}`, reason })
    }
  }

  // 批量结果提示（不阻断主流程）
  if (failed.length === 0) {
    ElMessage.success(`已删除 ${success} 位客户`)
  } else {
    ElMessage.warning(`成功 ${success}，失败 ${failed.length}`)
  }
}


function changePage(p: number) {
  page.value = p
  loadList()
}

// 搜索时重置到第 1 页
let searchTimer: number | undefined
watch(() => query.keyword, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    page.value = 1
    loadList()
  }, 350)
})

// 切换"包含已停用"时重新拉数据
watch(includeInactive, () => {
  page.value = 1
  loadList()
})

onMounted(() => {
  loadList()
  loadStats()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>客户管理</h1>
        <p class="page-desc">客户档案与关系管理 · 当前共 {{ total }} 位客户</p>
      </div>
      <div style="display: flex; gap: 8px">
        <button class="btn btn-outline btn-sm" @click="loadList">⟳ 刷新</button>
        <button class="btn btn-primary btn-sm" @click="gotoCreate()">+ 新建客户</button>
      </div>
    </div>

    <!-- 4 KPI + 顶部“全部/活跃”切换 -->
    <div class="kpi-scope-bar" style="display:flex;align-items:center;gap:8px;margin-bottom:10px;font-size:12px;color:#64748B">
      <span>统计口径：</span>
      <a href="javascript:void(0)"
         :class="['scope-chip', { active: kpiScope === 'all' }]"
         @click="kpiScope = 'all'">全部客户（含停用）</a>
      <a href="javascript:void(0)"
         :class="['scope-chip', { active: kpiScope === 'active' }]"
         @click="kpiScope = 'active'">仅活跃</a>
      <span v-if="(stats.inactive ?? 0) > 0" style="color:#94A3B8;margin-left:6px">· 含 {{ stats.inactive }} 个已停用</span>
    </div>
    <div class="kpi-row">
      <div class="stat-card">
        <div class="stat-label">{{ kpiTotalLabel }} <span class="stat-icon" :style="{ background: 'rgba(79,107,255,0.12)', color: '#4F6BFF' }">▤</span></div>
        <div class="stat-value">{{ kpiTotal }}<span class="unit">位</span></div>
        <div class="stat-delta" :class="{ 'delta-warn': kpiScope === 'all' && (stats.inactive ?? 0) > 0 }">{{ kpiTotalHint }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">VIP 客户 <span class="stat-icon" :style="{ background: 'rgba(245,158,11,0.12)', color: '#F59E0B' }">★</span></div>
        <div class="stat-value">{{ kpiVip }}<span class="unit">位</span></div>
        <div class="stat-delta">{{ kpiVipHint }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">活跃客户 <span class="stat-icon" :style="{ background: 'rgba(16,185,129,0.12)', color: '#10B981' }">✓</span></div>
        <div class="stat-value">{{ kpiActive }}<span class="unit">位</span></div>
        <div class="stat-delta">{{ kpiActiveHint }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">合同总金额 <span class="stat-icon" :style="{ background: 'rgba(124,58,237,0.12)', color: '#7C3AED' }">¥</span></div>
        <div class="stat-value">{{ fmtAmount(stats.contractAmount) }}</div>
        <div class="stat-delta">共 {{ stats.contractCount }} 份合同</div>
      </div>
    </div>

    <!-- 等级 filter-chip -->
    <div class="filter-bar" style="margin-bottom: 16px">
      <a v-for="t in levels" :key="t.key" href="javascript:void(0)"
         :class="['filter-chip', { active: activeLevel === t.key }]"
         @click="activeLevel = t.key">
        {{ t.label }} ({{ t.count }})
      </a>
    </div>

    <!-- 客户表 -->
    <div class="page-card">
      <div class="card-head-row">
        <h3>客户列表</h3>
        <div class="toolbar">
          <input v-model="query.keyword" class="search-input" placeholder="搜索客户名称 / 编号 / 联系人..." />
          <label class="toggle-inline" style="display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#475569;cursor:pointer;user-select:none">
            <input type="checkbox" v-model="includeInactive" />
            包含已停用
          </label>
          <span v-if="aiFilter && (aiFilter.level || aiFilter.industry)" style="display:inline-flex;align-items:center;gap:6px;font-size:12px;color:#7C3AED;background:rgba(124,58,237,0.08);border:1px solid rgba(124,58,237,0.25);padding:3px 10px;border-radius:999px">
            ✨ AI：
            <span v-if="aiFilter.level">等级={{ levelLabel(aiFilter.level) }}</span>
            <span v-if="aiFilter.industry">行业={{ aiFilter.industry }}</span>
            <a style="cursor:pointer;color:#7C3AED;margin-left:4px" @click="clearAiFilter">清除</a>
          </span>
          <!-- 批量删除：选中 >0 时高亮显示 -->
          <button
            v-if="selectedIds.size > 0"
            class="btn btn-danger btn-sm"
            :disabled="batchDeleting"
            @click="askBatchDelete"
          >
            🗑 批量删除 ({{ selectedIds.size }})
          </button>
          <!-- 触点 #22：AI 智能筛选 -->
          <button class="btn-ai-outline" @click="aiFilterVisible = true">🤖 AI 智能筛选</button>
          <el-dropdown trigger="click" @command="(c: string) => c === 'page' ? exportCurrentPage() : exportAll()">
            <button class="btn btn-outline btn-sm" :disabled="exporting">
              ⬇ 导出 {{ exporting ? '...' : '' }}
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="page">导出当前页（{{ rows.length }} 条）</el-dropdown-item>
                <el-dropdown-item command="all">导出全部（按当前筛选条件）</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <button class="btn btn-outline btn-sm" @click="loadList">⟳ 刷新</button>
        </div>
      </div>

      <table class="ct-table">
        <thead>
          <tr>
            <th class="col-check">
              <label class="checkbox-wrap" :class="{ partial: isPartialSelected, checked: isAllSelected }">
                <input type="checkbox"
                  :checked="isAllSelected"
                  :indeterminate="isPartialSelected"
                  @change="toggleSelectAll" />
                <span class="checkbox-box"></span>
              </label>
            </th>
            <th>客户编号</th>
            <th>客户名称</th>
            <th>联系人</th>
            <th>电话</th>
            <th>行业</th>
            <th>等级</th>
            <th style="text-align: right;">合同金额</th>
            <th>合同数</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="11" style="text-align:center; padding: 32px; color:#94A3B8">加载中...</td>
          </tr>
          <tr v-else-if="filtered.length === 0">
            <td colspan="11" style="text-align:center; padding: 32px; color:#94A3B8">暂无客户数据</td>
          </tr>
          <tr v-for="r in filtered" :key="r.id" :class="{ 'row-selected': selectedIds.has(r.id) }">
            <td class="col-check">
              <label class="checkbox-wrap" :class="{ checked: selectedIds.has(r.id) }">
                <input type="checkbox"
                  :checked="selectedIds.has(r.id)"
                  @change="toggleSelectOne(r.id)" />
                <span class="checkbox-box"></span>
              </label>
            </td>
            <td><span class="cell-mono">{{ r.code }}</span></td>
            <td><span class="cell-name">{{ r.name }}</span></td>
            <td>{{ r.contactName || '—' }}</td>
            <td>{{ r.contactPhone || '—' }}</td>
            <td>{{ r.industry || '—' }}</td>
            <td><span :class="['tag', levelTag(r.level)]">★ {{ levelLabel(r.level) }}</span></td>
            <td class="cell-amount">{{ fmtAmount(r.totalAmount) }}</td>
            <td class="cell-num">{{ r.contractCount }}</td>
            <td>
              <span :class="['tag', r.isActive !== false ? 'tag-success' : 'tag-gray']">
                {{ r.isActive !== false ? '活跃' : '停用' }}
              </span>
            </td>
            <td class="cell-actions">
              <a @click="gotoDetail(r)">查看</a>
              <a @click="gotoCreate(r.id)">编辑</a>
              <a class="act-danger" @click="askDelete(r)">删除</a>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="rec-foot">
        <span class="rec-count">
          共 {{ total }} 位 · 已选 {{ selectedIds.size }} 位
        </span>
        <div class="pagination">
          <button class="btn btn-ghost btn-sm" :disabled="page <= 1" @click="changePage(page - 1)">‹</button>
          <button class="btn btn-primary btn-sm">{{ page }}</button>
          <button class="btn btn-ghost btn-sm" :disabled="page * pageSize >= total" @click="changePage(page + 1)">›</button>
        </div>
      </div>
    </div>
  </div>

  <!-- 触点 #22：AI 智能筛选 Drawer -->
  <AiFilterDialog v-model:visible="aiFilterVisible" scope="client" @apply="onAiFilterApply" />

  <!-- 单条删除确认弹框（不依赖 window.confirm/ElMessageBox） -->
  <div v-if="pendingDelete" class="confirm-mask" @click.self="cancelDelete">
    <div class="confirm-box">
      <div class="confirm-icon">⚠️</div>
      <h3>删除客户</h3>
      <p>确定删除客户「<strong>{{ pendingDelete.name }}</strong>」？<br/>此操作将停用该客户档案（软删除）。</p>
      <div class="confirm-actions">
        <button class="btn btn-outline btn-sm" @click="cancelDelete">取消</button>
        <button class="btn btn-danger btn-sm" @click="confirmDelete">确认删除</button>
      </div>
    </div>
  </div>

  <!-- 批量删除确认弹框 -->
  <div v-if="pendingBatchDelete" class="confirm-mask" @click.self="cancelBatchDelete">
    <div class="confirm-box">
      <div class="confirm-icon">⚠️</div>
      <h3>批量删除客户</h3>
      <p>确定批量删除已选中的 <strong>{{ selectedIds.size }}</strong> 位客户？<br/>此操作将停用这些客户档案（软删除）。</p>
      <div class="confirm-actions">
        <button class="btn btn-outline btn-sm" @click="cancelBatchDelete">取消</button>
        <button class="btn btn-danger btn-sm" @click="confirmBatchDelete">确认批量删除</button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-card { @include page-card; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }

// 4 KPI
.kpi-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-bottom: 24px;
  @media (max-width: 1100px) { grid-template-columns: repeat(2, 1fr); }
}
.stat-card {
  @include stat-card;
  .stat-label {
    font-size: 12.5px; color: $color-text-secondary;
    display: flex; justify-content: space-between; align-items: center;
    position: relative; z-index: 1;
  }
  .stat-icon {
    width: 32px; height: 32px; border-radius: 8px;
    display: grid; place-items: center; font-size: 16px; font-weight: 600;
  }
  .stat-value {
    font-size: 26px; font-weight: 700; color: $color-text-primary;
    font-family: $font-family-mono; margin: 6px 0;
    position: relative; z-index: 1;
    .unit { font-size: 13px; color: $color-text-tertiary; font-weight: 500; margin-left: 4px; font-family: -apple-system, sans-serif; }
  }
  .stat-delta { font-size: 12px; color: $color-text-tertiary; position: relative; z-index: 1; }
}

.filter-bar {
  display: flex; gap: 8px; flex-wrap: wrap; padding: 4px 0;
}
.filter-chip {
  padding: 6px 14px; border-radius: 9999px;
  font-size: 12.5px; color: $color-text-secondary;
  background: #fff; border: 1px solid $color-border;
  cursor: pointer; transition: all 0.15s; font-weight: 500;
  text-decoration: none;
  &:hover { border-color: $color-primary; color: $color-primary; }
  &.active { background: $gradient-brand; color: #fff; border-color: transparent; }
}

.card-head-row {
  display: flex; justify-content: space-between; align-items: center; padding: 0 0 16px 0;
  h3 { font-size: 15px; font-weight: 600; margin: 0; }
  .toolbar { display: flex; gap: 8px; align-items: center; }
}
.search-input {
  height: 32px; padding: 0 12px; border: 1px solid $color-border; border-radius: $radius-md;
  font-size: 12px; background: #fff; width: 260px;
  &:focus { outline: none; border-color: $color-primary; }
}

.ct-table {
  width: 100%; border-collapse: collapse; font-size: 13.5px;
  th {
    background: #F8FAFC; text-align: left; padding: 12px 16px;
    font-size: 12px; font-weight: 600; color: $color-text-secondary;
    text-transform: uppercase; letter-spacing: 0.5px;
    border-bottom: 1px solid $color-border;
  }
  td { padding: 14px 16px; border-bottom: 1px solid $color-border; color: $color-text-primary; }
  tr:last-child td { border-bottom: none; }
  tr:hover { background: #F8FAFC; }
  tr.row-selected { background: rgba(79, 107, 255, 0.04); }
  .cell-mono { font-family: $font-family-mono; color: $color-primary; font-weight: 500; }
  .cell-name { font-weight: 500; color: $color-text-primary; }
  .cell-amount { font-weight: 600; text-align: right; }
  .cell-num { text-align: center; font-family: $font-family-mono; color: $color-text-secondary; }
  .cell-actions { display: flex; gap: 10px; }
  .cell-actions a {
    color: $color-primary; font-size: 12.5px; font-weight: 500;
    padding: 4px 8px; border-radius: $radius-sm; cursor: pointer;
    &:hover { background: $color-primary-bg; }
  }
  .cell-actions a.act-danger {
    color: #EF4444;
    &:hover { background: #FEF2F2; }
  }
  .col-check { width: 44px; text-align: center; padding-left: 12px; padding-right: 0; }
}

// 自定义复选框（避免 Element Plus 全局样式影响）
.checkbox-wrap {
  display: inline-flex; align-items: center; justify-content: center;
  cursor: pointer; position: relative;
  input[type="checkbox"] {
    position: absolute; opacity: 0; width: 0; height: 0;
  }
  .checkbox-box {
    width: 16px; height: 16px;
    border: 1.5px solid #CBD5E1; border-radius: 3px;
    background: #fff; transition: all 0.15s;
    position: relative; display: inline-block;
  }
  &.checked .checkbox-box {
    background: #4F6BFF; border-color: #4F6BFF;
    &::after {
      content: ''; position: absolute;
      left: 4px; top: 1px; width: 4px; height: 8px;
      border: solid #fff; border-width: 0 2px 2px 0;
      transform: rotate(45deg);
    }
  }
  &.partial .checkbox-box {
    background: #4F6BFF; border-color: #4F6BFF;
    &::after {
      content: ''; position: absolute;
      left: 3px; top: 6px; width: 8px; height: 2px;
      background: #fff;
    }
  }
}

.kpi-scope-bar .scope-chip {
  display: inline-block; padding: 3px 12px; border-radius: 999px;
  border: 1px solid #E2E8F0; background: #fff; cursor: pointer;
  color: #475569; transition: all 0.15s;
  &.active { background: rgba(79,107,255,0.08); border-color: #4F6BFF; color: #4F6BFF; font-weight: 500; }
  &:hover { border-color: #4F6BFF; }
}
.stat-delta.delta-warn { color: #F59E0B; font-weight: 500; }

.tag {
  display: inline-flex; align-items: center; padding: 2px 10px;
  font-size: 12px; font-weight: 500; border-radius: 9999px;
  background: #F1F5F9; color: $color-text-secondary;
  &.tag-primary { background: #E0E6FF; color: #4F6BFF; }
  &.tag-success { background: #D1FAE5; color: #047857; }
  &.tag-warning { background: #FEF3C7; color: #B45309; }
  &.tag-info    { background: #CFFAFE; color: #0E7490; }
  &.tag-gray    { background: #F1F5F9; color: #475569; }
}

.rec-foot {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 0 0 0; margin-top: 12px; border-top: 1px solid $color-border;
  flex-wrap: wrap; gap: 8px;
  .rec-count { font-size: 12.5px; color: $color-text-tertiary; }
  .pagination { display: flex; gap: 4px; }
}

.btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500;
  border-radius: $radius-md; transition: all 0.15s;
  border: 1px solid transparent; cursor: pointer; font-family: inherit;
  &.btn-primary { background: $gradient-brand; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4); } }
  &.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover { border-color: $color-primary; color: $color-primary; } }
  &.btn-ghost { background: transparent; color: $color-text-secondary; &:hover { background: $color-primary-bg; color: $color-primary; } }
  &.btn-danger { background: #EF4444; color: #fff; border-color: #EF4444; &:hover { background: #DC2626; border-color: #DC2626; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3); } }
}

// inline 确认弹框（不依赖 Element Plus / window.confirm）
.confirm-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 9999;
}
.confirm-box {
  background: #fff; border-radius: 12px; padding: 28px 32px;
  min-width: 380px; max-width: 480px; box-shadow: 0 20px 60px rgba(0,0,0,0.25);
  text-align: center;
  .confirm-icon { font-size: 36px; margin-bottom: 8px; }
  h3 { font-size: 16px; font-weight: 600; margin: 0 0 12px 0; color: #1E293B; }
  p { font-size: 13.5px; color: #475569; line-height: 1.6; margin: 0 0 20px 0; }
  .confirm-actions { display: flex; gap: 8px; justify-content: center; }
  strong { color: #EF4444; }
  &.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}
</style>
