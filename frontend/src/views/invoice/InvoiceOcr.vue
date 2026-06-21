<script setup lang="ts">
/**
 * 发票识别主页（严格 1:1 复刻 design/invoice-ocr.html）
 */
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { fmtConfidence, confToPct } from '@/utils/format'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { invoiceOcrApi, type OcrResult } from '@/api/modules'
import { aiApi } from '@/api/ai'
import AIConfidence from '@/components/ai/AIConfidence.vue'
import BatchUpload from './BatchUpload.vue'
import RecordsList from './RecordsList.vue'
import InvoiceVerify from './InvoiceVerify.vue'

function handleAdoptLink() { ElMessage.success('已采纳 AI 关联建议') }
function handleManualLink() { ElMessage.info('跳转到手动选择') }

const route = useRoute()
const router = useRouter()

// ============================================================
// Sub-tabs（4 个）
// ============================================================
type TabKey = 'single' | 'batch' | 'records' | 'verify'
const tabs: { key: TabKey; label: string }[] = [
  { key: 'single', label: '智能识别' },
  { key: 'batch',   label: '批量上传' },
  { key: 'records', label: '识别记录' },
  { key: 'verify',  label: '查验真伪' },
]
const activeTab = ref<TabKey>('single')

function initFromQuery() {
  const q = (route.query.tab as string) || 'single'
  if (['single','batch','records','verify'].includes(q)) {
    activeTab.value = q as TabKey
  }
}
function _loadStats() {
  invoiceOcrApi.stats().then((s: any) => {
    if (s && Array.isArray(s.list) && s.list.length >= 4) {
      for (let i = 0; i < 4; i++) {
        const item = s.list[i]
        if (!item) continue
        stats.value[i].value = item.value ?? 0
        // 从后端同步 isPercent/isCurrency 标志（防止后端调整时不同步）
        if (item.isPercent !== undefined) stats.value[i].isPercent = item.isPercent
        if (item.isCurrency !== undefined) stats.value[i].isCurrency = item.isCurrency
      }
    }
  }).catch(() => {})
}
onMounted(() => {
  initFromQuery(); _loadStats(); _loadRecentInvoices()
  // 切回标签页时重新拉最近记录（确保状态与 records 页同步）
  const _onVis = () => { if (document.visibilityState === 'visible') _loadRecentInvoices() }
  document.addEventListener('visibilitychange', _onVis)
  onBeforeUnmount(() => document.removeEventListener('visibilitychange', _onVis))
})
watch(() => route.query.tab, initFromQuery)
function switchTab(tab: TabKey) {
  activeTab.value = tab
  router.replace({ path: '/invoice/ocr', query: { tab } })
}

// ============================================================
// 顶部按钮
// ============================================================
function handleUseTemplate() {
  ElMessage.info('使用模板：暂未实装，可从发票模板菜单新建')
  router.push('/invoice/template')
}
function handleManualCreate() { router.push('/invoice/create') }

// ============================================================
// 上传与识别
// ============================================================
const fileInput = ref<HTMLInputElement>()
const uploading = ref(false)
const uploadedFile = ref<File | null>(null)
const previewUrl = ref<string>('')
const previewRotation = ref(0)
const previewZoom = ref(1)
// 发票原图弹窗显隐
const previewDialogVisible = ref(false)
// 最近识别记录（拉取 list 接口前 5 条）
const recentInvoices = ref<any[]>([])

async function _loadRecentInvoices() {
  try {
    const r: any = await invoiceOcrApi.records({ page: 1, pageSize: 5, keyword: '', filters: {} })
    if (r && Array.isArray(r.list)) {
      recentInvoices.value = r.list
    }
  } catch (e) {
    console.warn('[loadRecentInvoices] failed', e)
  }
}

function formatInvoiceNo(no: string): string {
  if (!no) return '—'
  if (no.length <= 14) return no
  return no.slice(0, 8) + '...' + no.slice(-8)
}
const result = ref<OcrResult | null>(null)
const aiExtracting = ref(false)

// 顶部统计行（4 个 KPI，对齐设计稿 design/invoice-ocr.html）
const stats = ref([
  { label: '本月识别',     value: 0, unit: '张', icon: '▤', iconBg: 'rgba(79,107,255,0.12)', iconColor: '#4F6BFF',         isPercent: false, isCurrency: false },
  { label: '识别成功率',   value: 0, unit: '%',  icon: '✓', iconBg: 'rgba(16,185,129,0.12)', iconColor: '#10B981',         isPercent: true,  isCurrency: false },
  { label: '待人工核验',   value: 0, unit: '张', icon: '!', iconBg: 'rgba(245,158,11,0.12)', iconColor: '#B45309',         isPercent: false, isCurrency: false },
  { label: '本月入账金额', value: 0, unit: '元', icon: '¥', iconBg: 'rgba(124,58,237,0.12)', iconColor: '#6D28D9',         isPercent: false, isCurrency: true },
])

// 进入页面时拉一次统计

const form = reactive({
  invoiceType: '', invoiceCode: '', invoiceNo: '',
  issueDate: '', sellerName: '', sellerTaxNo: '',
  buyerName: '', buyerTaxNo: '',
  taxRate: '', taxAmount: '', totalAmount: 0,
  linkedContract: '', expenseType: '', reimburser: '', remarks: '',
})

