<script setup lang="ts">
/**
 * ExpenseDetail · 销售费用详情（接真实 API）
 * - 真实数据源：expenseApi.detail(id)
 * - 状态映射：draft/pending/pending_review/submitted→审批中，approved→已通过，rejected→已驳回
 * - 金额单位：API 已返回元（不再换算）
 */
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { expenseApi, invoiceOcrApi } from '@/api/modules'

const router = useRouter()
const route = useRoute()

const activeTab = ref<'basic' | 'flow' | 'related' | 'history'>('basic')

const loading = ref(false)
const printVisible = ref(false)

function openPrint() { printVisible.value = true }
function doPrint() {
  // 给浏览器一点时间渲染打印内容
  setTimeout(() => window.print(), 100)
}
const detail = reactive<any>({
  expenseId: 0,
  code: '',
  category: '其他',
  title: '',
  description: '',
  amount: 0,
  currency: 'CNY',
  expenseDate: '',
  submitDate: null,
  applicant: { userId: 0, name: '-', avatar: null },
  department: null,
  contractId: null,
  projectId: null,
  breakdown: [] as Array<any>,
  attachments: [] as Array<any>,
  approvalFlow: null as any,
  status: 'draft',
  createdAt: '',
  updatedAt: '',
})

const CATEGORY_LABEL: Record<string, string> = {
  差旅: '差旅', 招待: '招待', 办公: '办公', 推广: '推广', 培训: '培训', 其他: '其他', communication: '通讯',
}
const CATEGORY_COLOR: Record<string, string> = {
  差旅: 'info', 招待: 'warning', 办公: 'primary', 推广: 'success', 培训: 'purple', 其他: 'gray', communication: 'cyan',
}
const STATUS_LABEL: Record<string, string> = {
  draft: '草稿', pending: '审批中', pending_review: '审批中', submitted: '审批中',
  approved: '已通过', rejected: '已驳回', paid: '已报销',
}
const STATUS_COLOR: Record<string, string> = {
  draft: 'gray', pending: 'warning', pending_review: 'warning', submitted: 'warning',
  approved: 'success', rejected: 'danger', paid: 'primary',
}

