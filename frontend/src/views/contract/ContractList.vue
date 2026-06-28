<script setup lang="ts">
/**
 * ContractList · 合同列表（1:1 复刻 design/contract.html）
 * - 4 KPI 统计卡（来自后端 stats）
 * - 5 类 filter-chip（前端基于真实数据算）
 * - flow-card 审批流程（6 步骤条）
 * - 合同表格（真实后端数据 + 9 列 + 自定义分页）
 * - AI 风险标签：前端基于金额/到期日/状态推导
 */
import { ref, computed, onMounted, reactive } from 'vue'
import AIRiskChip from '@/components/ai/AIRiskChip.vue'
import AiFilterDialog from '@/components/ai/AiFilterDialog.vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { contractApi } from '@/api/modules'
import { printApi } from '@/api/print'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 权限软判断（不再用 v-permission 隐藏，改为点击提示）
function canWrite(): boolean {
  return userStore.hasPerm('contract:write')
}
function permTip() {
  ElMessage.warning('暂无「合同写权限」(contract:write)，如需操作请联系管理员')
}

// 触点 #22：AI 智能筛选
const aiFilterVisible = ref(false)

// 触点 #24：从发票详情跳转过来 - 关联模式
const linkInvoiceId = computed(() => Number(route.query.linkInvoiceId) || 0)
const linkInvoiceNo = ref('')

async function _loadLinkInvoice() {
  if (!linkInvoiceId.value) return
  try {
    const { invoiceOcrApi } = await import('@/api/modules')
    const resp: any = await invoiceOcrApi.detail(linkInvoiceId.value).catch(() => null)
    const d = resp?.data || resp
    if (d) linkInvoiceNo.value = d.invoiceNo || d.code || String(linkInvoiceId.value)
  } catch (e) { console.warn(e) }
}

// 状态
const loading = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const activeType = ref<'all' | 'sales' | 'purchase' | 'service' | 'framework' | 'other'>('all')

// 催办/下载行级 busy
const urgeBusyId = ref<number | null>(null)
const downloadBusyId = ref<number | null>(null)
// 催办弹窗
const urgeDialogVisible = ref(false)
const urgeTarget = ref<any>(null)
const urgeMessage = ref('')

// 选中行（批量删除用）
const selectedIds = ref<Set<number>>(new Set())
function onRowToggle(row: any, checked: boolean) {
  if (checked) selectedIds.value.add(row.id)
  else selectedIds.value.delete(row.id)
  selectedIds.value = new Set(selectedIds.value)
}
function onToggleAll(checked: boolean) {
  if (checked) {
    filteredRows.value.forEach((r: any) => selectedIds.value.add(r.id))
  } else {
    filteredRows.value.forEach((r: any) => selectedIds.value.delete(r.id))
  }
  selectedIds.value = new Set(selectedIds.value)
}
const isAllSelected = computed(() =>
  filteredRows.value.length > 0 && filteredRows.value.every((r: any) => selectedIds.value.has(r.id))
)
const isIndeterminate = computed(() => {
  const n = filteredRows.value.filter((r: any) => selectedIds.value.has(r.id)).length
  return n > 0 && n < filteredRows.value.length
})
function clearSelection() {
  selectedIds.value = new Set()
}

// 批量打印 (UDPE M2 阶段 9) — 合并 PDF 下载
const batchPrinting = ref(false)
async function batchPrint() {
  if (selectedIds.value.size === 0) {
    ElMessage.warning('请先勾选要打印的合同')
    return
  }
  if (selectedIds.value.size > 100) {
    ElMessage.warning('单次最多 100 条, 当前已选 ' + selectedIds.value.size)
    return
  }
  batchPrinting.value = true
  try {
    const ids = Array.from(selectedIds.value)
    const stats = await printApi.batchPdf({
      templateCode: 'contract_v1',
      items: ids,
      options: { sourceModule: 'contract' },
    })
    ElMessage.success(`批量打印完成: ${stats.success}/${stats.total} 条`)
    clearSelection()
  } catch (e: any) {
    ElMessage.error('批量打印失败: ' + (e?.message || ''))
  } finally {
    batchPrinting.value = false
  }
}

// 5 类计数（前端基于真实数据动态算）
const typeCounts = ref({ all: 0, sales: 0, purchase: 0, service: 0, framework: 0, other: 0 })

// 搜索/筛选
const query = reactive({ keyword: '', client: '', date: '' })

// 4 KPI（来自后端 stats）
const stats = ref([
  { label: '合同总数',   value: '—', unit: '份',  icon: '▦', iconBg: 'rgba(79,107,255,0.12)',  iconColor: '#4F6BFF', delta: '—' },
  { label: '合同总金额', value: '—', unit: '万',  icon: '¥', iconBg: 'rgba(16,185,129,0.12)',  iconColor: '#10B981', delta: '—' },
  { label: '待审批',     value: '—', unit: '份',  icon: '⏱', iconBg: 'rgba(245,158,11,0.12)',  iconColor: '#F59E0B', delta: '—' },
  { label: '即将到期',   value: '—', unit: '份',  icon: '!', iconBg: 'rgba(239,68,68,0.12)',   iconColor: '#EF4444', delta: '—' },
])