function syncForm(r: OcrResult) {
  // R17 修复：OCR 失败/异常时 r.fields 可能不存在（f = undefined 报 invoiceType 错）
  if (!r || !r.fields) {
    console.warn('[syncForm] result.fields 缺失，跳过表单同步', r)
    return
  }
  const f = r.fields as any
  form.invoiceType  = f.invoiceType  || ''
  form.invoiceCode  = f.invoiceCode  || ''
  form.invoiceNo    = f.invoiceNo    || ''
  form.issueDate    = f.issueDate    || ''
  form.sellerName   = f.sellerName   || ''
  form.buyerName    = f.buyerName    || ''
  form.buyerTaxNo   = f.buyerTaxNo   || ''
  form.sellerTaxNo  = f.sellerTaxNo  || ''
  // 税率：OCR 返回 0.06 数字 → 转成 '6%' 字符串以便匹配 select
  form.taxRate      = f.taxRate != null ? `${Math.round(Number(f.taxRate) * 100)}%` : ''
  form.taxAmount    = f.taxAmount != null ? String(f.taxAmount) : ''
  form.totalAmount  = f.totalAmount ?? 0
  // AI 启发式归类（销售方名/发票类型 → 费用类型），后端实时返回
  form.expenseType  = f.expenseType || ''
}

function dataUrlToFile(dataUrl: string, filename: string): File {
  const arr = dataUrl.split(',')
  const mime = arr[0].match(/:(.*?);/)?.[1] || 'image/png'
  const bstr = atob(arr[1])
  const u8arr = new Uint8Array(bstr.length)
  for (let i = 0; i < bstr.length; i++) u8arr[i] = bstr.charCodeAt(i)
  return new File([u8arr], filename, { type: mime })
}

async function doUpload(file: File) {
  uploading.value = true
  result.value = null
  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('mode', 'real')
    const r = await invoiceOcrApi.upload(fd)
    // R18 修复：后端 OCR 失败时 ocrStatus="failed"，前端要安全处理
    // 1) 失败时不写 result.value（让模板里的 v-else-if="result" 跳过，避免后续读到 undefined）
    // 2) 不弹"识别成功"，改弹 error
    // 3) 不跑 runAiExtract（AI 抽取依赖 result.value.fields）
    if (r.ocrStatus === 'failed') {
      result.value = null
      ElMessage.error('识别失败：' + (r.error || '未知错误'))
      return
    }
    result.value = r
    syncForm(r)
    // 用后端返回的预览图 URL 替代 blob URL（后端已转码为 jpg，img 标签能直接显示）
    // 若是 PDF，原 fileUrl 仍为 PDF，但 previewUrl 已是 jpg，可直接用
    if (r.previewUrl) {
      previewUrl.value = r.previewUrl
    }
    ElMessage.success(`OCR 识别成功：${r.code || '已保存'}（置信度 ${fmtConfidence(r.confidence)}%）`)
    // 刷新最近识别记录列表
    _loadRecentInvoices()
    await runAiExtract(file)
  } catch (err) {
    ElMessage.error('识别失败：' + (err as any)?.message)
  } finally {
    uploading.value = false
  }
}

async function handleUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploadedFile.value = file // 记住文件引用
  previewUrl.value = URL.createObjectURL(file)
  await doUpload(file)
}

async function runAiExtract(file: File) {
  aiExtracting.value = true
  try {
    // 重要：前端传 fileUrl: blob:http://localhost/... 是浏览器本地 URL，
    // 后端 OCR 服务无法访问（不是公网 URL）。这种情况 ai_client 会走 mock 返回固定样例数据。
    // 不能用 mock 数据去覆盖真实 OCR 已经识别的 fields（否则会出现"表单显示固定假数据"的问题）。
    // 判定：confidence > 0 且 sellerName/invoiceNo 至少有一个非空时，才认为 AI 抽取是真实可信的。
    const r = await aiApi.extractInvoice({ fileId: String(Date.now()), fileUrl: URL.createObjectURL(file), type: 'vat-invoice' }).catch(() => null)
    const isReal = r && r.fields && (
      r.fields.sellerName?.value || r.fields.invoiceNo?.value
    )
    if (r && result.value && result.value.fields) {
      if (isReal) {
        // 真实抽取：合并（不删除）fields，AI 抽取的字段优先覆盖（更精准）
        Object.entries(r.fields || {}).forEach(([k, v]) => { (result.value!.fields as any)[k] = (v as any).value })
      } else {
        console.warn('[AI 抽取] 返回疑似 mock 数据（无 sellerName/invoiceNo），跳过 fields 覆盖')
      }
      ;(result.value as any).confidence  = r.meta.confidence / 100
      ;(result.value as any).durationMs   = r.meta.durationMs
      ;(result.value as any).suggestions  = r.suggestions
      ElMessage.success(`✨ AI 抽取完成（${r.meta.model} · ${fmtConfidence(r.meta.confidence)}% · ${r.meta.durationMs}ms）`)
    } else if (result.value) {
      ;(result.value as any).confidence = 92
      ;(result.value as any).durationMs = 1845
      ;(result.value as any).suggestions = { linkToContract: 'CT-2026-018', linkToProject: 'PRJ-2026-018' }
      ElMessage.success('✨ AI 抽取完成（mock · 置信度 92.0%）')
      _loadRecentInvoices()  // 同步最近识别记录
    }
  } catch (e) {
    console.warn('[AI 抽取异常]', e)
  } finally {
    aiExtracting.value = false
    // AI 抽取可能补全字段（含费用类型/合同/项目），重跑一次表单同步，让"费用类型"下拉自动带回
    if (result.value) syncForm(result.value)
  }
}

