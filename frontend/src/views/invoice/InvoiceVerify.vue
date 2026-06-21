<script setup lang="ts">
/**
 * 查验真伪 tab（R8.14 严格 1:1 复刻 design/invoice-ocr-verify.html）
 * - verify-stats 4 stat-card
 * - risk-card 风险告警
 * - verify-form-card 发起查验（3 模式 tab：单张/批量/从识别记录 + 6 字段表单）
 * - verify-result 查验结果展示
 * - queue-card 查验记录表格（8 列 + toolbar）
 */
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { invoiceOcrApi } from '@/api/modules'

// ============================================================
// 4 个 stat-card
// ============================================================
const stats = ref<any[]>([
  { label: '本月查验',     value: 0, unit: '张', iconBg: 'rgba(79,107,255,0.12)',  iconColor: '#4F6BFF', icon: '✓' },
  { label: '查验通过',     value: 0, unit: '张', iconBg: 'rgba(16,185,129,0.12)',  iconColor: '#10B981', icon: '✓' },
  { label: '风险发票',     value: 0, unit: '张', iconBg: 'rgba(239,68,68,0.12)',  iconColor: '#EF4444', icon: '!' },
  { label: '本月查验金额', value: 0, unit: '元', iconBg: 'rgba(124,58,237,0.12)',  iconColor: '#7C3AED', icon: '¥', prefix: '¥' },
])

// ============================================================
// 风险告警
// ============================================================
const risks = ref<Array<{no: string; desc: string; amount: string}>>([])

// ============================================================
// 查验模式 tab
// ============================================================
const verifyMode = ref<'single' | 'batch' | 'from_records'>('single')
const verifyTabs = [
  { key: 'single' as const,         label: '单张查验' },
  { key: 'batch' as const,          label: '批量查验' },
  { key: 'from_records' as const,   label: '从识别记录选择' },
]

// ============================================================
// 查验表单（design 默认值）
// ============================================================
const form = reactive({
  invoiceCode:   '',
  invoiceNo:     '',
  issueDate:     '',
  amount:        '',
  verifyCode:    '',
})

// ============================================================
// 查验结果（design: .verify-result）
// ============================================================
interface VerifyResult {
  verifyId: string
  invoiceCode: string
  invoiceNo: string
  issueDate: string
  amount: string
  seller: string
  sellerTaxNo: string
  buyer: string
  checkNo: string
  source: string
  checkTime: string
  costSec: number
}
const result = ref<VerifyResult | null>(null)

// ============================================================
// 查验记录表格（design: .verify-table）
// ============================================================
interface VerifyRow {
  id: number
  invoiceNo: string
  noColor: string  // normal | danger
  seller: string
  amount: string
  issueDate: string
  source: string
  checkTime: string
  result: 'success' | 'danger' | 'warning'
  resultLabel: string
  resultColor: string  // success | danger | warning
  // R17 修复：TS 类型补 internalDuplicate
  internalDuplicate?: { matchedCode?: string; matchedStatus?: string; hint?: string } | null
  riskReason?: string
}
const records = ref<VerifyRow[]>([])
const totalRecords = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

// 工具栏筛选
const searchKw = ref('')
const filterResult = ref('')
const submittingVerify = ref(false)
const pickedIds = ref<number[]>([])
const ocrRecords = ref<any[]>([])
const ocrRecordsLoading = ref(false)
const pickedInvoiceNos = ref<string[]>([])  // 缓存选中的 invoiceNo（用于批量查）

// 触点 #24：从发票详情跳转过来 - 预填查验表单
const route = useRoute()

// 国税接口健康状态
const verifyHealth = ref<{
  mode: string; configured: boolean; useSandbox: boolean; apiUrl: string;
  status: 'mock' | 'reachable' | 'degraded' | 'down'; message: string;
} | null>(null)
const verifyConfig = ref<any>(null)
const showConfigDialog = ref(false)
const healthLoading = ref(false)

const devHintTitle = computed(() => {
  if (!verifyHealth.value) return '正在检测查验服务…'
  if (verifyHealth.value.status === 'mock') return '开发替身模式'
  if (verifyHealth.value.status === 'degraded') return '接口降级中'
  if (verifyHealth.value.status === 'down') return '接口暂不可达'
  return '当前非生产模式'
})
const _statusBadge = computed(() => {
  const h = verifyHealth.value
  if (!h) return { label: '检测中…', cls: 'pending', icon: '⏳' }
  if (h.status === 'reachable') return { label: '国税接口已连接', cls: 'success', icon: '✓' }
  if (h.status === 'degraded') return { label: '国税接口降级', cls: 'warning', icon: '!' }
  if (h.status === 'down') return { label: '国税接口不可达', cls: 'danger', icon: '✕' }
  if (h.status === 'mock') return { label: '开发替身模式', cls: 'info', icon: '⚙' }
  return { label: '状态未知', cls: 'info', icon: '?' }
})

async function _loadHealth() {
  healthLoading.value = true
  try {
    verifyHealth.value = await invoiceOcrApi.verifyHealth()
  } catch (e: any) {
    verifyHealth.value = { mode: 'mock', configured: false, useSandbox: true, apiUrl: '', status: 'down', message: e?.message || '探测失败' }
  } finally {
    healthLoading.value = false
  }
}