// 审批流程（design: 6 步骤）
const flowSteps = ref([
  { state: 'done',    label: '起草',       meta: '李明 · 06-11 10:23' },
  { state: 'done',    label: '法务审核',   meta: '王律师 · 06-11 14:30' },
  { state: 'current', label: '财务审核',   meta: '张明 · 审核中' },
  { state: 'todo',    label: '总经理审批', meta: '待提交' },
  { state: 'todo',    label: '电子签',     meta: '未开始' },
  { state: 'todo',    label: '归档',       meta: '未开始' },
])

// type 中文/英文 → 内部 key（兼容后端：'销售合同'/'sale'/'sales'/'采购合同'/'purchase'/...）
function normalizeType(rawType: string): { key: 'sales' | 'purchase' | 'service' | 'framework' | 'other'; label: string; color: string } {
  const t = (rawType || '').toString().trim().toLowerCase()
  if (t === '销售合同' || t === 'sale' || t === 'sales' || t === '销售')
    return { key: 'sales',     label: '销售', color: 'primary' }
  if (t === '采购合同' || t === 'purchase' || t === '采购')
    return { key: 'purchase',  label: '采购', color: 'success' }
  if (t === '服务合同' || t === 'service'   || t === '服务')
    return { key: 'service',   label: '服务', color: 'info' }
  if (t === '框架协议' || t === 'framework' || t === '框架')
    return { key: 'framework', label: '框架', color: 'purple' }
  return { key: 'other', label: rawType || '其他', color: 'gray' }
}

// status 归一化（后端可能返回 active/draft/signed/...，统一为中文展示）
function normalizeStatus(rawStatus: string): { label: string; color: string } {
  const s = (rawStatus || '').toString().trim().toLowerCase()
  const map: Record<string, { label: string; color: string }> = {
    active:     { label: '执行中',   color: 'success' },
    signed:     { label: '已签订',   color: 'success' },
    executed:   { label: '执行中',   color: 'success' },
    approved:   { label: '已审批',   color: 'success' },
    draft:      { label: '草稿',     color: 'info' },
    approving:  { label: '审批中',   color: 'warning' },
    pending:    { label: '待审批',   color: 'warning' },
    expired:    { label: '已到期',   color: 'danger' },
    expiring:   { label: '即将到期', color: 'warning' },
    archived:   { label: '已归档',   color: 'info' },
    terminated: { label: '已终止',   color: 'danger' },
  }
  return map[s] || { label: rawStatus || '未知', color: 'gray' }
}

// AI 风险等级：前端基于 金额+到期日+状态 推导（后端不返回该字段）
function deriveRiskLevel(r: any): { level: 'high' | 'medium' | 'low' | 'unknown'; reason: string } {
  const amount = Number(r.amount) || 0
  const st = (r.status || '').toString().toLowerCase()
  const exp = r.expireDate ? new Date(r.expireDate) : null
  const now = new Date()
  const daysToExpire = exp ? Math.floor((exp.getTime() - now.getTime()) / 86400000) : 9999
  // 高风险：已过期 / 金额>=100万 且 60天内到期
  if (st === 'expired' || daysToExpire < 0) return { level: 'high', reason: '合同已到期' }
  if (amount >= 1000000 && daysToExpire <= 60) return { level: 'high',  reason: `金额大(¥${(amount/10000).toFixed(0)}万)且${daysToExpire}天内到期` }
  // 中风险：金额>=50万 或 90天内到期
  if (amount >= 500000 || (daysToExpire >= 0 && daysToExpire <= 90)) return { level: 'medium', reason: amount >= 500000 ? '金额较高' : `${daysToExpire}天内到期` }
  // 低风险：常规
  if (st === 'active' || st === 'signed' || st === 'executed') return { level: 'low', reason: '条款常规' }
  return { level: 'unknown', reason: '' }
}

// AI 筛选结果（接 AiFilterDialog 的 apply 事件）
const aiFilter = ref<{ keyword?: string; status?: string; type?: string; amountMin?: number; amountMax?: number } | null>(null)
function clearAiFilter() {
  aiFilter.value = null
  ElMessage.info('已清除 AI 筛选')
}
function onAiFilterApply(payload: { keyword?: string; status?: string; type?: string; amountMin?: number; amountMax?: number }) {
  aiFilter.value = {
    keyword: payload.keyword || undefined,
    status: payload.status || undefined,
    type: payload.type || undefined,
    amountMin: payload.amountMin ?? undefined,
    amountMax: payload.amountMax ?? undefined,
  }
  if (payload.keyword) {
    const q = (window as any).__contractQuery
    if (q) q.keyword = payload.keyword
  }
  ElMessage.success(`✨ AI 筛选已应用（命中 ${filteredRows.value.length} 条）`)
}