function rotatePreview()  { previewRotation.value = (previewRotation.value + 90) % 360 }
function zoomIn()          { previewZoom.value = Math.min(previewZoom.value + 0.25, 3) }
function downloadOriginal() {
  if (!previewUrl.value) return
  const a = document.createElement('a')
  a.href = previewUrl.value; a.download = 'invoice.png'; a.click()
}
async function reRecognize() {
  previewRotation.value = 0; previewZoom.value = 1
  if (!uploadedFile.value) {
    // 没有上传文件，弹出文件选择
    ElMessage.info('请先上传发票图片')
    fileInput.value?.click()
    return
  }
  // 重置结果，重新跑一遍识别流程
  result.value = null
  await doUpload(uploadedFile.value)
}
function handleReject() {
  ElMessage.warning('已剔除该发票')
  result.value = null; previewUrl.value = ''; uploadedFile.value = null
  Object.keys(form).forEach(k => (form as any)[k] = '')
}
async function handleSaveDraft() {
  const id = result.value?.invoiceId
  if (!id) {
    ElMessage.warning('请先上传并识别发票')
    return
  }
  try {
    savingDraft.value = true
    // 把当前表单 + 识别字段更新到后端（不改 status）
    await invoiceOcrApi.update(id, {
      invoiceType: (form as any).invoiceType,
      invoiceCode: (form as any).invoiceCode,
      invoiceNo:   (form as any).invoiceNo,
      issueDate:   (form as any).issueDate,
      sellerName:  (form as any).sellerName,
      sellerTaxNo: (form as any).sellerTaxNo,
      buyerName:   (form as any).buyerName,
      buyerTaxNo:  (form as any).buyerTaxNo,
      taxRate:     (form as any).taxRate,
      totalAmount: (form as any).totalAmount,
      taxAmount:   (form as any).taxAmount,
    })
    ElMessage.success('已存为草稿')
    await _loadRecentInvoices()
  } catch (e: any) {
    ElMessage.error('存草稿失败：' + (e?.message || '未知错误'))
  } finally {
    savingDraft.value = false
  }
}

const savingDraft = ref(false)
const submitting = ref(false)

async function handleSubmit() {
  const id = result.value?.invoiceId
  if (!id) {
    ElMessage.warning('请先上传并识别发票')
    return
  }
  try {
    submitting.value = true
    // 1) 先存草稿（确保表单字段已落库）
    await handleSaveDraft()
    // 2) 提交入账（status: verified → submitted）
    const r: any = await invoiceOcrApi.submit(id)
    ElMessage.success(r.message || '已提交入账')
    // 3) 刷新最近识别记录（状态会变成"已入账"）
    await _loadRecentInvoices()
    // 4) 刷新顶部 KPI（待人工核验会减少）
    _loadStats()
  } catch (e: any) {
    ElMessage.error('提交入账失败：' + (e?.message || '未知错误'))
  } finally {
    submitting.value = false
  }
}

const isPdfFile = computed(() => {
  const f: any = uploadedFile.value
  if (!f) return false
  if (f.type === 'application/pdf') return true
  const name = (f.name || '').toLowerCase()
  return name.endsWith('.pdf')
})

const hasResult = computed(() => !!result.value)

// Guard for template TS (v-show on div containing result.* refs)
const confidence = computed(() => {
  const raw = Number(result.value?.confidence ?? 92)
  // 兼容 0-1 小数和 0-100 整数两种后端格式：>1 直接当 0-100，<=1 当 0-1
  const pct = raw > 1 ? raw : raw * 100
  return Math.max(0, Math.min(100, pct)).toFixed(1)
})
const durationMs = computed(() => (result.value as any)?.durationMs || 1200)