const typeLabel = computed(() => CATEGORY_LABEL[detail.category] || detail.category || '其他')
const typeColor = computed(() => CATEGORY_COLOR[detail.category] || 'gray')
const statusLabel = computed(() => STATUS_LABEL[detail.status] || detail.status || '草稿')
const statusColor = computed(() => STATUS_COLOR[detail.status] || 'gray')
const amountYuan = computed(() => Number(detail.amount) || 0)
const formattedAmount = computed(() => `¥ ${amountYuan.value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
const formattedApplyDate = computed(() => {
  const s = detail.submitDate || detail.createdAt
  if (!s) return '-'
  return s.replace('T', ' ').substring(0, 16)
})
const formattedExpenseDate = computed(() => detail.expenseDate || '-')

async function loadDetail() {
  const id = Number(route.params.id)
  if (!id) {
    ElMessage.error('缺少费用 ID')
    return
  }
  loading.value = true
  try {
    const res: any = await expenseApi.detail(id)
    if (res) {
      Object.assign(detail, {
        expenseId: res.expenseId ?? id,
        code: res.code || '',
        category: res.category || '其他',
        title: res.title || '',
        description: res.description || '',
        amount: res.amount ?? 0,
        currency: res.currency || 'CNY',
        expenseDate: res.expenseDate || '',
        submitDate: res.submitDate || null,
        applicant: res.applicant || { userId: 0, name: '-', avatar: null },
        department: res.department || null,
        contractId: res.contractId || null,
        projectId: res.projectId || null,
        breakdown: Array.isArray(res.breakdown) ? res.breakdown : [],
        attachments: Array.isArray(res.attachments) ? res.attachments : [],
        approvalFlow: res.approvalFlow || null,
        status: res.status || 'draft',
        createdAt: res.createdAt || '',
        updatedAt: res.updatedAt || '',
        invoiceId: res.invoiceId ?? null,
        relatedInvoice: res.relatedInvoice || null,
      })
    }
  } catch (e) {
    console.error('加载费用详情失败', e)
  } finally {
    loading.value = false
  }
}

function goBack() { router.push('/expense/list') }
function goEdit() {
  if (!detail.expenseId) { ElMessage.error('缺少费用 ID'); return }
  router.push(`/expense/create?id=${detail.expenseId}`)
}
function copyAs() {
  if (!detail.expenseId) { ElMessage.error('缺少费用 ID'); return }
  ElMessage.success('已复制申请（以新草稿创建，可继续编辑）')
  router.push('/expense/create')
}

// 费用明细编辑（弹窗）
const breakdownDialogVisible = ref(false)
const breakdownDraft = ref<Array<{label: string, amount: number, remark: string}>>([])

// 关联单据相关
const hasAnyRelated = computed(() => !!(detail as any)?.relatedInvoice || !!(detail as any)?.contractId || !!(detail as any)?.projectId)
const canLinkInvoice = computed(() => detail.status === 'draft' || detail.status === 'pending' || detail.status === 'pending_review' || detail.status === 'rejected')
function verifyStatusLabel(s?: string) {
  return ({ pending: '待核验', verified: '已核验', rejected: '已驳回', failed: '识别失败', expired: '已过期' } as Record<string,string>)[s || ''] || s || '待核验'
}
function goInvoice(id?: number) {
  if (!id) return
  router.push(`/invoice/ocr/${id}`)
}
function auditLabel(s?: string) {
  return ({ match: '金额一致', partial: '部分报销', over: '超额异常', mismatch: '金额不匹配', unknown: '无法比对' } as Record<string,string>)[s || ''] || s || '未知'
}
function auditIcon(s?: string) {
  return ({ match: '✅', partial: '🟡', over: '⚠️', mismatch: '❌', unknown: '❔' } as Record<string,string>)[s || ''] || '·'
}

// 关联发票弹窗
const linkInvoiceDialog = ref(false)
const linkKeyword = ref('')
const linkCandidates = ref<any[]>([])
const linkSearching = ref(false)
const pickedInvoiceId = ref<number | null>(null)
const linkSubmitting = ref(false)
let linkSearchTimer: any = null

async function searchInvoices() {
  linkSearching.value = true
  try {
    // 走后端 /invoice/ocr/unlinked：已核验 + 未被任何费用关联
    const res: any = await invoiceOcrApi.unlinked({ page: 1, pageSize: 50, keyword: linkKeyword.value } as any)
    linkCandidates.value = res?.list || res?.data?.list || []
  } catch (e) {
    linkCandidates.value = []
  } finally {
    linkSearching.value = false
  }
}
function debounceSearchInvoices() {
  clearTimeout(linkSearchTimer)
  linkSearchTimer = setTimeout(searchInvoices, 300)
}
async function confirmLinkInvoice() {
  if (!pickedInvoiceId.value) return
  linkSubmitting.value = true
  try {
    await expenseApi.update(detail.expenseId, { invoiceId: pickedInvoiceId.value } as any)
    ElMessage.success('已关联发票')
    linkInvoiceDialog.value = false
    pickedInvoiceId.value = null
    linkKeyword.value = ''
    await loadDetail()
  } catch (e: any) {
    ElMessage.error('关联失败：' + (e?.response?.data?.msg || e?.message || '未知错误'))
  } finally {
    linkSubmitting.value = false
  }
}
async function unlinkInvoice() {
  try {
    await ElMessageBox.confirm('确认解除与该发票的关联？此操作不会删除发票。', '解除关联', { type: 'warning' })
  } catch { return }
  try {
    await expenseApi.update(detail.expenseId, { invoiceId: null } as any)
    ElMessage.success('已解除关联')
    await loadDetail()
  } catch (e: any) {
    ElMessage.error('解除失败：' + (e?.response?.data?.msg || e?.message || '未知错误'))
  }
}

// 监听弹窗打开，自动拉一次
watch(linkInvoiceDialog, (v) => { if (v) { linkKeyword.value = ''; pickedInvoiceId.value = null; searchInvoices() } })
// 关键字变化时去抖
watch(linkKeyword, debounceSearchInvoices)
const breakdownSaving = ref(false)

function openBreakdownEditor() {
  // 把现有明细深拷贝一份到草稿（amount 转元以便编辑）
  breakdownDraft.value = (detail.breakdown || []).map((b: any) => ({
    label: b.label || '',
    amount: Number(b.amount || 0),
    remark: b.remark || '',
  }))
  if (breakdownDraft.value.length === 0) {
    // 至少加一行空行
    breakdownDraft.value.push({ label: '', amount: 0, remark: '' })
  }
  breakdownDialogVisible.value = true
}
function addBreakdownRow() {
  breakdownDraft.value.push({ label: '', amount: 0, remark: '' })
}
function removeBreakdownRow(idx: number) {
  breakdownDraft.value.splice(idx, 1)
}
async function saveBreakdown() {
  if (breakdownSaving.value) return
  // 校验：去掉全空行
  const items = breakdownDraft.value.filter((r: any) => r.label || r.amount)
  for (const it of items) {
    if (!it.label) { ElMessage.warning('请填写项目名称'); return }
    if (!(Number(it.amount) > 0)) { ElMessage.warning('金额必须 > 0'); return }
  }
  breakdownSaving.value = true
  try {
    // 后端 update 接口要求 amount 是"分"，前端传"元"会再 *100
    // 这里用 raw 后端字段名 label/amount/remark，但 amount 传"分"
    const payload = items.map((it: any) => ({
      label: it.label,
      amount: Number(it.amount),  // 元 (后端 service *100 转分)
      remark: it.remark || null,
    }))
    await expenseApi.update(detail.expenseId, { breakdown: payload } as any)
    ElMessage.success(`已保存 ${items.length} 项费用明细`)
    breakdownDialogVisible.value = false
    await loadDetail()
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    const msg = Array.isArray(detail)
      ? detail.map((d: any) => `${d.loc?.slice(-1)[0] || ''}: ${d.msg || ''}`).join('；')
      : (detail || e?.message || '未知错误')
    ElMessage.error('保存失败：' + msg)
  } finally {
    breakdownSaving.value = false
  }
}
function cancelBreakdown() {
  breakdownDialogVisible.value = false
}
async function approve() {
  if (!detail.expenseId) return
  try {
    await expenseApi.approve(detail.expenseId, { action: 'approve', comment: '同意' })
    ElMessage.success('已审批通过')
    await loadDetail()
  } catch (e: any) {
    ElMessage.error('审批失败：' + (e?.message || '未知错误'))
  }
}
async function reject() {
  if (!detail.expenseId) return
  try {
    await expenseApi.approve(detail.expenseId, { action: 'reject', comment: '驳回' })
    ElMessage.warning('已驳回')
    await loadDetail()
  } catch (e: any) {
    ElMessage.error('驳回失败：' + (e?.message || '未知错误'))
  }
}
async function submitApproval() {
  if (!detail.expenseId) return
  try {
    await expenseApi.submit(detail.expenseId)
    ElMessage.success('已提交审批')
    await loadDetail()
  } catch (e: any) {
    ElMessage.error('提交失败：' + (e?.message || '未知错误'))
  }
}
async function markPaid() {
  if (!detail.expenseId) return
  try {
    await ElMessageBox.confirm('确认已向申请人打款 / 报销完成？该操作不可撤销。', '确认报销', { type: 'success', confirmButtonText: '确认报销', cancelButtonText: '再看看' })
    await expenseApi.markPaid(detail.expenseId)
    ElMessage.success('已确认报销')
    await loadDetail()
  } catch (e: any) {
    if (e?.message && e.message !== 'cancel') ElMessage.error('报销确认失败：' + (e?.message || '未知错误'))
  }
}
async function reassign() {
  if (!detail.expenseId) return
  try {
    const { value: userIdStr } = await ElMessageBox.prompt('请输入转交给的用户 ID（数字）', '转交审批', {
      inputPattern: /^\d+$/,
      inputErrorMessage: '请输入数字用户 ID',
      inputPlaceholder: '例如 2',
    } as any)
    const transferTo = Number(userIdStr)
    if (!transferTo) { ElMessage.warning('用户 ID 无效'); return }
    await expenseApi.approve(detail.expenseId, { action: 'transfer', comment: '转交', transferTo } as any)
    ElMessage.success('已转交')
    await loadDetail()
  } catch (e: any) {
    if (e?.message && e.message !== 'cancel') ElMessage.error('转交失败：' + (e?.message || '未知错误'))
  }
}
function uploadInvoice() { ElMessage.info('上传发票（待对接）') }
function downloadInvoice(item: any) { ElMessage.info('下载发票：' + (item?.name || item?.fileName || '附件')) }
function _flowStatusLabel(s: string) {
  return { in_progress: '进行中', approved: '已通过', rejected: '已驳回', transferred: '已转交' }[s] || s || '进行中'
}
function _stepStatusLabel(s: string) {
  return {
    done: '✓ 已完成', approved: '✓ 已通过', rejected: '✕ 已驳回',
    current: '⏳ 进行中', todo: '○ 待办', transferred: '↻ 已转交',
  }[s] || s || '○ 待办'
}
function _actionLabel(a: string) {
  return { approve: '同意', reject: '驳回', transfer: '转交', submit: '提交' }[a] || a
}


onMounted(() => {
  loadDetail()
})
</script>

<template>
  <div class="page-container">
    <!-- 顶部 detail-hero -->
    <div class="expense-hero">
      <div class="eh-left">
        <div class="eh-id">
          <span class="code">{{ detail.code || '—' }}</span>
          <span :class="['tag', `tag-${typeColor}`]">{{ typeLabel }}</span>
          <span :class="['tag', `tag-${statusColor}`]">{{ statusLabel }}</span>
        </div>
        <h1 class="eh-title">{{ detail.title || '—' }}</h1>
        <div class="eh-meta">
          <span>👤 {{ detail.applicant?.name || '-' }}</span>
          <span class="sep">·</span>
          <span>📅 {{ formattedApplyDate }}</span>
          <span v-if="detail.expenseDate" class="sep">·</span>
          <span v-if="detail.expenseDate">📆 费用日期 {{ formattedExpenseDate }}</span>
        </div>
      </div>
      <div class="eh-right">
        <div class="eh-amount-l">报销金额</div>
        <div class="eh-amount">{{ formattedAmount }}</div>
        <div class="eh-amount-c">{{ detail.breakdown?.length ? `含 ${detail.breakdown.length} 项费用明细` : '暂无费用明细' }}</div>
        <div class="eh-actions">
          <button v-if="statusLabel === '已通过'" class="eh-btn eh-btn-primary" @click="markPaid">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
            确认报销
          </button>
          <button v-if="statusLabel === '已驳回'" class="eh-btn eh-btn-primary" @click="submitApproval">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
            重新提交
          </button>
          <template v-if="statusLabel !== '已报销'">
            <button v-if="detail.status === 'draft' || (detail.status !== 'approved' && detail.status !== 'paid')" class="eh-btn eh-btn-default" @click="goEdit">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
              编辑
            </button>
            <button class="eh-btn eh-btn-default" @click="copyAs">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
              复制申请
            </button>
            <button class="eh-btn eh-btn-default" @click="openPrint">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"></polyline><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><rect x="6" y="14" width="12" height="8"></rect></svg>
              打印
            </button>
          </template>
          <span v-else class="eh-status-done">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
            已报销完成
          </span>
        </div>
      </div>
    </div>

    <!-- 4 tabs -->
    <div class="detail-tabs">
      <a href="javascript:void(0)" :class="{ active: activeTab === 'basic' }"   @click="activeTab = 'basic'">📋 费用信息</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'flow' }"    @click="activeTab = 'flow'">🔄 审批流程</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'related' }" @click="activeTab = 'related'">🔗 相关单据</a>
      <a href="javascript:void(0)" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">📜 操作历史</a>
    </div>

    <!-- 费用信息 tab -->
    <div v-show="activeTab === 'basic'" class="detail-layout">
      <div class="detail-section">
        <div class="detail-section-head"><h3>📌 基础信息</h3></div>
        <div class="detail-section-body">
          <div class="info-grid">
            <div class="info-row"><div class="l">申请单号</div><div class="v mono">{{ detail.code }}</div></div>
            <div class="info-row"><div class="l">费用类型</div><div class="v">{{ typeLabel }}</div></div>
            <div class="info-row"><div class="l">报销金额</div><div class="v amount">{{ formattedAmount }}</div></div>
            <div class="info-row"><div class="l">币种</div><div class="v">{{ detail.currency || 'CNY' }}</div></div>
            <div class="info-row"><div class="l">申请人</div><div class="v">{{ detail.applicant?.name || '-' }}</div></div>
            <div class="info-row"><div class="l">部门</div><div class="v">{{ detail.department?.name || '-' }}</div></div>
            <div class="info-row"><div class="l">费用日期</div><div class="v">{{ formattedExpenseDate }}</div></div>
            <div class="info-row"><div class="l">提交日期</div><div class="v">{{ detail.submitDate || '未提交' }}</div></div>
            <div class="info-row"><div class="l">关联合同</div><div class="v">{{ detail.contractId ? `#${detail.contractId}` : '—' }}</div></div>
            <div class="info-row"><div class="l">关联项目</div><div class="v">{{ detail.projectId ? `#${detail.projectId}` : '—' }}</div></div>
            <div class="info-row"><div class="l">状态</div><div class="v"><span :class="['tag', `tag-${statusColor}`]">{{ statusLabel }}</span></div></div>
            <div class="info-row"><div class="l">创建时间</div><div class="v mono">{{ detail.createdAt?.replace('T', ' ').substring(0, 19) || '-' }}</div></div>
          </div>

          <!-- AI 金额审核（有关联发票时显示） -->
          <div v-if="detail.relatedInvoice && detail.relatedInvoice.matchAudit" class="audit-bar" :class="'audit-' + detail.relatedInvoice.matchAudit.status">
            <span class="ab-icon">{{ auditIcon(detail.relatedInvoice.matchAudit.status) }}</span>
            <div class="ab-main">
              <div class="ab-title">🤖 AI 金额审核 · <b>{{ auditLabel(detail.relatedInvoice.matchAudit.status) }}</b></div>
              <div class="ab-reason">{{ detail.relatedInvoice.matchAudit.reason }}</div>
            </div>
            <div class="ab-actions">
              <span class="ab-tip">{{ detail.relatedInvoice.matchAudit.status === 'match' ? '可放心提交' : '建议核对报销金额' }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="detail-section">
        <div class="detail-section-head">
          <h3>📦 费用明细</h3>
          <button type="button" class="link-primary link-btn" @click="openBreakdownEditor">+ 添加明细</button>
        </div>
        <div class="detail-section-body">
          <table v-if="detail.breakdown?.length" class="expense-table">
            <thead>
              <tr><th>项目</th><th class="cell-amount">金额</th><th>备注</th></tr>
            </thead>
            <tbody>
              <tr v-for="(it, i) in detail.breakdown" :key="i">
                <td>{{ it.label || it.name || it.item || '—' }}</td>
                <td class="cell-amount">¥ {{ Number(it.amount || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</td>
                <td>{{ it.remark || it.spec || it.specification || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-tip">暂无费用明细</div>
        </div>
      </div>

      <div v-if="detail.description" class="detail-section">
        <div class="detail-section-head"><h3>📝 备注说明</h3></div>
        <div class="detail-section-body">
          <div class="description">{{ detail.description }}</div>
        </div>
      </div>
    </div>

    <!-- 审批流程 tab -->
    <div v-show="activeTab === 'flow'" class="detail-layout">
      <div class="detail-section">
        <div class="detail-section-head"><h3>🔄 当前审批节点</h3></div>
        <div class="detail-section-body">
          <div v-if="detail.approvalFlow" class="approval-flow">
            <div class="flow-summary">
              <span :class="['fs-tag', `flow-status-${detail.approvalFlow.status || 'in_progress'}`]">{{ _flowStatusLabel(detail.approvalFlow.status) }}</span>
              <span class="fs-text">共 {{ detail.approvalFlow.totalSteps || (detail.approvalFlow.steps||[]).length }} 步 · 当前第 {{ detail.approvalFlow.currentStep || '?' }} 步</span>
              <span v-if="detail.approvalFlow.startedAt" class="fs-time">开始：{{ String(detail.approvalFlow.startedAt).replace('T',' ').substring(0,16) }}</span>
              <span v-if="detail.approvalFlow.finishedAt" class="fs-time">结束：{{ String(detail.approvalFlow.finishedAt).replace('T',' ').substring(0,16) }}</span>
            </div>
            <div v-for="(step, i) in (detail.approvalFlow.steps || [])" :key="i" :class="['flow-step', `flow-step-${step.status || 'todo'}`]">
              <div class="flow-step-num">{{ step.seq || (i+1) }}</div>
              <div class="flow-step-body">
                <div class="flow-step-head">
                  <span class="flow-step-name">{{ step.name || `第${(i+1)}步` }}</span>
                  <span :class="['flow-state', `flow-${step.status || 'todo'}`]">{{ _stepStatusLabel(step.status) }}</span>
                </div>
                <div class="flow-step-meta">
                  <span>审批人：<b>{{ step.approverId ? '用户 #' + step.approverId : '系统/上级' }}</b></span>
                  <span v-if="step.action">· 操作：<b>{{ _actionLabel(step.action) }}</b></span>
                  <span v-if="step.triggerRule">· 触发：<b>{{ step.triggerRule }}</b></span>
                  <span v-if="step.finishedAt">· 完成：{{ String(step.finishedAt).replace('T',' ').substring(0,16) }}</span>
                </div>
                <div v-if="step.comment" class="flow-step-comment">💬 {{ step.comment }}</div>
              </div>
            </div>
          </div>
          <div v-else class="empty-tip">
            <template v-if="statusLabel === '草稿'">该申请尚未提交，无审批流


</template>
            <template v-else>暂无审批流信息</template>
          </div>
          <!-- 草稿：先提交审批 -->
          <div v-if="statusLabel === '草稿'" class="approval-actions">
            <button class="btn btn-primary btn-sm" @click="submitApproval">↗ 提交审批</button>
            <button class="btn btn-outline btn-sm" @click="reassign" disabled>↻ 转交</button>
            <span class="flow-tip">草稿状态，需先提交进入审批流</span>
          </div>
          <!-- 审批中：通过/驳回/转交 -->
          <div v-else-if="statusLabel === '审批中'" class="approval-actions">
            <button class="btn btn-primary btn-sm" @click="approve">✓ 审批通过</button>
            <button class="btn btn-outline btn-sm danger" @click="reject">✕ 驳回</button>
            <button class="btn btn-ghost btn-sm" @click="reassign">↻ 转交</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 相关单据 tab -->
    <div v-show="activeTab === 'related'" class="detail-layout">
      <div class="detail-section">
        <div class="detail-section-head">
          <h3>🔗 关联单据</h3>
          <div class="related-actions">
            <button v-if="canLinkInvoice" class="ff-link" @click="linkInvoiceDialog = true">+ 关联发票</button>
          </div>
        </div>
        <div class="detail-section-body">
          <!-- 空态 -->
          <div v-if="!hasAnyRelated" class="empty-related">
            <div class="er-icon">🔗</div>
            <div class="er-title">暂无关联单据</div>
            <div class="er-desc">本费用申请未关联合同、项目或其他发票。<br>如需关联发票（识别后），请点击右上角"关联发票"按钮。</div>
          </div>

          <!-- 关联列表 -->
          <div v-else class="related-list">
            <!-- 关联发票（来自"提交入账"自动生成或手动关联） -->
            <div class="related-item ri-invoice">
              <span class="ri-type ri-type-invoice">📄 发票</span>
              <div class="ri-main" @click="goInvoice(detail.relatedInvoice.invoiceId)">
                <div class="ri-name">{{ detail.relatedInvoice.invoiceType || '发票' }} · {{ detail.relatedInvoice.sellerName || '未知销售方' }}</div>
                <div class="ri-meta">
                  <span class="ri-no">发票号 {{ detail.relatedInvoice.invoiceNo || '-' }}</span>
                  <span class="ri-dot">·</span>
                  <span>开票日期 {{ detail.relatedInvoice.issueDate || '-' }}</span>
                  <span class="ri-dot">·</span>
                  <span class="ri-amt">¥ {{ Number(detail.relatedInvoice.totalAmount || 0).toFixed(2) }}</span>
                </div>
              </div>
              <span class="ri-status" :class="'rs-' + (detail.relatedInvoice.verifyStatus || 'pending')">
                {{ verifyStatusLabel(detail.relatedInvoice.verifyStatus) }}
              </span>
              <button v-if="canLinkInvoice" class="ri-unlink" title="解除关联" @click.stop="unlinkInvoice">解除</button>
              <span class="ri-arrow" @click="goInvoice(detail.relatedInvoice.invoiceId)">查看 ›</span>
            </div>

            <!-- AI 金额审核 -->
            <div v-if="detail.relatedInvoice.matchAudit" class="audit-bar" :class="'audit-' + detail.relatedInvoice.matchAudit.status">
              <span class="ab-icon">{{ auditIcon(detail.relatedInvoice.matchAudit.status) }}</span>
              <div class="ab-main">
                <div class="ab-title">🤖 AI 金额审核 · <b>{{ auditLabel(detail.relatedInvoice.matchAudit.status) }}</b></div>
                <div class="ab-reason">{{ detail.relatedInvoice.matchAudit.reason }}</div>
              </div>
              <div class="ab-actions" v-if="detail.relatedInvoice.matchAudit.status !== 'match'">
                <span class="ab-tip">建议核对报销金额</span>
              </div>
            </div>

            <!-- 合同 -->
            <div v-if="detail.contractId" class="related-item">
              <span class="ri-type">📑 合同</span>
              <div class="ri-main">
                <div class="ri-name">已关联合同</div>
                <div class="ri-meta"><span class="ri-no">#{{ detail.contractId }}</span></div>
              </div>
            </div>

            <!-- 项目 -->
            <div v-if="detail.projectId" class="related-item">
              <span class="ri-type">📁 项目</span>
              <div class="ri-main">
                <div class="ri-name">已关联项目</div>
                <div class="ri-meta"><span class="ri-no">#{{ detail.projectId }}</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 操作历史 tab -->
    <div v-show="activeTab === 'history'" class="detail-layout">
      <div class="detail-section">
        <div class="detail-section-head"><h3>📜 操作历史</h3></div>
        <div class="detail-section-body">
          <div class="timeline-det">
            <div class="t-item done">
              <div class="t">申请创建</div>
              <div class="m">{{ detail.applicant?.name || '-' }} · {{ detail.createdAt?.replace('T', ' ').substring(0, 19) || '-' }}</div>
              <div class="d">单号 {{ detail.code }}，金额 {{ formattedAmount }}</div>
            </div>
            <div v-if="detail.submitDate" class="t-item done">
              <div class="t">提交申请</div>
              <div class="m">{{ detail.applicant?.name || '-' }} · {{ detail.submitDate?.replace('T', ' ').substring(0, 19) || '-' }}</div>
              <div class="d">提交审批</div>
            </div>
            <div v-if="statusLabel === '已通过'" class="t-item done">
              <div class="t">审批通过</div>
              <div class="m">{{ detail.updatedAt?.replace('T', ' ').substring(0, 19) || '-' }}</div>
            </div>
            <div v-if="statusLabel === '已驳回'" class="t-item reject">
              <div class="t">已驳回</div>
              <div class="m">{{ detail.updatedAt?.replace('T', ' ').substring(0, 19) || '-' }}</div>
            </div>
            <div v-if="statusLabel === '已报销'" class="t-item done">
              <div class="t">已报销完成</div>
              <div class="m">{{ detail.updatedAt?.replace('T', ' ').substring(0, 19) || '-' }}</div>
              <div class="d">款项已支付，流程完结</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="form-foot">
      <div class="ff-left">
        <button class="ff-back" @click="goBack">
          <span class="ff-arrow">←</span>
          <span>返回列表</span>
        </button>
      </div>
      <div class="ff-right">
        <span class="ff-tip">💡 提示：可对上方 Tab 内容继续操作；本单据状态：<b>{{ statusLabel }}</b></span>
      </div>
    </div>
  </div>

  <!-- 费用明细编辑弹窗 -->
<!-- 关联发票弹窗 -->
<el-dialog
  v-model="linkInvoiceDialog"
  title="🔗 关联识别发票"
  width="780px"
  :close-on-click-modal="false"
  custom-class="link-invoice-dialog"
>
  <div class="li-search">
    <el-input v-model="linkKeyword" placeholder="搜索发票号 / 销售方 / 金额" clearable @input="searchInvoices" @clear="searchInvoices">
      <template #prefix><span style="padding:0 4px">🔍</span></template>
    </el-input>
    <span class="li-hint">仅显示未关联其他费用的发票</span>
  </div>
  <div class="li-list" v-loading="linkSearching">
    <div v-if="!linkCandidates.length" class="li-empty">没有可关联的发票</div>
    <div v-for="inv in linkCandidates" :key="inv.invoiceId" class="li-item" :class="{ selected: pickedInvoiceId === inv.invoiceId }" @click="pickedInvoiceId = inv.invoiceId">
      <div class="lii-icon">📄</div>
      <div class="lii-main">
        <div class="lii-title">{{ inv.invoiceType || '发票' }} · {{ inv.sellerName || '未知销售方' }}</div>
        <div class="lii-meta">
          <span>发票号 {{ inv.invoiceNo }}</span>
          <span class="lii-dot">·</span>
          <span>开票日期 {{ inv.issueDate }}</span>
          <span class="lii-dot">·</span>
          <span class="lii-amt">¥ {{ Number(inv.totalAmount).toFixed(2) }}</span>
        </div>
      </div>
      <div class="lii-radio">{{ pickedInvoiceId === inv.invoiceId ? '●' : '○' }}</div>
    </div>
  </div>
  <template #footer>
    <el-button @click="linkInvoiceDialog = false">取消</el-button>
    <el-button type="primary" :disabled="!pickedInvoiceId" :loading="linkSubmitting" @click="confirmLinkInvoice">确认关联</el-button>
  </template>
</el-dialog>

<el-dialog
  v-model="breakdownDialogVisible"
  width="780px"
  :close-on-click-modal="false"
  custom-class="breakdown-dialog"
  align-center
>
  <template #header>
    <div class="bd-dialog-header">
      <div class="bd-title-icon">📦</div>
      <div class="bd-title-text">
        <div class="bd-title-main">编辑费用明细</div>
        <div class="bd-title-sub">逐项录入金额，保存后将自动汇总到报销总额</div>
      </div>
    </div>
  </template>

  <div class="bd-banner">
    <span class="bd-banner-icon">💡</span>
    <span class="bd-banner-text">示例：差旅=机票+酒店+打车+餐补；招待=餐饮+酒水</span>
  </div>

  <div class="bd-table-wrap">
    <div class="bd-table-head">
      <div class="bd-col bd-col-idx">序号</div>
      <div class="bd-col bd-col-label">费用项目</div>
      <div class="bd-col bd-col-amount">金额（元）</div>
      <div class="bd-col bd-col-remark">备注</div>
      <div class="bd-col bd-col-action">操作</div>
    </div>
    <div
      v-for="(it, i) in breakdownDraft"
      :key="i"
      class="bd-table-row"
    >
      <div class="bd-col bd-col-idx">
        <span class="bd-idx-chip">{{ i + 1 }}</span>
      </div>
      <div class="bd-col bd-col-label">
        <input v-model="it.label" class="bd-input" placeholder="如：机票 / 酒店 / 餐补" maxlength="32" />
      </div>
      <div class="bd-col bd-col-amount">
        <span class="bd-amount-prefix">¥</span>
        <input v-model.number="it.amount" type="number" step="0.01" min="0" class="bd-input bd-num" placeholder="0.00" />
      </div>
      <div class="bd-col bd-col-remark">
        <input v-model="it.remark" class="bd-input" placeholder="可选" />
      </div>
      <div class="bd-col bd-col-action">
        <button class="bd-icon-btn" type="button" title="删除该行" @click="removeBreakdownRow(i)">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path><path d="M10 11v6"></path><path d="M14 11v6"></path><path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"></path></svg>
        </button>
      </div>
    </div>

    <div v-if="breakdownDraft.length === 0" class="bd-empty">
      <div class="bd-empty-icon">📝</div>
      <div class="bd-empty-text">还没有明细，点击下方「添加明细」开始录入</div>
    </div>
  </div>

  <div class="bd-add-row">
    <button type="button" class="bd-add-btn" @click="addBreakdownRow">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
      添加明细
    </button>
  </div>

  <div class="bd-summary">
    <div class="bd-summary-label">合计金额</div>
    <div class="bd-summary-value">
      <span class="bd-summary-currency">¥</span>
      <span class="bd-summary-num">{{ breakdownDraft.reduce((s: number, r: any) => s + (Number(r.amount) || 0), 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
    </div>
  </div>

  <template #footer>
    <div class="bd-footer">
      <el-button class="bd-btn-cancel" @click="cancelBreakdown">取消</el-button>
      <el-button class="bd-btn-save" type="primary" :loading="breakdownSaving" @click="saveBreakdown">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px;vertical-align:-2px;"><polyline points="20 6 9 17 4 12"></polyline></svg>
        保存明细
      </el-button>
    </div>
  </template>
</el-dialog>

<!-- 打印预览（@media print 时只显示这个 dialog） -->
  <el-dialog
    v-model="printVisible"
    title="🖨 打印预览 · 费用报销申请单"
    width="820px"
    :close-on-click-modal="false"
    append-to-body
    class="expense-print-dialog"
  >
    <div class="print-toolbar no-print">
      <el-button type="primary" @click="doPrint">🖨 立即打印</el-button>
      <el-button @click="printVisible = false">关闭</el-button>
      <span class="print-tip">建议使用 A4 纸张 · 边距「最小」</span>
    </div>

    <div class="print-page" id="expense-print-area">
      <!-- 表头 -->
      <div class="pp-header">
        <div class="pp-company">数智化管理系统</div>
        <h1 class="pp-title">费用报销申请单</h1>
        <div class="pp-code">申请单号：<b>{{ detail.code || '—' }}</b></div>
      </div>

      <!-- 基础信息 -->
      <table class="pp-table">
        <tbody>
          <tr>
            <th class="pp-th w-100">申请人</th><td class="pp-td">{{ detail.applicant?.name || '-' }}</td>
            <th class="pp-th w-100">部门</th><td class="pp-td">{{ detail.department?.name || '-' }}</td>
          </tr>
          <tr>
            <th class="pp-th">费用类型</th><td class="pp-td">{{ typeLabel }}</td>
            <th class="pp-th">币种</th><td class="pp-td">{{ detail.currency || 'CNY' }}</td>
          </tr>
          <tr>
            <th class="pp-th">费用日期</th><td class="pp-td">{{ formattedExpenseDate }}</td>
            <th class="pp-th">提交日期</th><td class="pp-td">{{ detail.submitDate || '未提交' }}</td>
          </tr>
          <tr>
            <th class="pp-th">关联合同</th><td class="pp-td">{{ detail.contractId ? '#' + detail.contractId : '—' }}</td>
            <th class="pp-th">关联项目</th><td class="pp-td">{{ detail.projectId ? '#' + detail.projectId : '—' }}</td>
          </tr>
          <tr>
            <th class="pp-th">标题</th>
            <td class="pp-td" colspan="3">{{ detail.title || '—' }}</td>
          </tr>
          <tr v-if="detail.description">
            <th class="pp-th">事由说明</th>
            <td class="pp-td" colspan="3">{{ detail.description }}</td>
          </tr>
        </tbody>
      </table>

      <!-- 费用明细 -->
      <h3 class="pp-h3">一、费用明细</h3>
      <table class="pp-table">
        <thead>
          <tr>
            <th class="pp-th" style="width:40px">序号</th>
            <th class="pp-th">费用项目</th>
            <th class="pp-th" style="width:80px">数量</th>
            <th class="pp-th" style="width:80px">单价(元)</th>
            <th class="pp-th" style="width:100px">金额(元)</th>
            <th class="pp-th">备注</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(it, i) in (detail.breakdown || [])" :key="i">
            <td class="pp-td center">{{ i + 1 }}</td>
            <td class="pp-td">{{ it.item || it.name || '—' }}</td>
            <td class="pp-td right">{{ it.qty || it.quantity || '—' }}</td>
            <td class="pp-td right">{{ it.price || it.unitPrice || '—' }}</td>
            <td class="pp-td right">{{ it.amount || '—' }}</td>
            <td class="pp-td">{{ it.remark || it.note || '—' }}</td>
          </tr>
          <tr v-if="!detail.breakdown?.length">
            <td class="pp-td center" colspan="6">（无费用明细）</td>
          </tr>
          <tr class="pp-total-row">
            <td class="pp-td" colspan="4" style="text-align:right;font-weight:600">合计（大写）：</td>
            <td class="pp-td right"><b>{{ formattedAmount }}</b></td>
            <td class="pp-td"></td>
          </tr>
        </tbody>
      </table>

      <!-- 审批流 -->
      <h3 class="pp-h3">二、审批流程</h3>
      <table class="pp-table">
        <thead>
          <tr>
            <th class="pp-th" style="width:40px">步骤</th>
            <th class="pp-th">审批节点</th>
            <th class="pp-th" style="width:90px">审批人</th>
            <th class="pp-th" style="width:90px">操作</th>
            <th class="pp-th" style="width:130px">时间</th>
            <th class="pp-th">意见</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(step, i) in (detail.approvalFlow?.steps || [])" :key="i">
            <td class="pp-td center">{{ step.seq || (i+1) }}</td>
            <td class="pp-td">{{ step.name || `第${i+1}步` }}</td>
            <td class="pp-td center">{{ step.approverName || (step.approverId ? '用户 #' + step.approverId : '系统') }}</td>
            <td class="pp-td center">{{ _actionLabel(step.action) || _stepStatusLabel(step.status) }}</td>
            <td class="pp-td center">{{ step.finishedAt ? String(step.finishedAt).replace('T',' ').substring(0,16) : '—' }}</td>
            <td class="pp-td">{{ step.comment || '—' }}</td>
          </tr>
          <tr v-if="!detail.approvalFlow?.steps?.length">
            <td class="pp-td center" colspan="6">（无审批记录 / 草稿状态）</td>
          </tr>
        </tbody>
      </table>

      <!-- 签字栏 -->
      <h3 class="pp-h3">三、签字确认</h3>
      <table class="pp-table pp-sign-table">
        <tbody>
          <tr>
            <th class="pp-th" style="height:80px">申请人签字</th>
            <td class="pp-td sign-cell"></td>
            <th class="pp-th" style="width:100px">日期</th>
            <td class="pp-td" style="width:140px"></td>
          </tr>
          <tr>
            <th class="pp-th" style="height:80px">部门负责人</th>
            <td class="pp-td sign-cell"></td>
            <th class="pp-th">日期</th>
            <td class="pp-td"></td>
          </tr>
          <tr>
            <th class="pp-th" style="height:80px">财务审核</th>
            <td class="pp-td sign-cell"></td>
            <th class="pp-th">日期</th>
            <td class="pp-td"></td>
          </tr>
        </tbody>
      </table>

      <div class="pp-footer">
        <span>打印时间：{{ new Date().toLocaleString('zh-CN') }}</span>
        <span>本单一式三份：申请人 / 财务 / 归档</span>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped lang="scss">
/* ============ expense-hero（R18 重设计：清爽+卡片化按钮） ============ */
.expense-hero {
  display: flex; justify-content: space-between; align-items: stretch;
  padding: 28px 32px;
  background: linear-gradient(135deg, #F8FAFF 0%, #EEF2FF 100%);
  border-radius: 16px;
  margin-bottom: 18px;
  position: relative;
  overflow: hidden;
}
.expense-hero::before {
  content: ""; position: absolute; right: -60px; top: -60px;
  width: 220px; height: 220px;
  background: radial-gradient(circle, rgba(79,107,255,0.08) 0%, transparent 70%);
  pointer-events: none;
}
.eh-left { flex: 1; min-width: 0; }
.eh-id { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.eh-id .code {
  font-family: 'SF Mono', Menlo, monospace;
  color: #6b7280; font-size: 12px;
  background: #FFFFFF;
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid #E5E7EB;
  letter-spacing: 0.3px;
}
.eh-title {
  font-size: 22px; font-weight: 600;
  margin: 4px 0 12px;
  color: #0F172A;
  line-height: 1.4;
  letter-spacing: -0.2px;
}
.eh-meta { color: #64748B; font-size: 13px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.eh-meta .sep { color: #CBD5E1; margin: 0 2px; }

.eh-right {
  text-align: right;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: space-between;
  position: relative;
  z-index: 1;
  padding-left: 24px;
}
.eh-amount-l { color: #64748B; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500; }
.eh-amount {
  font-size: 32px; font-weight: 700; color: #4F6BFF;
  margin: 4px 0 2px;
  font-family: 'SF Mono', Menlo, monospace;
  line-height: 1.1;
  letter-spacing: -0.5px;
}
.eh-amount-c { color: #94A3B8; font-size: 12px; margin-bottom: 14px; }

/* 按钮区 */
.eh-actions {
  display: flex; gap: 8px; justify-content: flex-end;
  flex-wrap: wrap;
}
.eh-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s ease;
  font-family: inherit;
  line-height: 1;
  white-space: nowrap;
  border: 1px solid transparent;
}
.eh-btn svg { flex-shrink: 0; }
.eh-btn-default {
  background: #FFFFFF;
  color: #475569;
  border-color: #E2E8F0;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.eh-btn-default:hover {
  background: #F8FAFC;
  color: #0F172A;
  border-color: #CBD5E1;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.08);
}
.eh-btn-default:active { transform: translateY(0); }
.eh-btn-primary {
  background: linear-gradient(135deg, #4F6BFF 0%, #3D5BE0 100%);
  color: #FFFFFF;
  border-color: transparent;
  box-shadow: 0 2px 6px rgba(79, 107, 255, 0.25);
}
.eh-btn-primary:hover {
  box-shadow: 0 6px 16px rgba(79, 107, 255, 0.35);
  transform: translateY(-1px);
}
.eh-btn-primary:active { transform: translateY(0); }
.eh-status-done {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  color: #047857;
  background: #ECFDF5;
  border: 1px solid #A7F3D0;
}
.detail-tabs { display: flex; gap: 24px; border-bottom: 1px solid #e5e7eb; margin-bottom: 16px; }
.detail-tabs a { padding: 12px 4px; color: #6b7280; cursor: pointer; text-decoration: none; border-bottom: 2px solid transparent; font-size: 14px; }
.detail-tabs a.active { color: #4f6bff; border-bottom-color: #4f6bff; font-weight: 600; }
.detail-layout { display: flex; flex-direction: column; gap: 16px; }
.detail-section { background: #fff; border-radius: 14px; padding: 22px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 1px 2px rgba(15, 23, 42, 0.02); transition: box-shadow .2s ease; }
.detail-section:hover { box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06), 0 2px 4px rgba(15, 23, 42, 0.03); }
.detail-section-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; padding-bottom: 12px; border-bottom: 1px solid #f3f4f6; }
.detail-section-head h3 { font-size: 15px; font-weight: 600; color: #111827; margin: 0; display: flex; align-items: center; gap: 6px; }
.info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px 24px; }
.info-row { display: flex; padding: 8px 0; border-bottom: 1px solid #f3f4f6; }
.info-row .l { width: 100px; color: #6b7280; font-size: 13px; }
.info-row .v { flex: 1; color: #111827; font-size: 13px; }
.info-row .v.mono { font-family: 'SF Mono', monospace; }
.info-row .v.amount { color: #4f6bff; font-weight: 600; }
.expense-table { width: 100%; border-collapse: collapse; }
.expense-table th, .expense-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #f3f4f6; font-size: 13px; }
.expense-table th { background: #f9fafb; color: #6b7280; font-weight: 500; }
.cell-amount { font-family: 'SF Mono', monospace; text-align: right; }
.empty-tip { padding: 24px; text-align: center; color: #9ca3af; font-size: 13px; }
.description { color: #374151; line-height: 1.6; font-size: 14px; white-space: pre-wrap; }
.approval-flow { display: flex; flex-direction: column; gap: 12px; }
.flow-summary { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: linear-gradient(135deg, #f0f5ff 0%, #faf5ff 100%); border-radius: 8px; flex-wrap: wrap; }
.flow-summary .fs-tag { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.flow-summary .fs-tag.flow-status-in_progress { background: #fef3c7; color: #92400e; }
.flow-summary .fs-tag.flow-status-approved { background: #d1fae5; color: #065f46; }
.flow-summary .fs-tag.flow-status-rejected { background: #fee2e2; color: #991b1b; }
.flow-summary .fs-tag.flow-status-transferred { background: #dbeafe; color: #1e40af; }
.flow-summary .fs-text { color: #374151; font-size: 13px; }
.flow-summary .fs-time { color: #6b7280; font-size: 12px; }
.flow-step { display: flex; align-items: flex-start; gap: 14px; padding: 14px; background: #f9fafb; border-radius: 8px; border-left: 3px solid #e5e7eb; }
.flow-step.flow-step-done { border-left-color: #10b981; background: #f0fdf4; }
.flow-step.flow-step-approved { border-left-color: #10b981; background: #f0fdf4; }
.flow-step.flow-step-rejected { border-left-color: #ef4444; background: #fef2f2; }
.flow-step.flow-step-current { border-left-color: #f59e0b; background: #fffbeb; box-shadow: 0 0 0 2px rgba(245,158,11,0.12); }
.flow-step.flow-step-todo { border-left-color: #d1d5db; background: #f9fafb; opacity: 0.85; }
.flow-step.flow-step-transferred { border-left-color: #3b82f6; background: #eff6ff; }
.flow-step-num { width: 32px; height: 32px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; background: #fff; border: 1px solid #e5e7eb; border-radius: 50%; font-weight: 600; color: #6b7280; font-size: 14px; }
.flow-step.flow-step-current .flow-step-num { background: #fef3c7; border-color: #f59e0b; color: #92400e; }
.flow-step.flow-step-done .flow-step-num, .flow-step.flow-step-approved .flow-step-num { background: #d1fae5; border-color: #10b981; color: #065f46; }
.flow-step.flow-step-rejected .flow-step-num { background: #fee2e2; border-color: #ef4444; color: #991b1b; }
.flow-step-body { flex: 1; min-width: 0; }
.flow-step-head { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.flow-step-name { font-weight: 600; color: #111827; font-size: 14px; }
.flow-step-meta { color: #6b7280; font-size: 12.5px; line-height: 1.7; }
.flow-step-meta b { color: #374151; font-weight: 500; }
.flow-step-comment { margin-top: 6px; padding: 6px 10px; background: #fff; border: 1px dashed #d1d5db; border-radius: 6px; color: #4b5563; font-size: 12.5px; }
.flow-state { padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
.flow-done { background: #d1fae5; color: #065f46; }
.flow-current { background: #fef3c7; color: #92400e; }
.flow-todo { background: #f3f4f6; color: #6b7280; }
.flow-meta { color: #6b7280; font-size: 13px; }
.approval-actions { display: flex; gap: 8px; align-items: center; margin-top: 16px; padding-top: 16px; border-top: 1px solid #f3f4f6; }
.flow-tip { margin-left: 8px; color: #9ca3af; font-size: 12px; }
.related-actions { display: flex; align-items: center; gap: 8px; }
.ff-link { padding: 6px 14px; border-radius: 8px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #fff; border: none; cursor: pointer; font-size: 12px; font-weight: 500; box-shadow: 0 2px 6px rgba(99, 102, 241, 0.25); transition: all .15s ease; }
.ff-link:hover { transform: translateY(-1px); box-shadow: 0 4px 10px rgba(99, 102, 241, 0.35); }
.ri-unlink { margin-left: 4px; padding: 3px 10px; border-radius: 6px; background: transparent; color: #6b7280; border: 1px solid #e5e7eb; cursor: pointer; font-size: 11px; opacity: 0; transition: all .15s; }
.ri-invoice:hover .ri-unlink { opacity: 1; }
.ri-unlink:hover { background: #fee2e2; color: #dc2626; border-color: #fca5a5; }
.li-search { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.li-hint { color: #9ca3af; font-size: 12px; }
.li-list { max-height: 480px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
.li-empty { padding: 40px; text-align: center; color: #9ca3af; font-size: 13px; }
.li-item { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border: 1px solid #e5e7eb; border-radius: 10px; cursor: pointer; transition: all .15s; }
.li-item:hover { border-color: #c7d2fe; background: #f8faff; }
.li-item.selected { border-color: #6366f1; background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%); box-shadow: 0 2px 8px rgba(99, 102, 241, 0.15); }
.lii-icon { font-size: 24px; }
.lii-main { flex: 1; min-width: 0; }
.lii-title { font-size: 13px; font-weight: 500; color: #111827; margin-bottom: 2px; }
.lii-meta { display: flex; align-items: center; gap: 6px; color: #6b7280; font-size: 12px; flex-wrap: wrap; }
.lii-dot { color: #d1d5db; }
.lii-amt { color: #4f6bff; font-weight: 600; }
.lii-radio { font-size: 18px; color: #6366f1; }
.related-list { display: flex; flex-direction: column; gap: 10px; }
.audit-bar { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-radius: 10px; border: 1px solid; font-size: 12px; margin-top: -4px; }
.audit-match { background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border-color: #6ee7b7; color: #065f46; }
.audit-partial { background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); border-color: #fcd34d; color: #92400e; }
.audit-over, .audit-mismatch { background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); border-color: #fca5a5; color: #991b1b; }
.audit-unknown { background: #f3f4f6; border-color: #e5e7eb; color: #6b7280; }
.ab-icon { font-size: 18px; line-height: 1; }
.ab-main { flex: 1; min-width: 0; }
.ab-title { font-weight: 600; margin-bottom: 2px; }
.ab-title b { font-weight: 700; }
.ab-reason { opacity: 0.85; line-height: 1.5; }
.ab-actions { display: flex; align-items: center; }
.ab-tip { padding: 2px 10px; background: rgba(255, 255, 255, 0.6); border-radius: 12px; font-size: 11px; font-weight: 500; }
.related-item { display: flex; align-items: center; gap: 14px; padding: 14px 16px; background: #fff; border-radius: 12px; border: 1px solid #e5e7eb; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03); transition: all .2s ease; }
.related-item:hover { border-color: #c7d2fe; box-shadow: 0 4px 12px rgba(79, 102, 241, 0.1); }
.ri-invoice { cursor: pointer; }
.ri-invoice:hover { background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%); transform: translateX(3px); }
.ri-type { padding: 4px 12px; background: #4f6bff; color: #fff; border-radius: 8px; font-size: 12px; white-space: nowrap; font-weight: 500; box-shadow: 0 1px 2px rgba(79, 107, 255, 0.2); }
.ri-type-invoice { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); box-shadow: 0 2px 6px rgba(99, 102, 241, 0.25); }
.ri-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.ri-name { color: #111827; font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ri-meta { display: flex; align-items: center; gap: 6px; color: #6b7280; font-size: 12px; flex-wrap: wrap; }
.ri-no { font-family: 'SF Mono', monospace; }
.ri-dot { color: #d1d5db; }
.ri-amt { color: #4f6bff; font-weight: 600; }
.ri-status { padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; white-space: nowrap; }
.rs-pending { background: #fef3c7; color: #92400e; }
.rs-verified { background: #d1fae5; color: #065f46; }
.rs-rejected { background: #fee2e2; color: #991b1b; }
.rs-failed, .rs-expired { background: #f3f4f6; color: #6b7280; }
.ri-arrow { color: #4f6bff; font-size: 13px; font-weight: 500; opacity: 0; transition: opacity .15s; }
.ri-invoice:hover .ri-arrow { opacity: 1; }
.empty-related { display: flex; flex-direction: column; align-items: center; padding: 48px 20px; background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 100%); border-radius: 14px; border: 1px dashed #c7d2fe; position: relative; overflow: hidden; }
.empty-related::before { content: ''; position: absolute; top: -50%; right: -20%; width: 200px; height: 200px; background: radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 70%); pointer-events: none; }
.er-icon { font-size: 40px; margin-bottom: 10px; opacity: 0.5; position: relative; }
.er-title { font-size: 15px; color: #374151; font-weight: 600; margin-bottom: 6px; position: relative; }
.er-desc { font-size: 12px; color: #6b7280; text-align: center; line-height: 1.7; position: relative; max-width: 360px; }
.timeline-det { display: flex; flex-direction: column; gap: 16px; }
.t-item { padding-left: 16px; border-left: 2px solid #e5e7eb; }
.t-item.done { border-left-color: #10b981; }
.t-item.reject { border-left-color: #ef4444; }
.t-item .t { font-weight: 600; color: #111827; font-size: 14px; }
.t-item .m { color: #6b7280; font-size: 12px; margin: 4px 0; }
.t-item .d { color: #4b5563; font-size: 13px; }
.tag { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }
.tag-info { background: #dbeafe; color: #1e40af; }
.tag-warning { background: #fef3c7; color: #92400e; }
.tag-success { background: #d1fae5; color: #065f46; }
.tag-danger { background: #fee2e2; color: #991b1b; }
.tag-primary { background: #e0e7ff; color: #3730a3; }
.tag-purple { background: #ede9fe; color: #5b21b6; }
.tag-cyan { background: #cffafe; color: #155e75; }
.tag-gray { background: #f3f4f6; color: #4b5563; }
.btn { padding: 6px 14px; border-radius: 6px; border: 1px solid transparent; cursor: pointer; font-size: 13px; }
.btn-ghost { background: transparent; color: #4b5563; border-color: #d1d5db; }
.btn-outline { background: #fff; color: #4b5563; border-color: #d1d5db; }
.btn-outline.danger { color: #dc2626; border-color: #fca5a5; }
.btn-primary { background: #4f6bff; color: #fff; }
.btn-sm { padding: 4px 12px; font-size: 12px; }
.form-foot { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 16px 20px; background: linear-gradient(180deg, rgba(255,255,255,0.6) 0%, #fff 100%); border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04); margin-top: 8px; }
.ff-left, .ff-right { display: flex; align-items: center; }
.ff-back { display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 8px; background: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; cursor: pointer; font-size: 13px; font-weight: 500; transition: all .15s ease; }
.ff-back:hover { background: #e5e7eb; color: #111827; transform: translateX(-2px); }
.ff-arrow { font-size: 16px; line-height: 1; transition: transform .2s; }
.ff-back:hover .ff-arrow { transform: translateX(-3px); }
.ff-tip { color: #6b7280; font-size: 12px; }
.ff-tip b { color: #4f6bff; font-weight: 600; }
.link-primary { color: #4f6bff; cursor: pointer; }
.link-btn { background: none; border: none; padding: 0; font: inherit; }
/* ================= 打印预览样式 ================= */
.print-toolbar { display: flex; align-items: center; gap: 8px; padding-bottom: 12px; border-bottom: 1px solid #E2E8F0; margin-bottom: 16px; }
.print-tip { color: #64748B; font-size: 12px; margin-left: auto; }
.print-page { background: #fff; padding: 32px 40px; color: #0F172A; font-size: 13px; line-height: 1.6; }
.pp-header { text-align: center; margin-bottom: 20px; border-bottom: 2px solid #0F172A; padding-bottom: 12px; }
.pp-company { font-size: 14px; color: #64748B; margin-bottom: 4px; }
.pp-title { font-size: 22px; font-weight: 700; margin: 0 0 6px 0; letter-spacing: 4px; }
.pp-code { font-size: 12px; color: #64748B; }
.pp-h3 { font-size: 14px; font-weight: 600; margin: 18px 0 8px 0; padding-left: 8px; border-left: 3px solid #4F6BFF; }
.pp-table { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
.pp-th { background: #F1F5F9; border: 1px solid #CBD5E1; padding: 6px 10px; text-align: left; font-weight: 600; font-size: 12px; }
.pp-td { border: 1px solid #CBD5E1; padding: 6px 10px; font-size: 12px; }
.pp-td.center { text-align: center; }
.pp-td.right { text-align: right; font-family: $font-family-mono; }
.pp-total-row td { background: #F8FAFC; }
.pp-sign-table .sign-cell { height: 80px; }
.pp-footer { display: flex; justify-content: space-between; margin-top: 24px; padding-top: 12px; border-top: 1px dashed #CBD5E1; font-size: 11px; color: #64748B; }

.w-100 { width: 100px; }

/* @media print：只显示打印区，隐藏所有 chrome */
@media print {
  body { background: #fff !important; }
  body * { visibility: hidden !important; }
  #expense-print-area, #expense-print-area * { visibility: visible !important; }
  .expense-print-dialog { box-shadow: none !important; }
  .expense-print-dialog .el-dialog__header,
  .expense-print-dialog .el-dialog__body { padding: 0 !important; }
  .expense-print-dialog .el-dialog__body { overflow: visible !important; }
  .no-print { display: none !important; }
  .print-page { padding: 0 !important; }
  @page { size: A4; margin: 12mm; }
}

/* ================ 费用明细编辑弹窗（R18 重设计） ================ */
.breakdown-dialog {
  border-radius: 14px !important;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.18), 0 0 0 1px rgba(15, 23, 42, 0.04) !important;
}
.breakdown-dialog .el-dialog__header {
  padding: 22px 28px 18px !important;
  border-bottom: 1px solid #F1F5F9;
  margin-right: 0 !important;
  background: linear-gradient(180deg, #FAFBFF 0%, #FFFFFF 100%);
}
.breakdown-dialog .el-dialog__headerbtn {
  top: 22px !important;
  right: 22px !important;
  width: 28px; height: 28px;
  border-radius: 6px;
  background: #F1F5F9;
  transition: all 0.15s;
}
.breakdown-dialog .el-dialog__headerbtn:hover {
  background: #E2E8F0;
}
.breakdown-dialog .el-dialog__headerbtn .el-dialog__close {
  font-size: 14px;
  color: #64748B;
}
.breakdown-dialog .el-dialog__body {
  padding: 22px 28px 8px !important;
  background: #FFFFFF;
}
.breakdown-dialog .el-dialog__footer {
  padding: 14px 28px 22px !important;
  background: #FAFBFF;
  border-top: 1px solid #F1F5F9;
}

.bd-dialog-header {
  display: flex;
  align-items: center;
  gap: 14px;
}
.bd-title-icon {
  width: 40px; height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  box-shadow: 0 2px 6px rgba(79, 107, 255, 0.15);
}
.bd-title-text { line-height: 1.4; }
.bd-title-main {
  font-size: 16px; font-weight: 600; color: #0F172A;
  letter-spacing: 0.2px;
}
.bd-title-sub {
  font-size: 12px; color: #64748B; margin-top: 2px;
}

.bd-banner {
  display: flex; align-items: center;
  gap: 8px;
  padding: 10px 14px;
  margin-bottom: 16px;
  background: linear-gradient(90deg, #FFFBEB 0%, #FEF3C7 100%);
  border-left: 3px solid #F59E0B;
  border-radius: 6px;
  font-size: 12px;
  color: #92400E;
}
.bd-banner-icon { font-size: 14px; }
.bd-banner-text { flex: 1; }

.bd-table-wrap {
  border: 1px solid #E2E8F0;
  border-radius: 10px;
  overflow: hidden;
  background: #FFFFFF;
  margin-bottom: 12px;
}
.bd-table-head {
  display: grid;
  grid-template-columns: 56px 1fr 160px 1.4fr 60px;
  gap: 12px;
  padding: 12px 16px;
  background: #F8FAFC;
  border-bottom: 1px solid #E2E8F0;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  letter-spacing: 0.2px;
}
.bd-table-head .bd-col-amount { text-align: right; }
.bd-table-head .bd-col-action { text-align: center; }
.bd-table-row {
  display: grid;
  grid-template-columns: 56px 1fr 160px 1.4fr 60px;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid #F1F5F9;
  align-items: center;
  transition: background 0.15s;
}
.bd-table-row:hover { background: #FAFBFF; }
.bd-table-row:last-child { border-bottom: none; }
.bd-col { display: flex; align-items: center; }
.bd-col-amount { justify-content: flex-end; position: relative; }
.bd-col-action { justify-content: center; }
.bd-idx-chip {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px;
  border-radius: 50%;
  background: #EEF2FF;
  color: #4F6BFF;
  font-size: 12px; font-weight: 600;
}

.bd-input {
  width: 100%;
  border: 1px solid transparent;
  background: #F8FAFC;
  border-radius: 6px;
  padding: 7px 10px;
  font-size: 13px;
  color: #0F172A;
  transition: all 0.15s;
  font-family: inherit;
}
.bd-input:hover { border-color: #E2E8F0; background: #FFFFFF; }
.bd-input:focus {
  outline: none;
  border-color: #4F6BFF;
  background: #FFFFFF;
  box-shadow: 0 0 0 3px rgba(79, 107, 255, 0.12);
}
.bd-input::placeholder { color: #94A3B8; }

.bd-col-amount .bd-input { text-align: right; padding-right: 10px; }
.bd-amount-prefix {
  position: absolute;
  left: 10px;
  color: #94A3B8;
  font-size: 13px;
  pointer-events: none;
  font-family: 'SF Mono', Menlo, monospace;
}
.bd-col-amount .bd-input { padding-left: 22px; }
.bd-num { font-family: 'SF Mono', Menlo, monospace; }

.bd-icon-btn {
  width: 28px; height: 28px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #94A3B8;
  cursor: pointer;
  transition: all 0.15s;
}
.bd-icon-btn:hover {
  background: #FEE2E2;
  color: #DC2626;
}

.bd-empty {
  padding: 36px 16px;
  text-align: center;
}
.bd-empty-icon { font-size: 32px; opacity: 0.4; margin-bottom: 6px; }
.bd-empty-text { font-size: 13px; color: #94A3B8; }

.bd-add-row {
  margin-bottom: 14px;
}
.bd-add-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 14px;
  background: #FFFFFF;
  border: 1px dashed #CBD5E1;
  border-radius: 6px;
  color: #4F6BFF;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}
.bd-add-btn:hover {
  border-color: #4F6BFF;
  background: #EEF2FF;
  border-style: solid;
}

.bd-summary {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 14px 18px;
  background: linear-gradient(90deg, #EEF2FF 0%, #F5F7FF 100%);
  border: 1px solid #E0E7FF;
  border-radius: 10px;
  margin-bottom: 6px;
}
.bd-summary-label {
  font-size: 13px;
  color: #475569;
  font-weight: 500;
}
.bd-summary-value {
  display: flex; align-items: baseline; gap: 2px;
}
.bd-summary-currency {
  font-size: 14px;
  color: #4F6BFF;
  font-weight: 500;
  font-family: 'SF Mono', Menlo, monospace;
}
.bd-summary-num {
  font-size: 22px;
  font-weight: 600;
  color: #4F6BFF;
  font-family: 'SF Mono', Menlo, monospace;
  letter-spacing: 0.5px;
}

.bd-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.bd-btn-cancel {
  border-radius: 8px !important;
  padding: 9px 20px !important;
  font-weight: 500 !important;
}
.bd-btn-save {
  border-radius: 8px !important;
  padding: 9px 22px !important;
  font-weight: 500 !important;
  background: linear-gradient(135deg, #4F6BFF 0%, #3D5BE0 100%) !important;
  border: none !important;
  box-shadow: 0 2px 8px rgba(79, 107, 255, 0.3) !important;
}
.bd-btn-save:hover {
  box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4) !important;
  transform: translateY(-1px);
}

</style>