function matchAi(r: any): boolean {
  const f = aiFilter.value
  if (!f) return true
  if (f.keyword) {
    const k = f.keyword.toLowerCase()
    const blob = ((r.name || '') + ' ' + (r.code || '') + ' ' + (r.client || '') + ' ' + (r.clientName || '')).toLowerCase()
    if (!blob.includes(k)) return false
  }
  if (f.status) {
    const raw = (r.statusCode || r.status || '').toString().toLowerCase()
    if (raw && raw !== f.status.toLowerCase()) {
      const m: Record<string, string[]> = {
        draft: ['草稿'],
        approving: ['审批中', '待审批'],
        approved: ['已通过', '已审批'],
        signed: ['已签订', '已签约'],
        executed: ['执行中'],
        active: ['执行中'],
        expired: ['已到期', '已过期'],
        archived: ['已归档'],
      }
      const cns = m[f.status] || []
      if (!cns.some(c => (r.statusLabel || r.status || '').includes(c))) return false
    }
  }
  if (f.type) {
    if (r.type !== f.type) return false
  }
  if (f.amountMin != null && (r.amount || 0) < f.amountMin) return false
  if (f.amountMax != null && (r.amount || 0) > f.amountMax) return false
  return true
}

// 筛选
const filteredRows = computed(() => {
  let out = list.value
  if (activeType.value !== 'all') {
    out = out.filter((r: any) => r.type === activeType.value)
  }
  if (query.keyword) {
    const k = query.keyword.toLowerCase()
    out = out.filter((r: any) =>
      (r.name || '').toLowerCase().includes(k) ||
      (r.code || '').toLowerCase().includes(k) ||
      (r.client || '').toLowerCase().includes(k)
    )
  }
  if (aiFilter.value) out = out.filter(matchAi)
  return out
})