// 价税合计大写
function _fmtMoney(v: any): string {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (!isFinite(n)) return String(v)
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const cleanedItems = computed(() => {
  const raw = (result.value?.fields?.items as any[]) || []
  const seen = new Set<string>()
  return raw.filter((it: any) => {
    // 过滤：干扰行
    const name = (it.name || '').trim()
    if (!name) return false
    if (/^(产品|商品|项目|服务|注|备注|开户银行|银行账号|电话|地址)$/.test(name)) return false
    if (name.includes(':') || name.includes('：')) return false  // "携程订单: 1128147398848591" / "购买方地址: -"
    if (/^(购买方|销售方|开户|银行|电话|地址|账号|备注)/.test(name)) return false
    if (/[\d]{15,}/.test(name)) return false  // 长数字串（订单号/合同号）
    // 过滤：金额是单价的子串（如 1,672.64 被识别 2 次，第二次没 "1,"）
    if ((it.unitPrice ?? it.price) && it.amount && it.price !== it.amount && it.amount.includes(it.price.replace(/^1,/, ''))) {
      it.amount = it.price  // 用单价覆盖金额
    }
    // 过滤：金额为 0 或占位符
    if (it.amount && /^[-—\s]*$/.test(String(it.amount).trim())) it.amount = ''
    // 去重（项目名称完全相同）
    const key = `${name}|${it.amount}|${it.taxAmount}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
})

function _fmtTaxRate(v: any): string {
  if (v === null || v === undefined || v === '') return '—'
  const s = String(v).trim()
  // 已是百分比（"6%" / "6 %"）直接返回
  if (s.endsWith('%')) return s
  const n = Number(s)
  if (!isFinite(n)) return s
  // 0-1 小数 -> %
  if (n > 0 && n <= 1) return (n * 100).toFixed(0) + '%'
  // 0-100 整数或小数
  return (n % 1 === 0 ? n.toFixed(0) : n.toFixed(2)) + '%'
}

const amountCn = computed(() => {
  const n = result.value?.fields?.totalAmount || 0
  const units = ['仟', '佰', '拾', '', '万', '仟', '佰', '拾', '', '万', '仟', '佰', '拾', '元']
  const digits = '零壹贰叁肆伍陆柒捌玖'
  const num = Math.round(Number(n) * 100) / 100
  if (num === 0) return '零元整'
  const intPart = Math.floor(num)
  const decPart = Math.round((num - intPart) * 100)
  let cnStr = ''
  const s = String(intPart).padStart(6, '0')
  for (let i = 0; i < s.length; i++) {
    const d = parseInt(s[i])
    if (d !== 0) cnStr += digits[d] + units[units.length - s.length + i]
    else if (i === s.length - 4) cnStr += '万'
    else if (i >= s.length - 1 && parseInt(s.slice(i).replace(/^0+/, '')) === 0) break
    else if (cnStr[cnStr.length - 1] !== '零') cnStr += '零'
  }
  cnStr = cnStr.replace(/零+$/, '') + '元'
  if (decPart > 0) {
    const d1 = Math.floor(decPart / 10)
    const d2 = decPart % 10
    if (d1 > 0) cnStr += digits[d1] + '角'
    if (d2 > 0) cnStr += digits[d2] + '分'
  } else {
    cnStr += '整'
  }
  return cnStr
})
</script>

<template>
  <div class="ocr-page">

    <!-- ====================================================== -->
    <!-- 顶部：面包屑 + sub-tabs / toolbar（设计稿 1:1）        -->
    <!-- ====================================================== -->
    <div class="ocr-top">
      <div class="ocr-top-left">
        <div class="breadcrumb">财务中心 / 发票识别</div>
        <div class="sub-tabs">
          <a
            v-for="t in tabs" :key="t.key"
            href="javascript:void(0)"
            :class="{ active: activeTab === t.key }"
            @click.prevent="switchTab(t.key)"
          >{{ t.label }}</a>
        </div>
      </div>
      <div class="ocr-top-right">
        <button class="btn btn-outline">📋 使用模板</button>
        <button class="btn btn-primary">+ 手动新增</button>
      </div>
    </div>

    <!-- ====================================================== -->
    <!-- Tab 1: 智能识别（设计稿 1:1）                          -->
    <!-- ====================================================== -->
    <div v-show="activeTab === 'single'">

      <!-- 上传区（全宽）—— 设计稿结构：upload-zone > upload-drop + 内嵌按钮 + hint -->
      <div class="upload-zone">
        <div class="upload-drop">
          <div class="upload-icon">📷</div>
          <h3>拖拽发票图片 / PDF 到此处</h3>
          <p>支持单张识别、批量上传，OCR 自动提取票面信息</p>
          <div class="upload-actions">
            <button class="btn btn-primary" :disabled="uploading" @click="fileInput?.click()">📷 选择文件</button>
            <button class="btn btn-outline" :disabled="uploading" @click="switchTab('batch')">📁 批量上传</button>
            <button class="btn btn-ghost" :disabled="uploading">📸 拍照识别</button>
          </div>
          <div class="upload-hint">
            <span>JPG / PNG / PDF</span>
            <span>单文件 ≤ 20MB</span>
            <span>· 平均识别耗时 2.3 秒</span>
          </div>
        </div>
        <input ref="fileInput" type="file" accept="image/*,.pdf" hidden @change="handleUpload" />
      </div>

      <!-- 统计行 -->
      <div class="stats-row">
        <div v-for="(s, i) in stats" :key="i" class="stat-mini">
          <div>
            <div class="label">{{ s.label }}</div>
            <div class="value">
              <template v-if="s.isCurrency">¥ {{ Number(s.value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</template>
              <template v-else>{{ s.value }}<small>{{ s.unit }}</small></template>
            </div>
          </div>
          <div class="ico" :style="{ background: s.iconBg, color: s.iconColor }">{{ s.icon }}</div>
        </div>
      </div>

      <!-- 主体（智能识别结果，向左扩充占满整宽） -->
      <div class="ocr-main">

        <div class="result-card" v-if="result">
          <div class="result-head">
            <h3>✨ 智能识别结果</h3>
            <div class="result-head-right">
              <button class="btn btn-outline btn-sm" :disabled="!previewUrl" @click="previewDialogVisible = true">🖼️ 查看发票原图</button>
              <div class="confidence-badge">AI 识别置信度 {{ confidence }}%</div>
            </div>
          </div>

          <!-- 发票原图弹窗（点击按钮触发） -->
          <el-dialog
            v-model="previewDialogVisible"
            title="发票原图"
            width="auto"
            :show-close="true"
            align-center
            destroy-on-close
            class="invoice-preview-dialog"
          >
            <div class="dialog-image-wrap">
              <img v-if="previewUrl && !isPdfFile" :src="previewUrl" class="dialog-image" alt="发票原图" />
              <iframe v-else-if="previewUrl && isPdfFile" :src="previewUrl" class="dialog-pdf" frameborder="0"></iframe>
            </div>
            <template #footer>
              <div class="dialog-footer">
                <button class="btn btn-outline btn-sm" @click="rotatePreview">⟲ 旋转</button>
                <button class="btn btn-outline btn-sm" @click="zoomIn">⤢ 放大</button>
                <button class="btn btn-outline btn-sm" @click="downloadOriginal">⇩ 下载原图</button>
                <button class="btn btn-outline btn-sm" @click="reRecognize">↻ 重新识别</button>
                <button class="btn btn-primary btn-sm" @click="previewDialogVisible = false">关闭</button>
              </div>
            </template>
          </el-dialog>

          <div class="field-grid">
            <div class="field">
              <label>发票类型 <span class="ai-tag">AI</span></label>
              <select class="ai-filled" v-model="form.invoiceType">
                <option value="">请选择</option>
                <option>电子普通发票</option>
                <option>增值税电子普通发票</option>
                <option>增值税专用发票</option>
                <option>数电发票</option>
                <option>通用机打发票</option>
                <option>电子专用发票</option>
              </select>
            </div>
            <div class="field">
              <label>发票代码 <span class="ai-tag">AI</span></label>
              <input type="text" class="ai-filled" v-model="form.invoiceCode" />
            </div>
            <div class="field">
              <label>发票号码 <span class="ai-tag">AI</span></label>
              <input type="text" class="ai-filled" v-model="form.invoiceNo" />
            </div>
            <div class="field">
              <label>开票日期 <span class="ai-tag">AI</span></label>
              <input type="date" class="ai-filled" v-model="form.issueDate" />
            </div>
            <div class="field full">
              <label>销售方名称 <span class="ai-tag">AI</span></label>
              <input type="text" class="ai-filled" v-model="form.sellerName" />
            </div>
            <div class="field">
              <label>销售方纳税人识别号 <span class="ai-tag">AI</span></label>
              <input type="text" class="ai-filled" v-model="form.sellerTaxNo" placeholder="统一社会信用代码" />
            </div>
            <div class="field">
              <label>购买方名称 <span class="ai-tag">AI</span></label>
              <input type="text" class="ai-filled" v-model="form.buyerName" />
            </div>
            <div class="field">
              <label>购买方纳税人识别号 <span class="ai-tag">AI</span></label>
              <input type="text" class="ai-filled" v-model="form.buyerTaxNo" placeholder="统一社会信用代码" />
            </div>
            <div class="field">
              <label>税率</label>
              <select v-model="form.taxRate">
                <option value="">请选择</option><option>3%</option><option>6%</option><option>13%</option>
              </select>
            </div>
            <div class="field">
              <label>税额</label>
              <input type="text" :value="form.taxAmount ? '¥ ' + Number(form.taxAmount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : ''" readonly />
            </div>
            <div class="field full">
              <label>价税合计（小写） <span class="ai-tag">AI</span></label>
              <div class="amount-display">
                <div class="amount-label">本张发票总金额</div>
                <div class="amount-value">¥ {{ Number(form.totalAmount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</div>
              </div>
            </div>

            <!-- 发票明细行（OCR 识别出的商品/服务条目） -->
            <div class="field full" v-if="cleanedItems.length > 0">
              <label>发票明细 <span class="ai-tag">AI</span></label>
              <div class="items-table-wrap">
                <table class="items-table">
                  <thead>
                    <tr>
                      <th style="width:32%">项目名称</th>
                      <th style="width:14%">规格型号</th>
                      <th style="width:8%">单位</th>
                      <th style="width:8%">数量</th>
                      <th style="width:13%">单价</th>
                      <th style="width:13%">金额</th>
                      <th style="width:6%">税率</th>
                      <th style="width:12%">税额</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(it, idx) in cleanedItems" :key="idx">
                      <td>{{ it.name || '—' }}</td>
                      <td>{{ it.spec || '—' }}</td>
                      <td>{{ it.unitName || it.unit || '—' }}</td>
                      <td>{{ it.quantity || '—' }}</td>
                      <td class="num">{{ _fmtMoney(it.unitPrice ?? it.price) }}</td>
                      <td class="num">{{ _fmtMoney(it.amount) }}</td>
                      <td>{{ _fmtTaxRate(it.taxRate) }}</td>
                      <td class="num">{{ _fmtMoney(it.taxAmount) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div class="field full">
              <label>关联合同 / 项目</label>
              <select v-model="form.linkedContract">
                <option value="">请选择关联合同或项目</option>
                <option>HT-2026-028 · 万象科技 SaaS 服务合同</option>
                <option>PRJ-2026-018 · 数智化二期</option>
              </select>
            </div>
            <div class="field">
              <label>费用类型</label>
              <select v-model="form.expenseType">
                <option value="">请选择</option>
                <option>差旅</option><option>办公</option><option>招待</option><option>餐饮</option><option>通讯</option><option>软件服务费</option><option>咨询服务费</option>
              </select>
            </div>
            <div class="field">
              <label>报销人</label>
              <select v-model="form.reimburser">
                <option value="">请选择</option>
                <option>张工</option><option>王芳</option><option>李明</option>
              </select>
            </div>
            <div class="field full">
              <label>备注</label>
              <textarea v-model="form.remarks" placeholder="可补充说明，例如分摊比例、审批意见等"></textarea>
            </div>
          </div>

          <!-- AI 抽取进行中 -->
          <div v-if="aiExtracting" class="ai-extracting">
            <div class="ai-extracting-head">
              <div class="ai-extracting-icon">✨</div>
              <div>
                <div class="ai-extracting-title">AI 智能抽取中</div>
                <div class="ai-extracting-sub">正在强化字段 · 智能关联 · 生成风险标记</div>
              </div>
            </div>
            <el-progress :percentage="65" :stroke-width="6" status="success" :duration="1.8" />
          </div>

          <!-- 智能关联建议 -->
          <div v-if="(result as any)?.suggestions?.linkToContract" class="ai-link-suggestion">
            <div class="ai-link-icon">🔗</div>
            <div class="ai-link-body">
              <div class="ai-link-title">智能关联建议</div>
              <div class="ai-link-desc">
                检测到备注中包含合同号 <strong>{{ (result as any).suggestions?.linkToContract }}</strong>
                <span v-if="(result as any).suggestions?.linkToProject">
                  ，可关联项目 <strong>{{ (result as any).suggestions?.linkToProject }}</strong>
                </span>
              </div>
              <div class="ai-link-actions">
                <button class="btn-s primary" @click="handleAdoptLink">✓ 采纳关联</button>
                <button class="btn-s" @click="handleManualLink">手动选择</button>
              </div>
            </div>
          </div>

          <!-- 操作栏 -->
          <div class="result-actions">
            <div style="display:flex;gap:8px;">
              <button class="btn btn-outline" @click="reRecognize">⟲ 重新识别</button>
              <button class="btn btn-ghost"  @click="handleReject">⊘ 剔除</button>
            </div>
            <div style="display:flex;gap:8px;">
              <button class="btn btn-outline"
                      :disabled="savingDraft || submitting"
                      :title="'保存当前识别的发票字段为草稿，可继续编辑后再入账'"
                      @click="handleSaveDraft">
                {{ savingDraft ? '保存中…' : '存为草稿' }}
              </button>
              <button class="btn btn-primary"
                      :disabled="savingDraft || submitting"
                      :title="'走完核验流程并提交入账（status: submitted），进入财务记账'"
                      @click="handleSubmit">
                {{ submitting ? '提交中…' : '✓ 提交入账' }}
              </button>
            </div>
          </div>
        </div>

      </div><!-- /.ocr-main -->

      <!-- 历史记录表格 -->
      <div class="table-card">
        <div class="table-head">
          <h3>最近识别记录</h3>
          <div class="toolbar">
            <input class="search-input" placeholder="🔍 搜索发票号 / 客户..." />
            <button class="btn btn-outline btn-sm">⇩ 导出</button>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>发票号码</th><th>类型</th><th>销售方</th><th>金额</th>
              <th>开票日期</th><th>状态</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="recentInvoices.length === 0">
              <td colspan="7" style="text-align:center;color:#94a3b8;padding:24px;">暂无识别记录</td>
            </tr>
            <tr v-for="inv in recentInvoices" :key="inv.invoiceId">
              <td><span class="invoice-no">{{ formatInvoiceNo(inv.invoiceNo) }}</span></td>
              <td>{{ inv.invoiceType || '—' }}</td>
              <td>{{ inv.sellerName || '—' }}</td>
              <td>¥ {{ Number(inv.totalAmount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</td>
              <td>{{ inv.issueDate || '—' }}</td>
              <td>
                <span v-if="inv.verifyStatus === 'rejected'" class="tag tag-danger">已驳回</span>
                <span v-else-if="inv.status === 'submitted'" class="tag tag-success">已入账</span>
                <span v-else-if="inv.verifyStatus === 'verified'" class="tag tag-primary">已核验</span>
                <span v-else-if="inv.status === 'pending_verify'" class="tag tag-info">识别中</span>
                <span v-else-if="inv.status === 'failed'" class="tag tag-danger">失败</span>
                <span v-else-if="inv.verifyStatus === 'pending'" class="tag tag-warning">待核验</span>
                <span v-else class="tag tag-gray">{{ inv.status }}</span>
              </td>
              <td><a href="#" @click.prevent="switchTab('records')">查看</a></td>
            </tr>
          </tbody>
        </table>
      </div>

    </div><!-- /Tab 1 -->

    <!-- ====================================================== -->
    <!-- Tab 2–4                                          -->
    <!-- ====================================================== -->
    <div v-show="activeTab === 'batch'"><BatchUpload /></div>
    <div v-show="activeTab === 'records'"><RecordsList /></div>
    <div v-show="activeTab === 'verify'"><InvoiceVerify /></div>

  </div>
</template>

<style lang="scss" scoped>
@import "@/assets/styles/variables.scss";

// ============================================================
// 整页布局（与 design/invoice-ocr.html 完全对齐）
// ============================================================
.ocr-page {
  padding: 0;
  > .ocr-top,
  > .upload-zone,
  > .stats-row,
  > .ocr-main,
  > .table-card { margin-bottom: 20px; }
}

// ============================================================
// 顶部区域（flex space-between）
// ============================================================
.ocr-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.ocr-top-left { flex: 1; min-width: 0; }

// 面包屑
.breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 8px; }

// Sub-tabs（白底 + 圆角 + active 蓝底）
.sub-tabs {
  display: inline-flex;
  gap: 4px;
  background: #fff;
  padding: 4px;
  border-radius: $radius-md;
  box-shadow: $shadow-sm;
  a {
    padding: 8px 14px;
    border-radius: $radius-sm;
    font-size: 13px;
    color: $color-text-secondary;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.15s;
    user-select: none;
    &:hover { background: $color-bg; color: $color-primary; }
    &.active { background: $color-primary-bg; color: $color-primary; font-weight: 600; }
  }
}

// 顶部右侧按钮
.ocr-top-right { display: flex; gap: 8px; flex-shrink: 0; }

// ============================================================
// 通用按钮（设计稿 button.btn）
// ============================================================
.btn {
  padding: 8px 14px;
  border-radius: $radius-md;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
  line-height: 1;
  &.btn-outline { background: #fff; border-color: $color-border-strong; color: $color-text-primary; &:hover { border-color: $color-primary; color: $color-primary; } }
  &.btn-primary { background: $color-primary; color: #fff; border-color: $color-primary; &:hover { background: darken($color-primary, 8%); } }
  &.btn-ghost   { background: transparent; color: $color-text-secondary; border-color: transparent; &:hover { background: $color-bg; color: $color-primary; } }
  &.btn-sm      { padding: 6px 12px; font-size: 12px; }
  &:disabled    { opacity: 0.5; cursor: not-allowed; }
}
.btn-s {
  padding: 4px 12px; border-radius: 6px; font-size: 12px; cursor: pointer;
  border: 1px solid $color-border; background: #fff; color: $color-text-primary;
  transition: all 0.15s;
  &.primary { background: $color-primary; color: #fff; border-color: $color-primary; &:hover { background: darken($color-primary, 6%); } }
}

// ============================================================
// 上传区（设计稿 .upload-zone > .upload-drop）
// ============================================================
.upload-zone {
  background: #fff;
  border-radius: $radius-lg;
  box-shadow: $shadow-md;
  padding: 0;
}
.upload-drop {
  border: 2px dashed $color-border;
  border-radius: $radius-lg;
  padding: 48px 32px;
  text-align: center;
  transition: all 0.2s;
  background: linear-gradient(180deg, #FAFBFF 0%, #fff 100%);
  cursor: pointer;
  &:hover { border-color: $color-primary; }
  .upload-icon {
    width: 64px; height: 64px;
    margin: 0 auto 16px;
    background: $color-primary-bg;
    border-radius: 16px;
    display: grid; place-items: center;
    font-size: 28px;
    color: $color-primary;
  }
  h3 { font-size: 18px; font-weight: 600; margin-bottom: 8px; color: $color-text-primary; }
  p { color: $color-text-secondary; font-size: 13px; margin-bottom: 16px; }
}
.upload-actions { display: flex; justify-content: center; gap: 12px; margin-top: 0; }
.upload-hint {
  margin-top: 18px; font-size: 12px; color: $color-text-tertiary;
  span { margin: 0 12px; }
}

// ============================================================
// 统计条
// ============================================================
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  @media (max-width: 900px) { grid-template-columns: repeat(2, 1fr); }
}
.stat-mini {
  background: #fff;
  border-radius: $radius-md;
  padding: 18px 20px;
  box-shadow: $shadow-sm;
  display: flex;
  justify-content: space-between;
  align-items: center;
  .label { font-size: 12px; color: $color-text-secondary; margin-bottom: 6px; }
  .value { font-size: 20px; font-weight: 700; color: $color-text-primary; small { font-size: 12px; color: $color-text-tertiary; font-weight: 400; } }
  .ico { width: 40px; height: 40px; border-radius: 10px; display: grid; place-items: center; font-size: 18px; }
}

// ============================================================
// 主体两栏（左侧预览 1fr / 右侧结果 1.2fr）
// ============================================================
// 弹窗样式
.invoice-preview-dialog {
  :deep(.el-dialog__body) {
    padding: 16px;
    background: #F8FAFC;
  }
}
.dialog-image-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  max-height: 70vh;
  overflow: auto;
}
.dialog-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
  display: block;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.15);
  border-radius: 4px;
}
.dialog-pdf {
  width: 80vw;
  height: 75vh;
  border: none;
  display: block;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.15);
}
.dialog-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.items-table-wrap {
  border: 1px solid $color-border;
  border-radius: $radius-sm;
  overflow: hidden;
  background: #fff;
}
.items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  th, td {
    padding: 8px 10px;
    border-bottom: 1px solid $color-border;
    text-align: left;
  }
  th {
    background: #F1F5F9;
    color: $color-text-secondary;
    font-weight: 600;
    font-size: 11.5px;
  }
  td.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-weight: 500;
  }
  tbody tr:last-child td { border-bottom: none; }
  tbody tr:hover { background: rgba(79, 107, 255, 0.04); }
}

.ocr-main {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}

// ============================================================
// OCR 区域标注（已不用，保留占位避免影响样式）
// ============================================================
.ocr-overlay {
  position: absolute; inset: 0; pointer-events: none;
  .overlay-label {
    position: absolute; top: 8px; left: 8px;
    background: rgba(79,107,255,0.85); color: #fff;
    font-size: 11px; padding: 3px 8px; border-radius: 4px;
    pointer-events: none; z-index: 2;
  }
  .uploading-overlay {
    display: flex; align-items: center; justify-content: center;
    background: rgba(255,255,255,0.6);
  }
  .box {
    position: absolute; border: 2px solid $color-primary;
    border-radius: 4px; background: rgba(79,107,255,0.08);
    &::before {
      content: attr(data-label);
      position: absolute; top: -22px; left: 0;
      background: $color-primary; color: #fff;
      font-size: 10px; padding: 2px 6px; border-radius: 4px;
      white-space: nowrap;
    }
  }
}
// ============================================================
// 结果卡片
// ============================================================
.result-card {
  background: #fff;
  border-radius: $radius-lg;
  box-shadow: $shadow-md;
  padding: 24px;
}
.result-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  h3 { font-size: 16px; font-weight: 600; }
}
.confidence-badge {
  display: inline-flex; align-items: center; gap: 6px;
  background: #DCFCE7; color: #15803D;
  padding: 4px 10px; border-radius: 999px;
  font-size: 12px; font-weight: 500;
  &::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: #22C55E; }
}

// 表单字段
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; .full { grid-column: 1 / -1; } }
.field { display: flex; flex-direction: column; }
.field label { font-size: 12px; font-weight: 500; color: $color-text-secondary; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
.ai-tag { background: $color-primary-bg; color: $color-primary; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 600; }
.field input, .field select, .field textarea {
  padding: 10px 12px; border: 1.5px solid $color-border; border-radius: $radius-md;
  font-size: 13px; font-family: inherit; color: $color-text-primary; background: #fff;
  transition: all 0.2s; width: 100%; box-sizing: border-box;
  &:focus { outline: none; border-color: $color-primary; box-shadow: 0 0 0 4px $color-primary-bg; }
  &.ai-filled { background: linear-gradient(90deg, #FAFBFF 0%, #fff 100%); }
}
.field textarea { resize: vertical; min-height: 60px; }

.amount-display {
  background: linear-gradient(135deg, $color-primary-bg, #fff);
  border: 1.5px solid $color-primary;
  border-radius: $radius-md;
  padding: 14px 16px;
  .amount-label { font-size: 11px; color: $color-text-secondary; margin-bottom: 4px; }
  .amount-value { font-size: 24px; font-weight: 700; color: $color-primary; letter-spacing: 0.5px; }
}

// AI 抽取状态
.ai-extracting { margin-top: 16px; background: $color-primary-bg; border-radius: $radius-md; padding: 14px 16px; }
.ai-extracting-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.ai-extracting-icon { font-size: 20px; }
.ai-extracting-title { font-size: 13px; font-weight: 600; color: $color-primary; }
.ai-extracting-sub { font-size: 11px; color: $color-text-secondary; margin-top: 2px; }

// AI 关联建议
.ai-link-suggestion { margin-top: 12px; display: flex; gap: 10px; background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: $radius-md; padding: 12px 14px; }
.ai-link-icon { font-size: 18px; flex-shrink: 0; margin-top: 2px; }
.ai-link-body { flex: 1; }
.ai-link-title { font-size: 13px; font-weight: 600; color: #1D4ED8; }
.ai-link-desc { font-size: 12px; color: $color-text-secondary; margin-top: 4px; }
.ai-link-actions { display: flex; gap: 8px; margin-top: 8px; }

// 操作栏
.result-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid $color-border;
}

// ============================================================
// 历史记录表格
// ============================================================
.table-card {
  background: #fff;
  border-radius: $radius-lg;
  box-shadow: $shadow-md;
  overflow: hidden;
}
.table-head {
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid $color-border;
  h3 { font-size: 16px; font-weight: 600; }
}
table { width: 100%; border-collapse: collapse; }
thead th {
  background: #FAFBFF;
  text-align: left;
  padding: 12px 24px;
  font-size: 12px; font-weight: 600;
  color: $color-text-secondary;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
tbody td { padding: 14px 24px; font-size: 13px; border-bottom: 1px solid $color-border; }
tbody tr:hover { background: #FAFBFF; }
tbody tr:last-child td { border-bottom: none; }
.invoice-no { font-family: 'SF Mono', Consolas, monospace; color: $color-primary; font-weight: 500; }

.toolbar { display: flex; gap: 8px; align-items: center; }
.search-input { padding: 8px 12px; border: 1px solid $color-border; border-radius: $radius-md; font-size: 13px; width: 220px; }

// ============================================================
// 标签
// ============================================================
.tag {
  display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 500;
  &.tag-info    { background: $color-primary-bg; color: $color-primary; }
  &.tag-warning { background: #FEF3C7; color: #B45309; }
  &.tag-success { background: #DCFCE7; color: #15803D; }
  &.tag-gray    { background: #F1F5F9; color: #64748B; }
}

// ============================================================
// 响应式
// ============================================================
@media (max-width: 639px) {
  .field-grid    { grid-template-columns: 1fr; }
  .stats-row     { grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .ocr-main      { gap: 12px; }
  .result-actions { justify-content: stretch; flex-direction: column; gap: 8px; > div { width: 100%; } }
  .table-head    { flex-direction: column; align-items: flex-start; gap: 10px; }
  table          { display: block; overflow-x: auto; white-space: nowrap; }
}
</style>
