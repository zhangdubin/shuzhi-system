<script setup lang="ts">
/**
 * AiExtract · AI 智能字段抽取（1:1 复刻 design/ai-extract-demo.html）
 * - demo-banner 紫色渐变演示说明
 * - demo-progress 80% 抽取进度
 * - demo-stage 1fr / 1.2fr 左右对比
 *   - 左：原始材料（fake-invoice + 5 extract-box 抽取框叠加）
 *   - 右：抽取结果（ai-summary-card 总览 + 置信度图例 + 11 字段 2 列表单 + 智能关联建议）
 * - 底部 result-actions 操作栏 + 历史准确率趋势卡（4%/11%/85% 堆叠条）
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { aiApi } from '@/api/ai'

const router = useRouter()

const fileInput = ref<HTMLInputElement>()
const fileName = ref('')
const previewUrl = ref<string>('')
const fileExt = ref<string>('')
const uploadedFileId = ref<string>('')
const uploadedFileUrl = ref<string>('')
const submitting = ref(false)
const progress = ref(0)
const status = ref('idle')
const result = ref<Record<string, unknown> | null>(null)
const taskId = ref('')

interface ExtractedField {
  key: string
  label: string
  value: string
  confidence: number
  group?: string
  required?: boolean
  warning?: string
  type?: 'text' | 'select' | 'textarea' | 'date'
  options?: string[]
  mono?: boolean
  highlight?: 'success' | 'warning'  // 高亮（绿色/黄色）
}

const fields = ref<ExtractedField[]>([])

const summary = ref({
  total: 0, high: 0, mid: 0, low: 0,
  cost: 0.002, model: 'PaddleOCR-v3', elapsed: '1.8s',
})

const overallScore = computed(() => {
  if (!fields.value.length) return 0
  const sum = fields.value.reduce((a, b) => a + b.confidence, 0)
  return Math.round((sum / fields.value.length) * 100)
})

function confClass(v: number) {
  if (v >= 0.9) return 'conf-high'
  if (v >= 0.7) return 'conf-mid'
  return 'conf-low'
}
function confLabel(v: number) { return `${Math.round(v * 100)}%` }

function handleFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  fileName.value = f.name
  // 后缀判断
  const ext = (f.name.split('.').pop() || '').toLowerCase()
  fileExt.value = ext
  // 释放旧的
  if (previewUrl.value && previewUrl.value.startsWith('blob:')) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = URL.createObjectURL(f)
  // 重置上传/抽取状态
  uploadedFileId.value = ''
  uploadedFileUrl.value = ''
  result.value = null
  fields.value = []
  status.value = 'idle'
  progress.value = 0
  summary.value = { total: 0, high: 0, mid: 0, low: 0, cost: 0, model: '', elapsed: '' }
}

const isImage = computed(() => /^(png|jpe?g|gif|webp|bmp|svg)$/i.test(fileExt.value))
const isPdf = computed(() => fileExt.value === 'pdf')

async function uploadToServer(file: File): Promise<{ fileId: string; url: string }> {
  const fd = new FormData()
  fd.append('file', file)
  const { http } = await import('@/utils/request')
  const data = await http.post('/common/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  } as any)
  return { fileId: data.fileId, url: data.url }
}

async function handleExtract() {
  if (!fileName.value) return ElMessage.warning('请先选择文件')
  const inputEl = fileInput.value
  const file = inputEl?.files?.[0]
  if (!file) return ElMessage.warning('请重新选择文件')

  submitting.value = true
  status.value = 'uploading'
  progress.value = 5
  result.value = null
  fields.value = []
  summary.value = { total: 0, high: 0, mid: 0, low: 0, cost: 0, model: '', elapsed: '' }

  try {
    // 1) 先把文件传到后端拿到 fileId/url（blob: URL 后端读不到）
    progress.value = 15
    const up = await uploadToServer(file)
    uploadedFileId.value = up.fileId
    uploadedFileUrl.value = up.url
    progress.value = 40
    status.value = 'extracting'

    // 2) 调 AI 抽取
    const r = await aiApi.extractInvoice({
      fileId: up.fileId,
      fileUrl: up.url,
      type: 'invoice',
    })
    taskId.value = r.taskId || r.meta?.traceId || ''
    status.value = 'done'
    progress.value = 100

    if (r.fields) {
      const ext: ExtractedField[] = []
      const groupMap: Record<string, string> = {
        invoiceCode: '基础', invoiceNo: '基础', issueDate: '基础', invoiceType: '基础',
        buyerName: '购销方', buyerTaxId: '购销方', sellerName: '购销方',
        amount: '金额', taxAmount: '金额', totalAmount: '金额', totalAmountCn: '金额', taxRate: '金额',
        remark: '其他',
      }
      const labelMap: Record<string, string> = {
        invoiceCode: '发票代码', invoiceNo: '发票号码', issueDate: '开票日期', invoiceType: '发票类型',
        buyerName: '购方名称', buyerTaxId: '统一社会信用代码', sellerName: '销方名称',
        amount: '金额（不含税）', taxAmount: '税额', totalAmount: '价税合计（小写）', totalAmountCn: '价税合计（大写）',
        taxRate: '税率', remark: '备注',
      }
      // 后端 confidence 是 0-100 百分制，内部统一转 0-1 小数
      for (const [key, info] of Object.entries(r.fields)) {
        const rawConf = Number(info.confidence ?? 0)
        const conf = rawConf > 1 ? rawConf / 100 : rawConf
        ext.push({
          key,
          label: labelMap[key] || key,
          value: String(info.value),
          confidence: conf,
          group: groupMap[key] || '其他',
          required: ['invoiceCode', 'invoiceNo', 'issueDate', 'buyerName', 'totalAmountCn'].includes(key),
          type: key === 'issueDate' ? 'date' : key === 'invoiceType' ? 'select' : key === 'taxRate' ? 'select' : 'text',
          mono: ['invoiceNo', 'buyerTaxId', 'amount', 'taxAmount', 'totalAmount'].includes(key),
          options: key === 'invoiceType' ? ['增值税电子专用发票', '增值税专用发票', '增值税普通发票'] : key === 'taxRate' ? ['3%', '6%', '9%', '13%'] : undefined,
          highlight: key === 'totalAmountCn' || key === 'totalAmount' ? 'success' : key === 'taxRate' && conf < 0.9 ? 'warning' : undefined,
        })
      }
      result.value = r
      fields.value = ext
      summary.value = {
        total: ext.length,
        high: ext.filter(f => f.confidence >= 0.9).length,
        mid: ext.filter(f => f.confidence >= 0.7 && f.confidence < 0.9).length,
        low: ext.filter(f => f.confidence < 0.7).length,
        cost: (r.meta.costCents || 0) / 100,
        model: r.meta.model || '',
        elapsed: `${r.meta.durationMs || 0}ms`,
      }
      ElMessage.success(`AI 抽取完成 · 耗时 ${r.meta.durationMs}ms`)
    } else {
      // 后端没返回 fields（一般是 fileUrl 不可达 / OCR 失败 / 文件非票据）
      status.value = 'done'
      // 把后端原始返回展开，方便排查
      fields.value = [{
        key: 'debug',
        label: '后端返回（调试）',
        value: JSON.stringify(r, null, 2),
        confidence: 0,
        group: '调试',
        type: 'text',
      }] as any
      result.value = r
      console.warn('[AiExtract] 后端未返回 fields，原始响应:', r)
      ElMessage.warning('AI 未识别到字段，请检查文件是否清晰或选择其他文件')
    }
  } catch (e: any) {
    console.error(e)
    ElMessage.error('AI 抽取失败：' + (e?.message || '未知错误'))
  } finally {
    submitting.value = false
  }
}

function fillDemoFields() {
  // 1:1 还原 design/ai-extract-demo.html 13 个字段
  const demo: ExtractedField[] = [
    // 基础（4 字段，design 2×2 grid）
    { key: 'invoiceCode', label: '发票代码', value: '011002000000',          confidence: 0.99, group: '基础',   required: true,  type: 'text' },
    { key: 'invoiceNo',   label: '发票号码', value: '12345678',                confidence: 0.99, group: '基础',   required: true,  type: 'text', mono: true },
    { key: 'issueDate',   label: '开票日期', value: '2024-05-21',              confidence: 0.98, group: '基础',   required: true,  type: 'date' },
    { key: 'invoiceType', label: '发票类型', value: '增值税电子专用发票',       confidence: 0.96, group: '基础',                  type: 'select', options: ['增值税电子专用发票', '增值税专用发票', '增值税普通发票'] },
    // 购销方（3 字段）
    { key: 'buyerName',   label: '购方名称', value: '示例客户有限公司',         confidence: 0.97, group: '购销方', required: true,  type: 'text' },
    { key: 'buyerTaxId',  label: '统一社会信用代码', value: '91110000XXXXXXXX', confidence: 0.92, group: '购销方',                type: 'text', mono: true },
    { key: 'sellerName',  label: '销方名称', value: '数智科技服务（北京）有限公司', confidence: 0.99, group: '购销方',             type: 'text' },
    // 金额（5 字段，design 2×2 grid）
    { key: 'amount',        label: '金额（不含税）',   value: '95,000.00',       confidence: 0.96, group: '金额', required: true, type: 'text', mono: true },
    { key: 'taxAmount',     label: '税额',             value: '5,700.00',        confidence: 0.96, group: '金额',                type: 'text', mono: true },
    { key: 'totalAmountCn', label: '价税合计（大写）', value: '壹拾万零柒佰元整', confidence: 0.98, group: '金额', required: true, type: 'text', highlight: 'success' },
    { key: 'totalAmount',   label: '价税合计（小写）', value: '100,700.00',      confidence: 0.99, group: '金额',                type: 'text', mono: true, highlight: 'success' },
    // 税率（1 字段，黄色高亮，design 黄色边框 + warning）
    { key: 'taxRate',     label: '税率',   value: '6%', confidence: 0.72, group: '金额', warning: '中置信度，建议复核', type: 'select', options: ['6%', '3%', '9%', '13%'], highlight: 'warning' },
    // 其他
    { key: 'remark',      label: '备注',   value: '合同号 C-2024-123（AI 自动识别并关联）', confidence: 0.95, group: '其他', type: 'textarea' },
  ]
  fields.value = demo
  summary.value = {
    total: demo.length, high: demo.filter(d => d.confidence >= 0.9).length,
    mid: demo.filter(d => d.confidence >= 0.7 && d.confidence < 0.9).length,
    low: demo.filter(d => d.confidence < 0.7).length,
    cost: 0.002, model: 'PaddleOCR-v3', elapsed: '1.8s',
  }
}

function handleAccept() { ElMessage.success('已采纳 AI 抽取结果') }
function handleReject() { ElMessage.info('已转人工复核') }
function handleReExtract() { handleExtract() }
async function handleExportJson() {
  if (!fields.value.length) return ElMessage.warning('暂无抽取结果')
  const obj = fields.value.reduce((a, b) => { a[b.key] = b.value; return a }, {} as Record<string, string>)
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `ai-extract-${Date.now()}.json`; a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出 JSON')
}
async function handleCopy() {
  if (!fields.value.length) return ElMessage.warning('暂无抽取结果')
  const text = fields.value.map(f => `${f.label}: ${f.value}`).join('\n')
  try { await navigator.clipboard.writeText(text); ElMessage.success('已复制到剪贴板') }
  catch { const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); ElMessage.success('已复制到剪贴板') }
}

const groupedFields = computed(() => {
  const map = new Map<string, ExtractedField[]>()
  for (const f of fields.value) {
    const g = f.group || '其他'
    if (!map.has(g)) map.set(g, [])
    map.get(g)!.push(f)
  }
  return Array.from(map.entries())
})
const hasResult = computed(() => fields.value.length > 0)

// 按组获取字段
function fieldsOfGroup(group: string) {
  return fields.value.filter(f => (f.group || '其他') === group)
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/dashboard')">首页</a>
          <span class="sep">/</span>
          <a @click="router.push('/ai')">数智（AI）</a>
          <span class="sep">/</span>
          <span class="current">字段抽取演示</span>
        </div>
        <h1>📷 AI 智能字段抽取 <span class="ai-badge phase">Phase 1</span></h1>
        <p class="page-desc">上传发票/合同图片，AI 自动抽取关键字段并结构化展示</p>
      </div>
    </div>

    <!-- demo-banner（design 同款） -->
    <div class="demo-banner">
      <div class="ico">✦</div>
      <div>
        <strong>AI 字段抽取演示</strong> — 左侧为原始材料，右侧为 AI 抽取结果（带 <span class="ai-badge">AI</span> 角标）。本月本能力已节省录入时间 <strong>52 小时</strong>。
      </div>
    </div>

    <!-- demo-progress（design 同款，12/15 字段 80%） -->
    <div v-if="submitting || (status !== 'idle' && !hasResult)" class="demo-progress">
      <div class="stage">
        <span class="label">
          <span class="ai-loading">识别中</span>
          <span>正在抽取字段...</span>
        </span>
        <span class="pct">12/15 字段 · {{ Math.round(progress) }}%</span>
      </div>
      <div class="bar"><div class="fill" :style="{ width: progress + '%' }"></div></div>
      <div v-if="taskId" class="task-id">任务 ID: <span class="mono">{{ taskId }}</span> · 状态 {{ status }}</div>
    </div>

    <!-- demo-stage 左右对比 1fr / 1.2fr（design 同款） -->
    <div class="demo-stage">
      <!-- 左：原始材料 -->
      <div class="demo-source">
        <div class="demo-source-head">
          <h3>📄 原始材料 <span class="muted">{{ fileName || '增值税电子专用发票' }}</span></h3>
          <span v-if="previewUrl" class="muted">{{ status }}</span>
        </div>
        <div class="demo-source-body">
          <input ref="fileInput" type="file" hidden accept="image/*,.pdf" @change="handleFile" />
          <div v-if="!previewUrl" class="upload-zone" @click="fileInput?.click()">
            <div class="upload-content">
              <div class="upload-icon">📄</div>
              <p>点击选择文件</p>
              <p class="muted">支持 JPG / PNG / PDF · 单张最大 10MB</p>
            </div>
          </div>
          <div v-else class="source-preview">
            <img v-if="isImage && previewUrl" :src="previewUrl" :alt="fileName" />
            <iframe v-else-if="isPdf && previewUrl" :src="previewUrl" :title="fileName" frameborder="0" />
            <div v-else class="fake-invoice">
              <div class="fi-title">增值税电子专用发票</div>
              <div class="fi-row"><span class="fi-label">发票代码：</span><span class="fi-value">011002000000</span></div>
              <div class="fi-row"><span class="fi-label">发票号码：</span><span class="fi-value">12345678</span></div>
              <div class="fi-row"><span class="fi-label">开票日期：</span><span class="fi-value">2024年05月21日</span></div>
              <div class="fi-row"><span class="fi-label">购方名称：</span><span class="fi-value">示例客户有限公司</span></div>
              <div class="fi-row"><span class="fi-label">统一社会信用代码：</span><span class="fi-value">91110000XXXXXXXX</span></div>
              <div class="fi-row"><span class="fi-label">销方名称：</span><span class="fi-value">数智科技服务（北京）有限公司</span></div>
              <table class="fi-table">
                <thead><tr><th>货物或应税劳务名称</th><th>数量</th><th>单价</th><th>金额</th><th>税率</th><th>税额</th></tr></thead>
                <tbody>
                  <tr><td>*信息技术服务*系统集成服务费</td><td>1</td><td>80000.00</td><td>80000.00</td><td>6%</td><td>4800.00</td></tr>
                  <tr><td>*信息技术服务*运维服务费</td><td>1</td><td>15000.00</td><td>15000.00</td><td>6%</td><td>900.00</td></tr>
                </tbody>
              </table>
              <div class="fi-row" style="font-weight: 600; margin-top: 6px">
                <span class="fi-label">价税合计：</span>
                <span class="fi-value">壹拾万零柒佰元整（¥100,700.00）</span>
              </div>
              <div class="fi-row"><span class="fi-label">备注：</span><span class="fi-value">合同号 C-2024-123</span></div>
              <div class="fi-stamp">数智科技<br>发票专用章</div>
              <div class="fi-footer">开票人：李雷  复核人：王芳  收款人：张明</div>
              <!-- 5 个 AI 抽取框（design 同款 5 个） -->
              <div v-if="hasResult" class="extract-box" style="top: 78px; left: 90px; width: 120px; height: 14px" data-label="购方名称" />
              <div v-if="hasResult" class="extract-box" style="top: 95px; left: 140px; width: 140px; height: 14px" data-label="统一社会信用代码" />
              <div v-if="hasResult" class="extract-box" style="top: 160px; left: 80px; width: 50px; height: 14px" data-label="税率" />
              <div v-if="hasResult" class="extract-box" style="top: 160px; left: 160px; width: 60px; height: 14px" data-label="金额" />
              <div v-if="hasResult" class="extract-box" style="top: 215px; left: 80px; width: 230px; height: 14px" data-label="价税合计" />
            </div>
          </div>
        </div>
        <div class="demo-source-foot">
          <button v-if="!previewUrl" class="btn btn-primary" @click="fileInput?.click()" style="width: 100%">📁 选择文件</button>
          <button v-else class="btn btn-outline" @click="fileInput?.click()" style="width: 100%">↻ 重新选择</button>
          <button class="btn btn-primary mt" :disabled="submitting" @click="handleExtract">✨ 开始 AI 抽取</button>
        </div>
      </div>

      <!-- 右：抽取结果 -->
      <div class="demo-result">
        <div class="demo-result-head">
          <h3>✦ AI 抽取结果 <span class="ai-badge">自动填入</span></h3>
          <span v-if="hasResult" class="muted">用时 {{ summary.elapsed }}</span>
        </div>

        <div class="demo-result-body">
          <!-- 暂无结果占位 -->
          <div v-if="!hasResult && !submitting" class="empty-result">
            <div class="empty-icon">📭</div>
            <div class="empty-text">上传文件后查看抽取结果</div>
          </div>

          <template v-if="hasResult">
            <!-- ai-summary-card 总览评分 -->
            <div class="ai-summary-card">
              <div class="score">{{ overallScore }}</div>
              <div class="info">
                <strong>整体置信度 {{ overallScore }} 分（{{ overallScore >= 90 ? '优秀' : overallScore >= 70 ? '良好' : '需复核' }}）</strong><br />
                15 个字段中 {{ summary.high }} 个高置信度<span v-if="summary.mid">，{{ summary.mid }} 个需复核（税率）</span>
              </div>
              <button class="btn-detail">📊 详情</button>
            </div>

            <!-- 置信度图例 -->
            <div class="confidence-legend">
              <div class="item"><span class="dot dot-high"></span>高 ≥ 90%</div>
              <div class="item"><span class="dot dot-mid"></span>中 70-90%</div>
              <div class="item"><span class="dot dot-low"></span>低 &lt; 70%</div>
              <div class="item link">查看抽取历史趋势 →</div>
            </div>

            <!-- 基础信息（2×2 grid，design 同款） -->
            <div class="field-grid-2">
              <div v-for="f in fieldsOfGroup('基础')" :key="f.key" :class="['field-row', 'ai-filled', { 'field-required': f.required }]">
                <div class="field-label">
                  <span class="label-left">
                    {{ f.label }}<span v-if="f.required" class="required">*</span>
                    <span class="ai-badge">AI</span>
                  </span>
                  <span :class="['conf-pill', confClass(f.confidence)]">{{ confLabel(f.confidence) }}</span>
                </div>
                <div class="field-input">
                  <input class="form-input" v-if="f.type === 'text' || f.type === 'date'" :class="{ mono: f.mono }" :value="f.value" readonly />
                  <select class="form-select" v-else-if="f.type === 'select'">
                    <option v-for="o in f.options" :key="o" :selected="o === f.value">{{ o }}</option>
                  </select>
                  <span class="ai-tooltip">AI <span class="ai-conf-mini">{{ confLabel(f.confidence) }}</span></span>
                </div>
              </div>
            </div>

            <!-- 购销方（3 字段，1 列） -->
            <div v-for="f in fieldsOfGroup('购销方')" :key="f.key" :class="['field-row', 'ai-filled', 'mt8', { 'field-required': f.required, 'field-cite': f.key === 'buyerName' }]">
              <div class="field-label">
                <span class="label-left">
                  {{ f.label }}<span v-if="f.required" class="required">*</span>
                  <span v-if="f.key === 'buyerName'" class="ai-citation" title="来源：原图第一行购方信息">来源</span>
                  <span v-if="f.key === 'buyerName'" class="source-popover">📍 来自原图 "购方名称" 行</span>
                </span>
                <span :class="['conf-pill', confClass(f.confidence)]">{{ confLabel(f.confidence) }}</span>
              </div>
              <div class="field-input">
                <input class="form-input" :class="{ mono: f.mono }" :value="f.value" readonly />
                <span class="ai-tooltip">AI <span class="ai-conf-mini">{{ confLabel(f.confidence) }}</span></span>
              </div>
            </div>

            <!-- 金额（2×2 grid 4 字段 + 1 行税率） -->
            <div class="field-grid-2 mt8">
              <div v-for="f in fieldsOfGroup('金额').filter(x => x.key !== 'taxRate')" :key="f.key" :class="['field-row', 'ai-filled', { 'field-required': f.required, 'field-highlight-success': f.highlight === 'success' }]">
                <div class="field-label">
                  <span class="label-left">
                    {{ f.label }}<span v-if="f.required" class="required">*</span>
                    <span class="ai-badge">AI</span>
                  </span>
                  <span :class="['conf-pill', confClass(f.confidence)]">{{ confLabel(f.confidence) }}</span>
                </div>
                <div class="field-input">
                  <input class="form-input" :class="{ mono: f.mono }" :value="f.value" readonly />
                  <span class="ai-tooltip">AI <span class="ai-conf-mini">{{ confLabel(f.confidence) }}</span></span>
                </div>
              </div>
            </div>

            <!-- 税率（黄色高亮，design warning 风格） -->
            <div v-if="fieldsOfGroup('金额').find(x => x.key === 'taxRate')" class="field-row ai-filled field-highlight-warning mt8">
              <div class="field-label">
                <span class="label-left">
                  税率
                  <span class="ai-confidence mid">72% 需复核</span>
                </span>
                <span class="muted">AI 推测: 6%</span>
              </div>
              <div class="field-input">
                <select class="form-select" v-if="true">
                  <option>6%</option><option>3%</option><option>9%</option><option>13%</option>
                </select>
                <span class="ai-tooltip warning">AI <span class="ai-conf-mini">72%</span></span>
              </div>
            </div>

            <!-- 备注（1 字段 textarea） -->
            <div v-if="fieldsOfGroup('其他').length" class="field-row ai-filled mt8">
              <div class="field-label">
                <span class="label-left">备注 <span class="ai-badge">AI</span></span>
                <span :class="['conf-pill', confClass(fieldsOfGroup('其他')[0].confidence)]">{{ confLabel(fieldsOfGroup('其他')[0].confidence) }}</span>
              </div>
              <div class="field-input">
                <textarea class="form-textarea" rows="2" readonly>{{ fieldsOfGroup('其他')[0].value }}</textarea>
                <span class="ai-tooltip">AI <span class="ai-conf-mini">{{ confLabel(fieldsOfGroup('其他')[0].confidence) }}</span></span>
              </div>
            </div>

            <!-- 调试：后端原始响应（仅当 fields 为空时显示） -->
            <div v-if="fieldsOfGroup('调试').length" class="field-row ai-filled mt8" style="border: 1px dashed #F59E0B; background: #FFFBEB;">
              <div class="field-label">
                <span class="label-left">⚠️ AI 未识别到字段（调试）<span class="ai-badge" style="background:#F59E0B">DEBUG</span></span>
              </div>
              <div class="field-input">
                <textarea class="form-textarea" rows="8" readonly style="font-family: monospace; font-size: 11.5px;">{{ fieldsOfGroup('调试')[0].value }}</textarea>
              </div>
            </div>

            <!-- 智能关联建议（design 同款） -->
            <div class="ai-suggestion">
              <div class="ai-s-icon">🔗</div>
              <div class="ai-s-body">
                <div class="ai-s-title">智能关联建议</div>
                <div class="ai-s-desc">
                  AI 检测到发票备注中包含合同号 <strong>C-2024-123</strong>，建议自动关联到 <strong>「数智化二期」项目</strong>，并匹配 <strong>客户：示例客户有限公司</strong>。
                </div>
                <div class="ai-s-actions">
                  <button class="btn-s primary" @click="handleAccept">✓ 采纳关联</button>
                  <button class="btn-s" @click="handleReject">手动选择</button>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- result-actions 底部操作栏（design 同款） -->
        <div v-if="hasResult" class="result-actions">
          <div class="meta">✦ 抽取消耗时 <strong>{{ summary.elapsed }}</strong> · 模型 <strong>{{ summary.model }}</strong> · 成本 <strong>{{ summary.cost.toFixed(3) }} 元</strong></div>
          <div class="actions">
            <button class="btn-s" @click="handleReExtract">🔄 重新抽取</button>
            <button class="btn-s" @click="handleExportJson">📥 导出 JSON</button>
            <button class="btn-s primary" @click="handleAccept">✓ 确认保存</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部历史准确率趋势（design 同款） -->
    <div class="history-card">
      <div class="hc-head">
        <h3>抽取准确率趋势 <span class="muted">最近 30 天</span></h3>
        <a class="link-ai">查看明细 →</a>
      </div>
      <div class="hc-body">
        <div class="history-strip">
          <span class="muted">低置信度</span>
          <div class="bar-row">
            <div class="seg low" style="width: 4%"></div>
            <div class="seg mid" style="width: 11%"></div>
            <div class="seg" style="width: 85%"></div>
          </div>
          <span class="muted">高置信度</span>
          <span class="pct">94.2%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

$color-ai: #7C3AED;
$color-ai-2: #4F6BFF;
$gradient-ai: linear-gradient(135deg, #4F6BFF 0%, #7C3AED 100%);
$color-ai-bg: rgba(124, 58, 237, 0.05);
$color-ai-border: rgba(124, 58, 237, 0.25);
$gradient-ai-soft: linear-gradient(135deg, rgba(79, 107, 255, 0.15) 0%, rgba(124, 58, 237, 0.15) 100%);

.page-header h1 { @include page-title-h1; margin: 0; display: flex; align-items: center; gap: 8px; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-ai; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.ai-badge { display: inline-block; padding: 1px 6px; background: $gradient-ai; color: #fff; border-radius: 4px; font-size: 10.5px; font-weight: 600; vertical-align: middle; margin-left: 4px; }
.ai-badge.phase { background: rgba(79, 107, 255, 0.1); color: #4F6BFF; font-weight: 500; font-size: 11px; padding: 1px 8px; }
.muted { color: $color-text-tertiary; font-size: 12px; }
.mono { font-family: $font-family-mono; }
.link-ai { font-size: 12px; color: $color-ai; cursor: pointer; &:hover { text-decoration: underline; } }

// demo-banner
.demo-banner { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: $gradient-ai-soft; border: 1px solid $color-ai-border; border-radius: $radius-lg; margin-bottom: 16px; font-size: 13px; color: $color-text-secondary; .ico { width: 32px; height: 32px; background: $gradient-ai; border-radius: $radius-md; color: #fff; display: grid; place-items: center; font-size: 14px; font-weight: 700; flex-shrink: 0; } strong { color: $color-text-primary; } }

// demo-progress
.demo-progress { background: $color-ai-bg; border: 1px solid $color-ai-border; border-radius: $radius-md; padding: 14px 18px; margin-bottom: 16px; .stage { font-size: 12.5px; color: $color-text-secondary; margin-bottom: 8px; display: flex; justify-content: space-between; .label { display: flex; align-items: center; gap: 8px; } .pct { color: $color-ai; font-weight: 600; } } .bar { height: 6px; background: #fff; border-radius: 999px; overflow: hidden; .fill { height: 100%; background: $gradient-ai; border-radius: 999px; transition: width 0.3s; } } .task-id { margin-top: 8px; font-size: 11.5px; color: $color-text-tertiary; } }
.ai-loading { display: inline-block; padding: 2px 8px; background: $gradient-ai; color: #fff; border-radius: 4px; font-size: 11.5px; font-weight: 600; animation: ai-pulse 1.5s infinite; }
@keyframes ai-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

// demo-stage 1fr / 1.2fr
.demo-stage { display: grid; grid-template-columns: 1fr 1.2fr; gap: 20px; margin-bottom: 20px; @media (max-width: 1000px) { grid-template-columns: 1fr; } }

// 左：原始材料
.demo-source { background: #fff; border-radius: $radius-lg; border: 1px solid $color-border; overflow: hidden; }
.demo-source-head { padding: 14px 18px; border-bottom: 1px solid $color-border; display: flex; justify-content: space-between; align-items: center; h3 { font-size: 14px; font-weight: 600; margin: 0; display: flex; align-items: center; gap: 8px; } }
.demo-source-body { padding: 20px; background: #F8FAFC; min-height: 540px; }
.demo-source-foot { padding: 12px 18px; border-top: 1px solid $color-border; background: #fff; .mt { margin-top: 8px; } }

.upload-zone { border: 2px dashed $color-border-strong; border-radius: $radius-md; min-height: 220px; display: flex; align-items: center; justify-content: center; cursor: pointer; background: #fff; transition: all 0.2s; &:hover { border-color: $color-primary; background: rgba(79, 107, 255, 0.04); } }
.upload-content { text-align: center; color: #94A3B8; .upload-icon { font-size: 48px; margin-bottom: 6px; } p { margin: 4px 0; font-size: 13px; } .muted { font-size: 11.5px; } }

.source-preview { position: relative; background: #fff; border: 1px solid $color-border; border-radius: $radius-md; overflow: hidden; img { display: block; max-width: 100%; max-height: 540px; margin: 0 auto; } }

// fake-invoice
.fake-invoice { padding: 18px 20px; font-size: 10.5px; color: #1E293B; position: relative; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); .fi-title { text-align: center; font-size: 15px; font-weight: 700; margin-bottom: 14px; color: #0F172A; } .fi-row { display: flex; margin-bottom: 5px; .fi-label { color: #64748B; min-width: 80px; } .fi-value { color: #0F172A; font-weight: 500; } } .fi-table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 10px; th, td { border: 1px solid #CBD5E1; padding: 4px 6px; text-align: left; } th { background: #F1F5F9; font-weight: 600; } } .fi-stamp { position: absolute; right: 40px; bottom: 80px; width: 70px; height: 70px; border: 2px solid #DC2626; border-radius: 50%; color: #DC2626; display: grid; place-items: center; font-size: 11px; font-weight: 700; text-align: center; transform: rotate(-12deg); opacity: 0.75; } .fi-footer { border-top: 1px dashed #CBD5E1; padding-top: 8px; margin-top: 10px; font-size: 9.5px; color: #64748B; } }

// extract-box
.extract-box { position: absolute; border: 2px solid $color-ai; background: rgba(124, 58, 237, 0.08); border-radius: 3px; pointer-events: none; animation: extract-pulse 1.5s infinite; &::after { content: attr(data-label); position: absolute; bottom: 100%; left: 0; background: $gradient-ai; color: #fff; font-size: 10px; padding: 2px 6px; border-radius: 3px 3px 0 0; font-weight: 600; white-space: nowrap; } }
@keyframes extract-pulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(124, 58, 237, 0.3); } 50% { box-shadow: 0 0 0 6px rgba(124, 58, 237, 0); } }

// 右：抽取结果
.demo-result { background: #fff; border-radius: $radius-lg; border: 1px solid $color-border; overflow: hidden; }
.demo-result-head { padding: 14px 18px; border-bottom: 1px solid $color-border; display: flex; justify-content: space-between; align-items: center; h3 { font-size: 14px; font-weight: 600; margin: 0; display: flex; align-items: center; gap: 8px; } }
.demo-result-body { padding: 20px; min-height: 540px; }

.empty-result { text-align: center; padding: 80px 20px; .empty-icon { font-size: 56px; margin-bottom: 8px; opacity: 0.4; } .empty-text { font-size: 13px; color: $color-text-tertiary; } }

// ai-summary-card
.ai-summary-card { background: $color-ai-bg; border: 1px solid $color-ai-border; border-radius: $radius-md; padding: 12px 16px; margin-bottom: 16px; display: flex; align-items: center; gap: 14px; .score { font-size: 28px; font-weight: 700; color: $color-ai; font-family: $font-family-mono; } .info { flex: 1; font-size: 12.5px; color: $color-text-secondary; line-height: 1.5; } .info strong { color: $color-text-primary; } .btn-detail { background: #fff; color: $color-text-primary; border: 1px solid $color-border; border-radius: $radius-sm; padding: 4px 10px; font-size: 12px; cursor: pointer; &:hover { border-color: $color-ai; color: $color-ai; } } }

// confidence-legend
.confidence-legend { display: flex; gap: 14px; padding: 10px 14px; background: #F8FAFC; border-radius: $radius-sm; margin-bottom: 16px; font-size: 12px; color: $color-text-secondary; .item { display: flex; align-items: center; gap: 5px; &.link { margin-left: auto; color: $color-ai; cursor: pointer; } } .dot { width: 8px; height: 8px; border-radius: 50%; &.dot-high { background: #10B981; } &.dot-mid { background: #F59E0B; } &.dot-low { background: #EF4444; } } }

// field-grid-2
.field-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

// field-row
.field-row { margin-bottom: 16px; position: relative; &.mt8 { margin-top: 8px; } }
.field-label { display: flex; justify-content: space-between; align-items: center; font-size: 12.5px; color: $color-text-secondary; margin-bottom: 6px; .label-left { display: flex; align-items: center; gap: 6px; } .required { color: $color-danger; } }
.field-input { position: relative; }
.form-input, .form-textarea, .form-select { width: 100%; padding: 9px 12px; border: 1px solid $color-border; border-radius: $radius-sm; font-size: 13px; color: $color-text-primary; background: #fff; transition: all 0.2s; font-family: inherit; &:focus { outline: none; border-color: $color-primary; box-shadow: 0 0 0 3px $color-primary-bg; } &.mono { font-family: $font-family-mono; font-weight: 600; } }
.form-textarea { min-height: 60px; resize: vertical; }

// ai-filled
.ai-filled { .form-input, .form-textarea, .form-select { background: linear-gradient(90deg, #F5F3FF 0%, #fff 100%); border-color: $color-ai; padding-right: 80px; } }

// conf-pill
.conf-pill { min-width: 42px; text-align: center; padding: 2px 8px; border-radius: 999px; font-size: 11.5px; font-weight: 600; &.conf-high { background: rgba(16, 185, 129, 0.12); color: #047857; } &.conf-mid { background: rgba(245, 158, 11, 0.12); color: #B45309; } &.conf-low { background: rgba(239, 68, 68, 0.12); color: #B91C1C; } }

// ai-tooltip
.ai-tooltip { position: absolute; top: 50%; transform: translateY(-50%); right: 8px; display: inline-flex; align-items: center; gap: 4px; background: $gradient-ai; color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 999px; font-weight: 600; &.warning { background: #F59E0B; } }
.ai-conf-mini { font-size: 10.5px; opacity: 0.9; }

// ai-confidence
.ai-confidence { font-size: 11px; padding: 1px 6px; border-radius: 999px; font-weight: 500; &.mid { background: rgba(245, 158, 11, 0.12); color: #B45309; } }

// field-highlight
.field-highlight-success { background: $color-success-bg; padding: 10px 12px; border-radius: $radius-md; border-left: 3px solid $color-success; .field-label .label-left { color: $color-text-primary; font-weight: 600; } }
.field-highlight-warning { border-left: 3px solid #F59E0B; background: rgba(245, 158, 11, 0.05); padding: 10px 12px; border-radius: $radius-md; }

// field-cite 来源 popover
.field-cite { .ai-citation { font-size: 10.5px; color: $color-ai; background: $color-ai-bg; padding: 1px 6px; border-radius: $radius-sm; cursor: help; } .source-popover { display: none; } }

// ai-suggestion
.ai-suggestion { display: flex; gap: 12px; padding: 12px 14px; background: $gradient-ai-soft; border: 1px solid $color-ai-border; border-radius: $radius-md; margin-top: 16px; .ai-s-icon { font-size: 20px; flex-shrink: 0; } .ai-s-body { flex: 1; } .ai-s-title { font-size: 13px; font-weight: 600; color: $color-text-primary; margin-bottom: 4px; } .ai-s-desc { font-size: 12.5px; color: $color-text-secondary; line-height: 1.6; margin-bottom: 8px; strong { color: $color-primary; } } .ai-s-actions { display: flex; gap: 6px; } .btn-s { padding: 4px 10px; font-size: 12px; background: #fff; border: 1px solid $color-border; color: $color-text-primary; border-radius: $radius-sm; cursor: pointer; font-family: inherit; transition: all 0.15s; &:hover { border-color: $color-ai; color: $color-ai; } &.primary { background: $gradient-ai; color: #fff; border-color: transparent; &:hover { box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4); } } } }

// result-actions
.result-actions { display: flex; gap: 10px; padding: 14px 20px; background: #F8FAFC; border-top: 1px solid $color-border; justify-content: space-between; align-items: center; .meta { font-size: 12px; color: $color-text-tertiary; } .actions { display: flex; gap: 8px; } }

// history-card（design 底部）
.history-card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; overflow: hidden; }
.hc-head { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid $color-border; h3 { font-size: 14px; font-weight: 600; margin: 0; } }
.hc-body { padding: 4px 22px 16px; }
.history-strip { display: flex; align-items: center; gap: 12px; font-size: 12px; color: $color-text-tertiary; .bar-row { flex: 1; height: 4px; background: #F1F5F9; border-radius: 999px; overflow: hidden; display: flex; } .seg { height: 100%; background: $color-success; &.mid { background: #F59E0B; } &.low { background: $color-danger; } } .pct { margin-left: 8px; font-family: $font-family-mono; font-weight: 600; color: $color-text-primary; font-size: 13px; } }

// btn
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 14px; height: 36px; font-size: 13px; font-weight: 500; border-radius: $radius-md; transition: all 0.15s; border: 1px solid transparent; cursor: pointer; font-family: inherit; }
.btn-primary { background: $gradient-ai; color: #fff; &:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4); } }
.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover { border-color: $color-ai; color: $color-ai; } }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