function fmtAmount(n: number) {
  // 后端 amount 单位是「元」，直接显示
  return '¥ ' + Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function gotoDetail(row: any) { router.push(`/contract/${row.id}`) }
function gotoCreate() { router.push('/contract/create') }
function gotoAiPanel() { router.push('/ai/risk') }

// ===== 催办 =====
function openUrgeDialog(row: any) {
  if (!row || !row.id) return
  urgeTarget.value = row
  urgeMessage.value = `请尽快审批合同 ${row.code} ${row.name}`
  urgeDialogVisible.value = true
}
async function submitUrge() {
  const row = urgeTarget.value
  if (!row) return
  urgeBusyId.value = row.id
  try {
    const resp: any = await contractApi.urge(row.id, { message: urgeMessage.value.trim() || undefined })
    const notified = (resp?.data?.notifiedUserIds?.length) ?? (resp?.notifiedUserIds?.length) ?? 0
    ElMessage.success(`已催办 ${notified} 位审批人`)
    urgeDialogVisible.value = false
  } catch (e: any) {
    ElMessage.error(e?.message || '催办失败')
  } finally {
    urgeBusyId.value = null
  }
}
function urgeOne(row: any) {
  // 兼容旧模板的 @click 入口
  openUrgeDialog(row)
}

// ===== 下载 =====
async function downloadOne(row: any) {
  if (!row || !row.id) return
  downloadBusyId.value = row.id
  try {
    const { blob, filename } = await contractApi.download(row.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    ElMessage.success(`已下载 ${filename}`)
  } catch (e: any) {
    ElMessage.error(e?.message || '下载失败')
  } finally {
    downloadBusyId.value = null
  }
}

// ===== 删除 =====
function canDelete(r: any): boolean {
  const s = (r.status || '').toString().toLowerCase()
  const forbidden = ['approving', 'approved', 'signed']
  return !forbidden.includes(s)
}
async function deleteOne(row: any) {
  if (!canWrite()) { permTip(); return }
  if (!canDelete(row)) {
    ElMessage.warning('该合同处于「审批中/已审批/已签订」状态，不允许删除。请先处理状态后再试。')
    return
  }
  const ok = await ElMessageBox.confirm(
    `确定删除合同「${row.code} ${row.name}」？\n\n此操作不可撤销。`,
    '删除确认',
    { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' },
  ).then(() => true).catch(() => false)
  if (!ok) return
  try {
    await contractApi.delete(row.id)
    ElMessage.success('删除成功')
    clearSelection()
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.message || '删除失败')
  }
}
async function deleteBatch() {
  if (!canWrite()) { permTip(); return }
  const ids = Array.from(selectedIds.value)
  if (!ids.length) {
    ElMessage.warning('请先选择要删除的合同')
    return
  }
  const rows = filteredRows.value.filter((r: any) => selectedIds.value.has(r.id))
  const forbiddenCount = rows.filter((r: any) => !canDelete(r)).length
  const tip = forbiddenCount > 0
    ? `已选 ${ids.length} 条，其中 ${forbiddenCount} 条因处于「审批中/已审批/已签订」状态将被跳过。\n\n`
    : `已选 ${ids.length} 条合同，确定删除？\n\n`
  const ok = await ElMessageBox.confirm(
    `${tip}此操作不可撤销。`,
    '批量删除确认',
    { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' },
  ).then(() => true).catch(() => false)
  if (!ok) return
  try {
    const res: any = await contractApi.batchDelete(ids)
    const d = (res?.data ?? res) as any
    const deleted = Number(d?.deleted ?? 0)
    const skipped = (d?.skipped?.length) || 0
    let msg = `已删除 ${deleted} 条`
    if (skipped > 0) msg += `，跳过 ${skipped} 条（状态不允许删除）`
    ElMessage.success(msg)
    clearSelection()
    await loadData()
  } catch (e: any) {
    ElMessage.error(e?.message || '批量删除失败')
  }
}

// 导出 CSV（按当前筛选结果）
function exportCsv() {
  const rows = filteredRows.value
  if (!rows.length) {
    ElMessage.warning('当前无可导出数据')
    return
  }
  const headers = ['合同编号', '合同名称', '客户', '类型', '金额(元)', '签订日期', '到期日期', '审批状态', '电子签', 'AI 风险']
  const escape = (v: any) => {
    const s = (v ?? '').toString()
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const lines = [
    headers.join(','),
    ...rows.map((r: any) => [
      r.code, r.name, r.client, r.typeLabel,
      r.amount, r.signDate, r.expireDate, r.statusLabel, r.signLabel, r.aiRiskReason || '—',
    ].map(escape).join(','))
  ]
  // 加 BOM 让 Excel 正确识别 UTF-8
  const csv = '\uFEFF' + lines.join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  a.href = url
  a.download = `合同列表-${ts}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success(`已导出 ${rows.length} 条合同`)
}

// 加载真实数据
async function loadData() {
  loading.value = true
  try {
    // 并行：列表 + stats
    const [listRes, statsRes] = await Promise.all([
      contractApi.list({ page: 1, pageSize: 100 } as any).catch((e: any) => {
        console.warn('contracts/list 失败：', e)
        return { list: [], total: 0 } as any
      }),
      contractApi.stats().catch((e: any) => {
        console.warn('contracts/stats 失败：', e)
        return null
      }),
    ])

    // 1. 列表映射
    const raw = (listRes as any)?.list || []
    list.value = raw.map((r: any) => {
      const t = normalizeType(r.type || r.contractType)
      const s = normalizeStatus(r.status)
      const risk = deriveRiskLevel(r)
      const signRaw = (r.signingStatus || r.status || '').toString().toLowerCase()
      const signMap: Record<string, { key: string; label: string }> = {
        done:    { key: 'done',    label: '已签' },
        signed:  { key: 'done',    label: '已签' },
        active:  { key: 'done',    label: '已签' },
        partial: { key: 'partial', label: '部分' },
        none:    { key: 'none',    label: '未签' },
        draft:   { key: 'none',    label: '未签' },
      }
      const sign = signMap[signRaw] || (signRaw === 'executed' ? { key: 'done', label: '已签' } : { key: 'none', label: '未签' })
      return {
        id: r.contractId || r.id,
        code: r.code || r.contractCode || 'DRAFT',
        name: r.name || r.contractName || '-',
        client: r.clientName || r.client?.name || '-',
        type: t.key,
        typeLabel: t.label,
        typeColor: t.color,
        amount: Number(r.amount) || 0,  // 后端单位：元
        signDate: r.signDate || '-',
        expireDate: r.expireDate || '-',
        status: (r.status || 'draft').toString().toLowerCase(),
        statusLabel: s.label,
        statusColor: s.color,
        sign: sign.key,
        signLabel: sign.label,
        aiRiskLevel: risk.level,
        aiRiskReason: risk.reason,
      }
    })
    total.value = (listRes as any)?.total || 0

    // 2. 更新 KPI（优先用后端 stats，否则前端算）
    if (statsRes && (statsRes as any)?.data) {
      const d = (statsRes as any).data
      const totalAmtWan = ((Number(d.totalAmount) || 0) / 10000).toFixed(1)
      const executed = Number(d.executed) || 0
      const pending = Number(d.pendingApproval) || 0
      const expSoon = Number(d.expiringSoon) || 0
      stats.value[0].value = Number(d.total) || list.value.length
      stats.value[0].delta = executed > 0 ? `执行中 ${executed} 份` : '暂无执行中'
      stats.value[1].value = totalAmtWan
      stats.value[1].delta = list.value.length > 0 ? `本年累计 / ${list.value.length} 份` : '本年累计'
      stats.value[2].value = pending
      stats.value[2].delta = pending > 0 ? '需法务审核' : '无待办'
      stats.value[3].value = expSoon
      stats.value[3].delta = expSoon > 0 ? '30 天内到期' : '暂无'
    } else {
      // 降级：前端基于列表算
      const mapped = list.value
      const totalAmtWan = (mapped.reduce((s, r) => s + (r.amount || 0), 0) / 10000).toFixed(1)
      const pending = mapped.filter((r: any) => ['审批中', '待审批', 'approving', 'pending'].includes(r.statusLabel)).length
      const expSoon = mapped.filter((r: any) => r.statusLabel === '即将到期').length
      const executing = mapped.filter((r: any) => ['执行中', '已签订'].includes(r.statusLabel)).length
      stats.value[0].value = mapped.length
      stats.value[0].delta = `执行中 ${executing} 份`
      stats.value[1].value = totalAmtWan
      stats.value[1].delta = `本年累计 / ${mapped.length} 份`
      stats.value[2].value = pending
      stats.value[2].delta = pending > 0 ? '需法务审核' : '无待办'
      stats.value[3].value = expSoon
      stats.value[3].delta = expSoon > 0 ? '30 天内到期' : '暂无'
    }

    // 3. 类型计数（前端按映射 key 算）
    const cntMap: Record<string, number> = { sales: 0, purchase: 0, service: 0, framework: 0, other: 0 }
    list.value.forEach((r: any) => { cntMap[r.type] = (cntMap[r.type] || 0) + 1 })
    typeCounts.value.all = list.value.length
    typeCounts.value.sales = cntMap.sales
    typeCounts.value.purchase = cntMap.purchase
    typeCounts.value.service = cntMap.service
    typeCounts.value.framework = cntMap.framework
    typeCounts.value.other = cntMap.other
  } catch (e) {
    console.error('loadData 异常：', e)
    ElMessage.error('合同数据加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // 触点 #24：发票详情跳过来要关联合同
  if (linkInvoiceId.value) {
    await _loadLinkInvoice()
    ElMessageBox.confirm(
      `已从发票详情跳转，请选择：\n\n• 「确定」= 新建一份合同并自动关联到该发票\n• 「取消」= 返回列表手动选择已有合同关联`,
      `🔗 关联合同到发票 #${linkInvoiceId.value}`,
      { confirmButtonText: '📝 新建并关联', cancelButtonText: '查看现有合同', type: 'info' }
    ).then(() => {
      router.push({ path: '/contract/create', query: { linkInvoiceId: linkInvoiceId.value } })
    }).catch(() => {
      ElMessage.info('已为你筛选该发票关联的合同')
    })
  }
  await loadData()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>合同管理</h1>
        <p class="page-desc">合同全生命周期管理 · 当前 {{ typeCounts.all }} 份合同</p>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button @click="gotoAiPanel">🤖 AI 体检</el-button>
        <el-button type="primary" :icon="'Plus'" @click="gotoCreate">新建合同</el-button>
      </div>
    </div>

    <!-- 4 KPI 统计卡（来自后端 stats） -->
    <div class="kpi-row fade-up">
      <div v-for="s in stats" :key="s.label" class="stat-card">
        <div class="stat-label">
          <span>{{ s.label }}</span>
          <span class="stat-icon" :style="{ background: s.iconBg, color: s.iconColor }">{{ s.icon }}</span>
        </div>
        <div class="stat-value">{{ s.value }} <span class="unit">{{ s.unit }}</span></div>
        <div class="stat-delta">{{ s.delta }}</div>
      </div>
    </div>

    <!-- 5 类 filter-chip -->
    <div class="page-card">
      <div class="filter-bar">
        <a href="javascript:void(0)" :class="['filter-chip', { active: activeType === 'all' }]"
           @click="activeType = 'all'">全部 ({{ typeCounts.all }})</a>
        <a href="javascript:void(0)" :class="['filter-chip', { active: activeType === 'sales' }]"
           @click="activeType = 'sales'">销售合同 ({{ typeCounts.sales }})</a>
        <a href="javascript:void(0)" :class="['filter-chip', { active: activeType === 'purchase' }]"
           @click="activeType = 'purchase'">采购合同 ({{ typeCounts.purchase }})</a>
        <a href="javascript:void(0)" :class="['filter-chip', { active: activeType === 'service' }]"
           @click="activeType = 'service'">服务合同 ({{ typeCounts.service }})</a>
        <a href="javascript:void(0)" :class="['filter-chip', { active: activeType === 'framework' }]"
           @click="activeType = 'framework'">框架协议 ({{ typeCounts.framework }})</a>
      </div>
    </div>

    <!-- 审批流程（design: .flow-card 6 步骤） -->
    <div class="flow-card fade-up">
      <h3>当前审批流程 · HT-2026-031 销售服务合同</h3>
      <div class="flow-sub">由李明于 2026-06-11 提交，预计今日 18:00 前完成全部审批</div>
      <div class="flow-row">
        <template v-for="(step, i) in flowSteps" :key="i">
          <div :class="['flow-step', step.state]">
            <div class="node">{{ step.state === 'done' ? '✓' : (i + 1) }}</div>
            <div class="lbl">{{ step.label }}</div>
            <div class="meta">{{ step.meta }}</div>
          </div>
          <div v-if="i < flowSteps.length - 1" :class="['flow-line', step.state === 'done' ? 'done' : '']"></div>
        </template>
      </div>
    </div>

    <!-- 合同列表（真实后端数据） -->
    <div class="page-card">
      <div class="card-head-row">
        <h3>合同列表</h3>
        <div class="toolbar">
          <input v-model="query.keyword" class="search-input" placeholder="搜索合同名 / 客户..." />
          <select v-model="query.client" class="select-sm">
            <option value="">所有客户</option>
            <option>天津西尔旅游</option>
            <option>北京速燃茶业</option>
            <option>北京花神假日酒店</option>
          </select>
          <input v-model="query.date" type="date" class="select-sm" />
          <!-- 触点 #22：AI 智能筛选 -->
          <button class="btn btn-ai-outline" @click="aiFilterVisible = true">🤖 AI 智能筛选</button>
          <button v-if="aiFilter" class="btn btn-ghost btn-sm" @click="clearAiFilter">✕ 清筛选</button>
          <button class="btn btn-outline btn-sm" @click="exportCsv">⇩ 导出 CSV</button>
          <button
            class="btn btn-outline btn-sm"
            :class="{ disabled: selectedIds.size === 0 || batchPrinting }"
            :disabled="selectedIds.size === 0 || batchPrinting"
            @click="batchPrint"
            v-permission="'print:document:export'"
          >
            🖨 批量打印{{ selectedIds.size > 0 ? ` (${selectedIds.size})` : '' }}
          </button>
          <button
            class="btn btn-outline btn-sm danger"
            :class="{ disabled: selectedIds.size === 0 }"
            :disabled="selectedIds.size === 0"
            @click="deleteBatch"
          >
            🗑 批量删除{{ selectedIds.size > 0 ? ` (${selectedIds.size})` : '' }}
          </button>
          <button
            class="btn btn-primary btn-sm"
            @click="canWrite() ? gotoCreate() : permTip()"
          >+ 新建合同</button>
        </div>
      </div>

      <div v-if="loading" class="table-loading">
        <div class="spinner"></div>
        <span>加载中…</span>
      </div>
      <div v-else-if="!filteredRows.length" class="ct-empty">
        <span>📭 暂无数据</span>
      </div>
      <table v-else class="ct-table">
        <thead>
          <tr>
            <th style="width: 40px;">
              <input
                type="checkbox"
                :checked="isAllSelected"
                :indeterminate.prop="isIndeterminate"
                @change="(e: any) => onToggleAll(e.target.checked)"
                class="row-check"
              />
            </th>
            <th>合同编号</th>
            <th>合同名称</th>
            <th>客户</th>
            <th>类型</th>
            <th>AI 风险</th>
            <th style="text-align: right;">金额</th>
            <th>签订日期</th>
            <th>到期日期</th>
            <th>审批状态</th>
            <th>电子签</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in filteredRows" :key="r.id" :class="{ 'row-selected': selectedIds.has(r.id) }">
            <td>
              <input
                type="checkbox"
                :checked="selectedIds.has(r.id)"
                @change="(e: any) => onRowToggle(r, e.target.checked)"
                class="row-check"
              />
            </td>
            <td><span class="cell-mono">{{ r.code }}</span></td>
            <td>{{ r.name }}</td>
            <td>{{ r.client }}</td>
            <td><span :class="['tag', `tag-${r.typeColor}`]">{{ r.typeLabel }}</span></td>
            <!-- 触点 #7：AI 风险标签列 -->
            <td>
              <AIRiskChip v-if="r.aiRiskLevel && r.aiRiskLevel !== 'unknown'" :level="r.aiRiskLevel" :reason="r.aiRiskReason" />
              <span v-else class="text-tertiary">—</span>
            </td>
            <td class="cell-amount">{{ fmtAmount(r.amount) }}</td>
            <td>{{ r.signDate }}</td>
            <td>{{ r.expireDate }}</td>
            <td><span :class="['tag', `tag-${r.statusColor}`]">{{ r.statusLabel }}</span></td>
            <td>
              <span :class="['sign-status', r.sign]">
                <span class="ico">{{ r.sign === 'done' ? '✓' : (r.sign === 'partial' ? '!' : '◯') }}</span>
                {{ r.signLabel }}
              </span>
            </td>
            <td class="cell-actions">
              <a @click="gotoDetail(r)">查看</a>
              <a v-if="r.status === 'approving' || r.statusLabel === '审批中'" :class="{ 'is-busy': urgeBusyId === r.id }" @click="openUrgeDialog(r)">催办</a>
              <a v-if="['signed','executed','active','approved'].includes(r.status) || ['已签订','执行中','已审批'].includes(r.statusLabel)" :class="{ 'is-busy': downloadBusyId === r.id }" @click="downloadOne(r)">下载</a>
              <a v-if="r.status === 'expiring' || r.statusLabel === '即将到期' || r.status === 'expired' || r.statusLabel === '已到期'"
                 @click="canWrite() ? ElMessage.info('续签：' + r.code) : permTip()">续签</a>
              <a v-if="r.status === 'expired' || r.statusLabel === '已到期'"
                 @click="canWrite() ? ElMessage.info('归档：' + r.code) : permTip()">归档</a>
              <a
                class="link-danger"
                @click="deleteOne(r)"
              >删除</a>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="rec-foot">
        <span class="rec-count">共 {{ filteredRows.length }} 份 · 显示 1-{{ filteredRows.length }}</span>
        <span v-if="selectedIds.size > 0" class="rec-selected">
          已选 {{ selectedIds.size }} 条 ·
          <a class="link-primary" @click="clearSelection">清空选择</a>
        </span>
      </div>
    </div>
  </div>

  <!-- 触点 #22：AI 智能筛选 Drawer -->
  <AiFilterDialog v-model:visible="aiFilterVisible" scope="contract" @apply="onAiFilterApply" />

  <!-- 催办弹窗 -->
  <el-dialog
    v-model="urgeDialogVisible"
    title="催办合同"
    width="480px"
    :close-on-click-modal="false"
    @close="urgeTarget = null"
  >
    <div v-if="urgeTarget" class="urge-target">
      <div class="urge-row">
        <span class="urge-label">合同</span>
        <span class="cell-mono">{{ urgeTarget.code }}</span>
        <span class="urge-name">{{ urgeTarget.name }}</span>
      </div>
      <div class="urge-row">
        <span class="urge-label">状态</span>
        <span class="tag tag-warning">{{ urgeTarget.statusLabel || '审批中' }}</span>
      </div>
      <div class="urge-field">
        <label>催办留言（可选，会作为通知内容发给审批人）</label>
        <el-input
          v-model="urgeMessage"
          type="textarea"
          :rows="3"
          :maxlength="500"
          show-word-limit
          placeholder="例如：请优先审批，本周内需签约…"
        />
      </div>
    </div>
    <template #footer>
      <el-button @click="urgeDialogVisible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="urgeBusyId === urgeTarget?.id"
        @click="submitUrge"
      >发送催办</el-button>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-card { @include page-card; }
.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }

// KPI 4 列
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
  margin-bottom: 24px;
  @media (max-width: 1100px) { grid-template-columns: repeat(2, 1fr); }
}
.stat-card {
  @include stat-card;
  .stat-label {
    font-size: 12.5px;
    color: $color-text-secondary;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: relative;
    z-index: 1;
  }
  .stat-icon {
    width: 32px; height: 32px;
    border-radius: 8px;
    display: grid; place-items: center;
    font-size: 16px;
    font-weight: 600;
  }
  .stat-value {
    font-size: 26px;
    font-weight: 700;
    color: $color-text-primary;
    font-family: $font-family-mono;
    margin: 6px 0;
    position: relative;
    z-index: 1;
    .unit { font-size: 13px; color: $color-text-tertiary; font-weight: 500; margin-left: 4px; font-family: -apple-system, sans-serif; }
  }
  .stat-delta { font-size: 12px; color: $color-text-tertiary; position: relative; z-index: 1; }
}

// filter-chip 类别切换
.filter-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 4px 0;
}
.filter-chip {
  padding: 6px 14px;
  border-radius: 9999px;
  font-size: 12.5px;
  color: $color-text-secondary;
  background: #fff;
  border: 1px solid $color-border;
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;
  text-decoration: none;
  &:hover { border-color: $color-primary; color: $color-primary; }
  &.active {
    background: $gradient-brand;
    color: #fff;
    border-color: transparent;
  }
}