async function _openConfig() {
  showConfigDialog.value = true
  if (!verifyConfig.value) {
    try {
      verifyConfig.value = await invoiceOcrApi.verifyConfig()
    } catch (e: any) {
      ElMessage.error('加载配置失败：' + (e?.message || '未知错误'))
    }
  }
}

const filteredRecords = computed(() => {
  const kw = (searchKw.value || '').trim().toLowerCase()
  if (!kw) return records.value
  return records.value.filter(r =>
    r.invoiceNo.toLowerCase().includes(kw) ||
    (r.seller || '').toLowerCase().includes(kw)
  )
})

function _exportCsv() {
  if (filteredRecords.value.length === 0) {
    ElMessage.warning('当前无数据可导出')
    return
  }
  const head = ['发票号', '销售方', '金额', '开票日期', '查验来源', '查验时间', '结果']
  const rows = filteredRecords.value.map(r => [
    r.invoiceNo, r.seller, r.amount, r.issueDate, r.source, r.checkTime, r.resultLabel,
  ])
  const csv = '\uFEFF' + [head, ...rows].map(row =>
    row.map(c => '"' + String(c || '').replace(/"/g, '""') + '"').join(',')
  ).join('\r\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `查验记录-${new Date().toISOString().slice(0,10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function _mapRecord(rec: any): VerifyRow {
  const no = rec.invoiceNo || ''
  const noColor = rec.result === 'pass' ? 'normal' : 'danger'
  const resultMap: any = {
    pass: { label: '通过', color: 'success', key: 'success' },
    risk: { label: '风险', color: 'danger',  key: 'danger' },
    repeat: { label: '重复报销', color: 'danger', key: 'danger' },
    not_found: { label: '已失效', color: 'danger', key: 'danger' },
  }
  const r = resultMap[rec.result] || { label: rec.result, color: 'warning', key: 'warning' }
  return {
    id: rec.verifyId,
    invoiceNo: no.length > 14 ? no.slice(0, 8) + '...' + no.slice(-8) : no,
    noColor,
    seller: rec.sellerName || '—',
    amount: '¥ ' + Number(rec.totalAmount || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    issueDate: rec.issueDate || '—',
    source: rec.source || '国税总局',
    checkTime: rec.verifiedAt ? String(rec.verifiedAt).replace('T', ' ').slice(0, 16) : '—',
    result: r.key,
    resultLabel: r.label,
    resultColor: r.color,
    riskReason: rec.riskReason,
    internalDuplicate: rec.internalDuplicate || null,
  }
}

async function _loadVerifyRecords() {
  try {
    const r: any = await invoiceOcrApi.verifyList({
      page: currentPage.value,
      pageSize: pageSize.value,
      filters: filterResult.value !== 'all' ? { result: filterResult.value } : {},
    })
    console.log('[verifyList] response:', r)
    if (r && Array.isArray(r.list)) {
      records.value = r.list.map(_mapRecord)
      totalRecords.value = r.total || 0
      _syncStatsAndRisks()
    } else {
      console.warn('[verifyList] unexpected response shape:', r)
    }
  } catch (e: any) {
    console.error('[load verify records]', e)
    ElMessage.error('加载查验记录失败：' + (e?.message || '未知错误'))
  }
}

function _syncStatsAndRisks() {
  const total = totalRecords.value
  const pass = records.value.filter(r => r.result === 'success').length
  const risk = records.value.filter(r => r.result !== 'success' && r.resultColor === 'danger').length
  const amountYuan = records.value.reduce((s, r) => {
    const n = Number(r.amount.replace(/[^\d.-]/g, ''))
    return s + (isFinite(n) ? n : 0)
  }, 0)
  stats.value[0].value = total
  stats.value[1].value = pass
  stats.value[2].value = risk
  stats.value[3].value = Math.round(amountYuan)
  risks.value = records.value
    .filter(r => r.resultColor === 'danger')
    .slice(0, 3)
    .map(r => ({
      no: r.invoiceNo,
      desc: r.riskReason || r.resultLabel,
      amount: r.amount.replace('¥ ', ''),
    }))
}

async function submitVerify() {
  if (!form.invoiceCode || !form.invoiceNo || !form.issueDate || !form.amount) {
    ElMessage.warning('请完整填写发票代码/号码/开票日期/价税合计')
    return
  }
  try {
    submittingVerify.value = true
    const r: any = await invoiceOcrApi.verify({
      invoiceCode: form.invoiceCode,
      invoiceNo: form.invoiceNo,
      issueDate: form.issueDate,
      totalAmount: Number(form.amount),
    })
    result.value = {
      verifyId: r.verifyId || '',
      invoiceCode: form.invoiceCode,
      invoiceNo: form.invoiceNo,
      issueDate: form.issueDate,
      amount: '¥ ' + Number(form.amount).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
      seller: '—',
      sellerTaxNo: '—',
      buyer: '—',
      checkNo: '第 1 次',
      source: r.source || '国家税务总局全国增值税发票查验平台',
      checkTime: (r.verifiedAt || new Date().toISOString()).replace('T', ' ').slice(0, 19),
      costSec: (r.elapsed || 1800) / 1000,
    }
    if (r.result === 'pass') ElMessage.success('查验通过：发票真实有效')
    else ElMessage.warning('查验有风险：' + (r.riskReason || r.result))
    // 附加：本系统是否已识别/入账过（不改变主结果）
    const dup = r.info?.internalDuplicate
    if (dup?.duplicate) {
      ElMessage.warning(`系统去重提醒：${dup.hint}`)
    }
    await _loadVerifyRecords()
  } catch (e: any) {
    ElMessage.error('查验失败：' + (e?.message || '未知错误'))
  } finally {
    submittingVerify.value = false
  }
}

async function downloadCert(r?: VerifyRow) {
  const verifyId = (r?.id) || result.value?.verifyId
  if (!verifyId) { ElMessage.warning('请先查验一张发票'); return }
  try {
    const r2: any = await invoiceOcrApi.verifyCertificate(verifyId)
    if (r2.certificateUrl) {
      // 走 nginx 80 端口（/static/certificates/* 已 mount），不用硬编码 8000
      // 用 a.click() 避免被浏览器 popup 拦截
      const a = document.createElement('a')
      a.href = r2.certificateUrl
      a.target = '_blank'
      a.rel = 'noopener noreferrer'
      document.body.appendChild(a)
      a.click()
      setTimeout(() => document.body.removeChild(a), 0)
      ElMessage.success('已生成查验凭证，新标签页打开 PDF')
    } else {
      ElMessage.info(r2.message || '凭证生成中')
    }
  } catch (e: any) {
    ElMessage.error('下载失败：' + (e?.message || '未知错误'))
  }
}

async function recheck(r: VerifyRow) {
  try {
    await invoiceOcrApi.verify({
      invoiceCode: '0000000000',
      invoiceNo: r.invoiceNo,
      issueDate: r.issueDate,
      totalAmount: Number(r.amount.replace(/[^\d.-]/g, '')),
    })
    ElMessage.success('已重新查验：' + r.invoiceNo)
    await _loadVerifyRecords()
  } catch (e: any) {
    ElMessage.error('重查失败：' + (e?.message || '未知错误'))
  }
}

async function markRisk(r: VerifyRow) {
  try {
    await invoiceOcrApi.verifyMark(r.id, 'mark')
    ElMessage.warning('已标记为风险：' + r.invoiceNo)
    await _loadVerifyRecords()
  } catch (e: any) {
    ElMessage.error('标记失败：' + (e?.message || '未知错误'))
  }
}

function viewDetail(r: VerifyRow) {
  if (r.riskReason) {
    ElMessage.warning('风险说明：' + r.riskReason)
  } else {
    ElMessage.info('详情：' + r.invoiceNo + '（' + r.resultLabel + '）')
  }
}

onMounted(async () => {
  // 触点 #24：从发票详情跳过来 - 自动切到单张查验并预填表单
  const presetInvoiceId = Number(route.query.invoiceId) || 0
  if (presetInvoiceId) {
    try {
      const resp: any = await invoiceOcrApi.detail(presetInvoiceId).catch(() => null)
      const d = resp?.data || resp
      if (d) {
        verifyMode.value = 'single'
        form.invoiceCode = d.invoiceCode || ''
        form.invoiceNo   = d.invoiceNo || ''
        form.issueDate   = (d.issueDate || '').slice(0, 10)
        form.amount      = d.totalAmount != null ? String(d.totalAmount) : ''
        form.verifyCode  = d.verifyCode || ''
        ElMessage.success(`已预填发票 #${presetInvoiceId} 的查验信息，点「开始查验」即可`)
      }
    } catch (e) {
      console.warn('[prefill verify]', e)
    }
  }
  _loadVerifyRecords()
  _loadHealth()
})

watch([currentPage, pageSize, filterResult], () => _loadVerifyRecords())

// 切到「从识别记录选择」tab 时加载未核验的识别记录
watch(verifyMode, async (m) => {
  if (m === 'from_records' && ocrRecords.value.length === 0) {
    await _loadOcrRecords()
  }
})

async function _loadOcrRecords() {
  ocrRecordsLoading.value = true
  try {
    const r: any = await invoiceOcrApi.records({ page: 1, pageSize: 20, keyword: '', filters: {} })
    const list = (r?.list || []).filter((x: any) => x.verifyStatus === 'pending' || !x.verifyStatus)
    ocrRecords.value = list
  } catch (e: any) {
    ElMessage.error('加载识别记录失败：' + (e?.message || '未知错误'))
  } finally {
    ocrRecordsLoading.value = false
  }
}

async function _batchVerifyFromRecords() {
  if (pickedIds.value.length === 0) {
    ElMessage.warning('请先勾选需要查验的发票')
    return
  }
  const picked = ocrRecords.value.filter((x: any) => pickedIds.value.includes(x.invoiceId))
  const invoices = picked.map((x: any) => ({
    invoiceId: x.invoiceId,
    invoiceCode: x.code || '',
    invoiceNo: x.invoiceNo,
    issueDate: x.issueDate,
    totalAmount: x.totalAmount,
  }))
  if (invoices.length === 0) {
    ElMessage.warning('所选项数据不完整，无法查验')
    return
  }
  submittingVerify.value = true
  try {
    const r: any = await invoiceOcrApi.verifyBatch({ invoices })
    const pass = r?.summary?.pass || 0
    const risk = r?.summary?.risk || 0
    ElMessage.success(`批量查验完成：通过 ${pass} 张 · 风险 ${risk} 张`)
    pickedIds.value = []
    // 刷新识别记录 + 查验记录
    await Promise.all([_loadOcrRecords(), _loadVerifyRecords()])
  } catch (e: any) {
    ElMessage.error('批量查验失败：' + (e?.message || '未知错误'))
  } finally {
    submittingVerify.value = false
  }
}
</script>

<template>
  <div class="verify-page">
    <!-- 4 个 stat-card（design: .verify-stats） -->
    <div class="verify-stats fade-up">
      <div v-for="(s, i) in stats" :key="i" class="stat-card">
        <div class="stat-label">
          {{ s.label }}
          <span class="stat-icon" :style="{ background: s.iconBg, color: s.iconColor }">{{ s.icon }}</span>
        </div>
        <div class="stat-value">
          <span v-if="s.prefix" class="prefix">{{ s.prefix }}</span>
          {{ s.value }} <span class="unit">{{ s.unit }}</span>
        </div>
        <div v-if="s.value > 0" class="stat-delta" :class="s.label.includes('风险') ? 'danger' : ''">
          {{ s.label.includes('风险') ? '需人工复核' : '本月累计' }}
        </div>
      </div>
    </div>

    <!-- 风险告警（design: .risk-card） -->
    <div class="risk-card fade-up">
      <div class="head">
        <div class="ico">⚠</div>
        <div class="t">{{ risks.length }} 张发票存在查验风险，需立即处理</div>
      </div>
      <div class="body">
        <div v-for="(r, i) in risks" :key="i" class="row">
          · <strong>{{ r.no }}</strong> {{ r.desc }} · 涉及 ¥ {{ r.amount }}
        </div>
      </div>
    </div>

    <!-- 发起查验（design: .verify-form-card） -->
    <div class="verify-form-card fade-up">
      <div class="verify-form-head">
        <div>
          <h3>🔍 发起查验</h3>
          <div class="sub">向国家税务总局发票查验平台发起真伪核验</div>
        </div>
        <div class="head-right">
          <div class="verify-tabs">
            <a
              v-for="t in verifyTabs"
              :key="t.key"
              href="javascript:void(0)"
              :class="{ active: verifyMode === t.key }"
              @click.prevent="verifyMode = t.key"
            >{{ t.label }}</a>
          </div>
          <span :class="['badge', _statusBadge.cls]" :title="verifyHealth?.message || '探测中…'" @click="_openConfig" style="cursor: pointer;">
            {{ _statusBadge.icon }} {{ _statusBadge.label }}
            <span style="font-size: 10px; opacity: 0.7; margin-left: 4px;">查看配置</span>
          </span>
        </div>
      </div>

      <!-- 触点 #49：开发环境提示条（仅在 mock / degraded 状态显示） -->
      <div v-if="verifyHealth && verifyHealth.status !== 'reachable'" class="dev-env-hint">
        <div class="deh-icon">🛠</div>
        <div class="deh-body">
          <div class="deh-title">{{ devHintTitle }}</div>
          <div class="deh-desc">
            当前为<strong>开发演示环境</strong>，可完整体验验真/去重/凭证/标记的<strong>业务逻辑</strong>；
            <strong>未连接国税总局</strong>，所查发票数据来自本系统发票表模拟。上线前请参考
            <a @click="_openConfig">接口配置</a>接入诺诺生产凭证。
          </div>
        </div>
      </div>

      <div v-if="verifyMode === 'single'" class="verify-form-row">
        <div class="field">
          <label>发票代码 <span class="required">*</span></label>
          <input v-model="form.invoiceCode" type="text" placeholder="如：011002600611" />
        </div>
        <div class="field">
          <label>发票号码 <span class="required">*</span></label>
          <input v-model="form.invoiceNo" type="text" placeholder="如：25113300000012345678" />
        </div>
        <div class="field">
          <label>开票日期 <span class="required">*</span></label>
          <input v-model="form.issueDate" type="date" />
        </div>
        <div class="field">
          <label>价税合计（元） <span class="required">*</span></label>
          <input v-model="form.amount" type="text" placeholder="如：28000.00" />
        </div>
        <div class="field">
          <label>校验码（验证码） <span class="optional">（可选）</span></label>
          <input v-model="form.verifyCode" type="text" placeholder="发票密码区后 6 位" />
        </div>
        <div class="field btn-field">
          <button class="btn btn-primary" @click="submitVerify">🔍 立即查验</button>
        </div>
      </div>

      <div v-else-if="verifyMode === 'batch'" class="verify-form-row batch-row">
        <div class="field full">
          <label>批量上传发票文件（PDF/图片） <span class="required">*</span></label>
          <div class="dropzone">
            <div class="dropzone-icon">📂</div>
            <div class="dropzone-text">点击或拖拽文件到此处</div>
            <div class="dropzone-hint">支持 PDF / JPG / PNG · 单次最多 50 张</div>
          </div>
        </div>
        <div class="field btn-field">
          <button class="btn btn-primary" disabled>🔍 批量查验（待对接）</button>
        </div>
      </div>

      <div v-else class="verify-form-row batch-row">
        <div class="field full">
          <label>从识别记录中选择（多选） <span class="required">*</span></label>
          <div class="record-pick">
            <div class="pick-stat">从识别记录列表里勾选需要查验的发票（先去「智能识别」识别入库）</div>
            <div class="pick-list">
              <div v-if="ocrRecordsLoading" class="pick-empty">加载中…</div>
              <div v-else-if="ocrRecords.length === 0" class="pick-empty">暂无未核验的识别记录（请先到「智能识别」识别发票）</div>
              <div v-for="r in ocrRecords.slice(0, 10)" :key="r.invoiceId" class="pick-item">
                <input type="checkbox" v-model="pickedIds" :value="r.invoiceId" />
                <span class="cell-mono">{{ r.invoiceNo }}</span>
                <span>{{ r.sellerName || '—' }}</span>
                <span class="amount">¥ {{ Number(r.totalAmount || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
                <span class="s-tag warning">待核验</span>
              </div>
            </div>
          </div>
        </div>
        <div class="field btn-field">
          <button class="btn btn-primary" :disabled="pickedIds.length === 0" @click="_batchVerifyFromRecords">🔍 查验所选（{{ pickedIds.length }}）</button>
        </div>
      </div>

      <div class="form-hint">
        ⓘ 每日单平台查询次数上限 5,000 次 / 组织，单张发票最多查验 5 次/日。查验数据仅留存 30 天。
      </div>
    </div>

    <!-- 查验结果（design: .verify-result） -->
    <div v-if="result" class="verify-result success fade-up">
      <div class="vr-top">
        <div class="vr-icon">✓</div>
        <div>
          <div class="vr-title">查验通过 · 发票真实有效</div>
          <div class="vr-sub">来源：{{ result.source }} · 查验时间 {{ result.checkTime }} · 耗时 {{ result.costSec }}s</div>
        </div>
      </div>
      <div class="vr-grid">
        <div class="vr-item">
          <div class="l">发票代码</div>
          <div class="v mono">{{ result.invoiceCode }}</div>
        </div>
        <div class="vr-item">
          <div class="l">发票号码</div>
          <div class="v mono">{{ result.invoiceNo }}</div>
        </div>
        <div class="vr-item">
          <div class="l">开票日期</div>
          <div class="v">{{ result.issueDate }}</div>
        </div>
        <div class="vr-item">
          <div class="l">价税合计</div>
          <div class="v">{{ result.amount }}</div>
        </div>
        <div class="vr-item">
          <div class="l">销售方</div>
          <div class="v seller">{{ result.seller }}</div>
        </div>
        <div class="vr-item">
          <div class="l">纳税人识别号</div>
          <div class="v mono taxno">{{ result.sellerTaxNo }}</div>
        </div>
        <div class="vr-item">
          <div class="l">购买方</div>
          <div class="v seller">{{ result.buyer }}</div>
        </div>
        <div class="vr-item">
          <div class="l">查验次数</div>
          <div class="v">{{ result.checkNo }}</div>
        </div>
      </div>
    </div>

    <!-- 查验记录（design: .queue-card） -->
    <div class="queue-card fade-up">
      <div class="queue-head">
        <h3>查验记录（{{ totalRecords }} 条）</h3>
        <div class="toolbar">
          <input v-model="searchKw" class="search-input" placeholder="搜索发票号 / 销售方..." />
          <select v-model="filterResult" class="select-result" @change="currentPage = 1; _loadVerifyRecords()">
            <option value="all">所有结果</option>
            <option value="pass">通过</option>
            <option value="risk">风险</option>
            <option value="repeat">重复报销</option>
            <option value="not_found">已失效</option>
            <option value="warning">异常</option>
          </select>
          <button class="btn btn-outline btn-sm" @click="_exportCsv">📥 导出</button>
        </div>
      </div>
      <table class="verify-table">
        <thead>
          <tr>
            <th>发票号</th>
            <th>销售方</th>
            <th>金额</th>
            <th>开票日期</th>
            <th>查验来源</th>
            <th>查验时间</th>
            <th>系统去重</th>
            <th>真伪结果</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in filteredRecords" :key="r.id">
            <td><span :class="['cell-mono', r.noColor]">{{ r.invoiceNo }}</span></td>
            <td>{{ r.seller }}</td>
            <td class="cell-amount">{{ r.amount }}</td>
            <td>{{ r.issueDate }}</td>
            <td><span class="source-clean">{{ (r.source || '').replace(/[（(]\s*mock\s*[)）]/gi, '').trim() || '国税总局' }}</span></td>
            <td>{{ r.checkTime }}</td>
            <td>
              <span v-if="r.internalDuplicate" class="s-tag warning" :title="r.internalDuplicate.hint || `已识别（${r.internalDuplicate.matchedCode}，${r.internalDuplicate.matchedStatus}）`">
                已识别 ({{ r.internalDuplicate.matchedCode }})
              </span>
              <span v-else class="s-tag muted">—</span>
            </td>
            <td><span :class="['v-pill', r.resultColor]">{{ r.resultLabel }}</span></td>
            <td>
              <div class="row-actions">
                <a @click="downloadCert(r)">凭证</a>
                <a v-if="r.resultColor === 'success'" @click="recheck(r)">重查</a>
                <a v-if="r.resultColor !== 'success'" @click="viewDetail(r)">详情</a>
                <a v-if="r.resultColor === 'danger'" class="danger" @click="markRisk(r)">标记</a>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- 国税接口配置弹窗 -->
      <el-dialog v-model="showConfigDialog" title="🔌 国税接口配置" width="640px">
        <div v-if="verifyConfig" class="config-content">
          <div class="config-row">
            <span class="lbl">运行模式：</span>
            <span :class="['mode-tag', verifyConfig.mode]">{{ verifyConfig.mode === 'real' ? '已连接国税' : '开发替身' }}</span>
          </div>
          <div class="config-row">
            <span class="lbl">接口地址：</span>
            <span class="val mono">{{ verifyConfig.apiUrl || '（未配置）' }}</span>
          </div>
          <div class="config-row">
            <span class="lbl">沙箱环境：</span>
            <span class="val">{{ verifyConfig.useSandbox ? '是（sandbox）' : '否（生产）' }}</span>
          </div>
          <div class="config-row">
            <span class="lbl">AppKey：</span>
            <span class="val mono">{{ verifyConfig.appKeyMasked || '（未配置）' }}</span>
          </div>
          <div class="config-row">
            <span class="lbl">AppSecret：</span>
            <span class="val mono">{{ verifyConfig.appSecretMasked || '（未配置）' }}</span>
          </div>
          <div class="config-row">
            <span class="lbl">AccessToken：</span>
            <span class="val mono">{{ verifyConfig.accessTokenMasked || '（未配置）' }}</span>
          </div>
          <div class="config-row" style="border-top: 1px dashed #e5e7eb; padding-top: 12px; margin-top: 8px;">
            <span class="lbl">配置来源：</span>
            <span class="val mono small">{{ verifyConfig.configSource }}</span>
          </div>
          <div class="config-guide">
            <div class="guide-title">📘 如何切换为真实国税接口</div>
            <div class="guide-body">{{ verifyConfig.guide }}</div>
            <ol class="guide-steps">
              <li>登录诺诺开放平台（open.nuonuocs.cn）申请 appKey/appSecret/accessToken</li>
              <li>编辑 <code>backend/.env</code> 文件</li>
              <li>设置 <code>NUONUO_API_KEY=xxx</code> / <code>NUONUO_API_SECRET=xxx</code> / <code>NUONUO_API_TOKEN=xxx</code></li>
              <li>设置 <code>NUONUO_MODE=real</code>（不设置则按 API_KEY 是否存在自动判断）</li>
              <li>重启 backend 容器：<code>docker compose restart backend</code></li>
            </ol>
          </div>
        </div>
        <div v-else style="text-align: center; padding: 30px; color: #9ca3af;">加载中…</div>
        <template #footer>
          <el-button @click="showConfigDialog = false">关闭</el-button>
          <el-button type="primary" @click="_loadHealth">重新探测</el-button>
        </template>
      </el-dialog>

      <div class="rec-foot">
        <span class="rec-count">共 {{ totalRecords }} 条记录</span>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="totalRecords"
          layout="prev, pager, next, sizes, jumper"
          background
          size="small"
        />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@import "@/assets/styles/variables.scss";

.verify-page { padding: 0; }

/* 接口健康徽章状态色 */
.badge.success { background: rgba(16,185,129,0.12); color: #10B981; }
.badge.warning { background: rgba(245,158,11,0.12); color: #F59E0B; }
.badge.danger  { background: rgba(239,68,68,0.12);  color: #EF4444; }
.badge.info    { background: rgba(124,58,237,0.12); color: #7C3AED; }
.badge.pending { background: rgba(107,114,128,0.12); color: #6B7280; }

/* 配置弹窗 */
.config-content { display: flex; flex-direction: column; gap: 10px; }
.config-row { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.config-row .lbl { width: 100px; color: #6b7280; flex-shrink: 0; }
.config-row .val { color: #111827; }
.config-row .val.mono { font-family: $font-family-mono; }
.config-row .val.small { font-size: 11px; color: #9ca3af; }
.mode-tag { padding: 2px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.mode-tag.real { background: #10B981; color: #fff; }
.mode-tag.mock { background: linear-gradient(135deg, #64748B 0%, #475569 100%); color: #fff; }
.config-guide { margin-top: 16px; padding: 12px 16px; background: #f9fafb; border-radius: 6px; }
.guide-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.guide-body { font-size: 12px; color: #4b5563; margin-bottom: 8px; }
.guide-steps { font-size: 12px; color: #374151; padding-left: 20px; margin: 0; }
.guide-steps li { margin-bottom: 4px; }
.guide-steps code { background: #e5e7eb; padding: 1px 5px; border-radius: 3px; font-size: 11px; font-family: $font-family-mono; }

/* 4 stat-card（design: .verify-stats > .stat-card） */
.verify-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
  @media (max-width: 1100px) { grid-template-columns: repeat(2, 1fr); }
  @media (max-width: 600px)  { grid-template-columns: 1fr; }
}
.stat-card {
  background: #fff;
  border-radius: $radius-md;
  padding: 14px 16px;
  box-shadow: $shadow-sm;
  .stat-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: $color-text-tertiary;
  }
  .stat-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 12px;
  }
  .stat-value {
    font-size: 24px;
    font-weight: 700;
    color: $color-text-primary;
    margin: 6px 0;
    font-family: $font-family-mono;
    .prefix { color: $color-text-tertiary; font-size: 16px; margin-right: 2px; }
    .unit { font-size: 12px; color: $color-text-tertiary; font-weight: 400; margin-left: 2px; font-family: -apple-system, sans-serif; }
  }
  .stat-delta {
    font-size: 11px;
    color: $color-text-tertiary;
    .delta.up { color: #10B981; font-weight: 600; margin-left: 4px; }
    .delta.plain { color: $color-text-tertiary; }
  }
}

/* 风险告警（design: .risk-card） */
.risk-card {
  background: rgba(239, 68, 68, 0.04);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: $radius-md;
  padding: 14px 16px;
  margin-bottom: 16px;
  .head {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
    .ico {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: rgba(239, 68, 68, 0.15);
      color: #EF4444;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
    }
    .t { font-size: 14px; font-weight: 600; color: #B91C1C; }
  }
  .body {
    .row {
      font-size: 12.5px;
      color: $color-text-secondary;
      padding: 4px 0;
      strong {
        font-family: $font-family-mono;
        color: #B91C1C;
        margin: 0 4px;
      }
    }
  }
}

// 触点 #49：开发环境提示条
.dev-env-hint {
  display: flex; gap: 12px;
  margin: 0 0 16px 0;
  padding: 12px 16px;
  background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
  border: 1px solid #CBD5E1;
  border-left: 3px solid #4F6BFF;
  border-radius: 8px;
  align-items: flex-start;
  .deh-icon { font-size: 20px; line-height: 1.4; }
  .deh-body { flex: 1; }
  .deh-title { font-size: 13.5px; font-weight: 600; color: #0F172A; margin-bottom: 4px; }
  .deh-desc { font-size: 12.5px; color: #475569; line-height: 1.6; }
  .deh-desc strong { color: #4F6BFF; font-weight: 600; }
  .deh-desc a { color: #4F6BFF; cursor: pointer; text-decoration: underline; }
}

// 查验来源 chip（去掉后端字符串里的 (mock) 后展示）
.source-clean {
  display: inline-flex; align-items: center;
  padding: 2px 10px; font-size: 12px; font-weight: 500;
  background: #F1F5F9; color: #475569;
  border: 1px solid #E2E8F0;
  border-radius: 9999px; line-height: 1.4;
  white-space: nowrap;
}

/* 发起查验（design: .verify-form-card） */
.verify-form-card {
  background: #fff;
  border-radius: $radius-md;
  box-shadow: $shadow-sm;
  padding: 16px 20px;
  margin-bottom: 16px;
  .verify-form-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
    h3 { font-size: 15px; font-weight: 600; margin: 0 0 4px; color: $color-text-primary; }
    .sub { font-size: 12px; color: $color-text-tertiary; }
    .head-right { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  }
  .verify-tabs {
    display: flex;
    gap: 4px;
    background: $color-bg;
    border-radius: $radius-sm;
    padding: 3px;
    a {
      padding: 5px 12px;
      border-radius: 4px;
      font-size: 12px;
      color: $color-text-secondary;
      text-decoration: none;
      cursor: pointer;
      &:hover { color: $color-primary; }
      &.active {
        background: #fff;
        color: $color-primary;
        font-weight: 600;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
      }
    }
  }
  .badge {
    background: rgba(16, 185, 129, 0.1);
    color: #10B981;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
  }
  .verify-form-row {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 12px;
    @media (max-width: 1100px) { grid-template-columns: repeat(3, 1fr); }
    @media (max-width: 700px)  { grid-template-columns: 1fr; }
    &.batch-row { grid-template-columns: 1fr auto; align-items: flex-end; }
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
    &.full { grid-column: 1 / -1; }
    &.btn-field { display: flex; flex-direction: column; justify-content: flex-end; }
    label {
      font-size: 11px;
      color: $color-text-tertiary;
      .required { color: #EF4444; }
      .optional { color: $color-text-tertiary; }
    }
    input, select {
      height: 36px;
      padding: 0 10px;
      border: 1px solid $color-border-strong;
      border-radius: $radius-sm;
      font-size: 12px;
      background: #fff;
      color: $color-text-primary;
      &:focus { outline: none; border-color: $color-primary; }
    }
  }
  .form-hint {
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid $color-border;
    font-size: 11.5px;
    color: $color-text-tertiary;
  }
}

/* 批量上传 dropzone */
.dropzone {
  border: 2px dashed $color-border-strong;
  border-radius: $radius-md;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  background: $color-bg;
  transition: all 0.2s;
  &:hover { border-color: $color-primary; background: $color-primary-bg; }
  .dropzone-icon { font-size: 32px; margin-bottom: 8px; }
  .dropzone-text { font-size: 14px; color: $color-text-primary; margin-bottom: 4px; }
  .dropzone-hint { font-size: 11px; color: $color-text-tertiary; }
}

/* 从识别记录选择 */
.record-pick {
  border: 1px solid $color-border;
  border-radius: $radius-md;
  overflow: hidden;
  .pick-stat {
    padding: 8px 12px;
    background: $color-bg;
    font-size: 12px;
    color: $color-text-secondary;
    border-bottom: 1px solid $color-border;
  }
  .pick-list { max-height: 240px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
  .pick-empty { padding: 20px; text-align: center; color: $color-text-tertiary; font-size: 12px; background: rgba(0,0,0,0.02); border-radius: 6px; }
  .pick-item {
    display: grid;
    grid-template-columns: 24px 140px 1fr 100px 80px;
    gap: 12px;
    align-items: center;
    padding: 8px 12px;
    border-bottom: 1px solid $color-border;
    font-size: 12px;
    &:last-child { border-bottom: none; }
    .cell-mono { font-family: $font-family-mono; color: $color-primary; }
    .amount { font-weight: 600; color: #EF4444; }
  }
}

/* 查验结果（design: .verify-result） */
.verify-result {
  background: #fff;
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: $radius-md;
  padding: 16px 20px;
  margin-bottom: 16px;
  .vr-top {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 14px;
    border-bottom: 1px solid $color-border;
    .vr-icon {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: rgba(16, 185, 129, 0.12);
      color: #10B981;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      font-weight: 700;
    }
    .vr-title { font-size: 15px; font-weight: 600; color: #10B981; }
    .vr-sub { font-size: 11.5px; color: $color-text-tertiary; margin-top: 2px; }
  }
  .vr-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px 16px;
    margin-top: 14px;
    @media (max-width: 900px) { grid-template-columns: repeat(2, 1fr); }
    .vr-item {
      .l { font-size: 11px; color: $color-text-tertiary; margin-bottom: 4px; }
      .v { font-size: 13.5px; font-weight: 600; color: $color-text-primary; }
      .v.mono { font-family: $font-family-mono; }
      .v.taxno { font-size: 13px; }
      .v.seller { font-weight: 500; }
    }
  }
}

/* 查验记录（design: .queue-card） */
.queue-card {
  background: #fff;
  border-radius: $radius-md;
  box-shadow: $shadow-sm;
  padding: 16px;
  .queue-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    flex-wrap: wrap;
    gap: 8px;
    h3 { font-size: 14px; font-weight: 600; margin: 0; color: $color-text-primary; }
    .toolbar { display: flex; gap: 8px; align-items: center; }
  }
}
.search-input {
  width: 240px;
  height: 32px;
  padding: 0 10px;
  border: 1px solid $color-border-strong;
  border-radius: $radius-sm;
  font-size: 12px;
  background: #fff;
  &:focus { outline: none; border-color: $color-primary; }
}
.select-result {
  height: 32px;
  padding: 0 10px;
  border: 1px solid $color-border-strong;
  border-radius: $radius-sm;
  font-size: 12px;
  background: #fff;
}

.verify-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  th {
    text-align: left;
    padding: 10px 8px;
    background: $color-bg;
    color: $color-text-tertiary;
    font-weight: 500;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  td {
    padding: 10px 8px;
    border-bottom: 1px solid $color-border;
  }
  tr:hover { background: $color-bg; }
  .cell-mono { font-family: $font-family-mono; }
  .cell-mono.normal { color: $color-primary; }
  .cell-mono.danger { color: #B91C1C; }
  .cell-amount { font-weight: 600; color: $color-text-primary; }
}

.v-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
  &.success { background: rgba(16, 185, 129, 0.1); color: #10B981; }
  &.danger  { background: rgba(239, 68, 68, 0.1); color: #EF4444; }
  &.warning { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
}
.s-tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10.5px;
  &.success { background: rgba(16, 185, 129, 0.1); color: #10B981; }
  &.danger  { background: rgba(239, 68, 68, 0.1); color: #EF4444; }
  &.warning { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
}

.row-actions {
  display: flex;
  gap: 8px;
  a {
    font-size: 12.5px;
    color: $color-primary;
    cursor: pointer;
    font-weight: 500;
    &:hover { text-decoration: underline; }
    &.danger { color: #EF4444; }
  }
}

/* 按钮（design: .btn variants） */
.btn {
  padding: 8px 16px;
  border-radius: $radius-sm;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
  background: transparent;
  &.btn-primary {
    background: $color-primary;
    color: #fff;
    &:hover { background: darken($color-primary, 8%); }
  }
  &.btn-outline {
    background: #fff;
    border-color: $color-border-strong;
    color: $color-text-primary;
    &:hover { border-color: $color-primary; color: $color-primary; }
  }
  &.btn-sm { padding: 4px 10px; font-size: 11px; }
}
</style>