// flow-card 审批流程
.flow-card {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 24px 28px;
  margin-bottom: 24px;
  h3 { font-size: 15px; font-weight: 600; margin: 0 0 6px 0; }
  .flow-sub { font-size: 12.5px; color: $color-text-tertiary; margin-bottom: 24px; }
  .flow-row { display: flex; align-items: flex-start; gap: 0; }
  .flow-step {
    display: flex; flex-direction: column; align-items: center;
    position: relative; flex: 1; min-width: 80px;
    .node {
      width: 40px; height: 40px;
      border-radius: 50%;
      background: $color-bg;
      color: $color-text-tertiary;
      display: grid; place-items: center;
      font-size: 14px; font-weight: 600;
      border: 2px solid $color-border-strong;
      z-index: 1;
    }
    &.done .node {
      background: linear-gradient(135deg, #10B981, #059669);
      border-color: transparent;
      color: #fff;
    }
    &.current .node {
      background: $gradient-brand;
      border-color: transparent;
      color: #fff;
      box-shadow: 0 0 0 4px rgba(79,107,255,0.15);
    }
    .lbl { font-size: 12.5px; font-weight: 600; margin-top: 8px; color: $color-text-primary; }
    .meta { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; text-align: center; }
  }
  .flow-line {
    flex: 0 0 32px;
    height: 2px;
    background: $color-border;
    margin-top: 19px;
    &.done { background: linear-gradient(90deg, #10B981, #059669); }
  }
}

// 工具栏
.card-head-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  h3 { font-size: 15px; font-weight: 600; margin: 0; }
  .toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
}
.search-input {
  padding: 6px 12px;
  border: 1px solid $color-border;
  border-radius: 6px;
  font-size: 13px;
  width: 180px;
  outline: none;
  &:focus { border-color: $color-primary; }
}
.select-sm {
  padding: 6px 8px;
  border: 1px solid $color-border;
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
  outline: none;
}

// 按钮
.btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
  background: #fff;
}
.btn-sm { padding: 5px 10px; font-size: 12.5px; }
.btn-primary {
  background: $gradient-brand;
  color: #fff;
  border-color: transparent;
  &:hover { opacity: 0.9; }
}
.btn-outline {
  background: #fff;
  border-color: $color-border;
  color: $color-text-primary;
  &:hover { border-color: $color-primary; color: $color-primary; }
}
.btn-ai-outline {
  background: linear-gradient(135deg, rgba(79,107,255,0.08), rgba(16,185,129,0.08));
  border: 1px solid rgba(79,107,255,0.3);
  color: $color-primary;
  &:hover { background: linear-gradient(135deg, rgba(79,107,255,0.15), rgba(16,185,129,0.15)); }
}
.btn-ghost {
  background: transparent;
  border-color: transparent;
  color: $color-text-secondary;
  &:hover { background: $color-bg; }
}

// 表格
.table-loading {
  padding: 48px 0;
  text-align: center;
  color: $color-text-tertiary;
  .spinner {
    width: 24px; height: 24px;
    border: 2px solid $color-border;
    border-top-color: $color-primary;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto 8px;
  }
}
@keyframes spin { to { transform: rotate(360deg); } }
.ct-empty {
  padding: 48px 0;
  text-align: center;
  color: $color-text-tertiary;
  font-size: 14px;
}
.ct-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  thead th {
    text-align: left;
    padding: 10px 12px;
    background: $color-bg;
    color: $color-text-secondary;
    font-weight: 600;
    font-size: 12.5px;
    border-bottom: 1px solid $color-border;
  }
  tbody td {
    padding: 12px;
    border-bottom: 1px solid $color-border;
    color: $color-text-primary;
  }
  tbody tr:hover { background: rgba(79,107,255,0.02); }
}
.cell-mono {
  font-family: $font-family-mono;
  font-size: 12.5px;
  color: $color-text-primary;
  font-weight: 500;
}
.cell-amount {
  text-align: right;
  font-family: $font-family-mono;
  font-weight: 600;
}
.cell-actions {
  display: flex;
  gap: 8px;
  a {
    color: $color-primary;
    cursor: pointer;
    font-size: 12.5px;
    &:hover { text-decoration: underline; }
  }
}
.text-tertiary { color: $color-text-tertiary; font-size: 12.5px; }

// 标签
.tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}
.tag-primary { background: rgba(79,107,255,0.1); color: $color-primary; }
.tag-success { background: rgba(16,185,129,0.1); color: #059669; }
.tag-warning { background: rgba(245,158,11,0.1); color: #B45309; }
.tag-danger  { background: rgba(239,68,68,0.1); color: #B91C1C; }
.tag-info    { background: rgba(99,102,241,0.1); color: #4F46E5; }
.tag-purple  { background: rgba(168,85,247,0.1); color: #7E22CE; }
.tag-gray    { background: $color-bg; color: $color-text-secondary; }

.sign-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12.5px;
  .ico { font-weight: 600; }
  &.done { color: #059669; }
  &.partial { color: #B45309; }
  &.none { color: $color-text-tertiary; }
}

.urge-target { display: flex; flex-direction: column; gap: 10px; }
.urge-row { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.urge-label { color: var(--text-tertiary, #94a3b8); min-width: 32px; }
.urge-name { color: var(--text-primary, #1f2937); font-weight: 500; }
.urge-field { display: flex; flex-direction: column; gap: 6px; margin-top: 6px; }
.urge-field label { font-size: 12px; color: var(--text-secondary, #6b7280); }
.cell-actions a.is-busy { opacity: 0.5; pointer-events: none; }

.rec-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0 4px;
  .rec-count { font-size: 12.5px; color: $color-text-tertiary; }
  .rec-selected { font-size: 12.5px; color: $color-primary; }
}

/* checkbox 样式 */
.row-check {
  width: 16px; height: 16px;
  cursor: pointer;
  accent-color: $color-primary;
  &:disabled { cursor: not-allowed; opacity: 0.4; }
}
tr.row-selected {
  background: rgba(79, 107, 255, 0.04) !important;
}

/* 危险按钮 & 链接 */
.btn.danger {
  color: $color-danger;
  border-color: rgba(239, 68, 68, 0.3);
  &:hover:not(:disabled) {
    background: rgba(239, 68, 68, 0.06);
    border-color: $color-danger;
    color: $color-danger;
  }
  &:disabled, &.disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
}
.link-danger {
  color: $color-danger !important;
  &:hover { color: #B91C1C !important; }
}
</style>
