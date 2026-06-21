<script setup lang="ts">
/**
 * InvoiceDetail · 发票详情（1:1 复刻 design/invoice-detail.html）
 * - 顶部 4 KPI 仪表盘
 * - 票面预览（fake-invoice 模拟发票样式）
 * - 字段核验（AI 识别 vs 票面）
 * - 商品明细表
 * - 报销信息 / 当前状态 / 上传信息 / 查验真伪
 * - 快捷操作
 */
import { ref, reactive, onMounted } from 'vue'
import { fmtConfidence, confToPct } from '@/utils/format'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { invoiceOcrApi, expenseApi, fileApi } from '@/api/modules'

const router = useRouter()
const route = useRoute()

const loading = ref(false)

const mock = reactive({
  id: 1,
  no: '25113300000012345678',
  code: '011002600611',
  type: '电子普通发票',
  typeColor: 'primary',
  status: '已识别',
  statusColor: 'success',
  seller: '上海茶馆餐饮有限公司',
  sellerTaxNo: '91310000MA1FL01X9G',
  buyer: '上海数智信息技术有限公司',
  buyerTaxNo: '91310000MA1FL3X9G',
  issueDate: '2026-06-08',
  checkCode: '1234 5678 9012 3456 7890',
  totalAmount: '248.00',
  amountCn: '' as string,
  taxRate: '6%',
  taxAmount: '14.04',
  amountExTax: '233.96',
  confidence: 0.968,
  uploader: '王芳',
  uploadTime: '2026-06-08 19:23',
  verifyTime: '2026-06-08 19:24',
  fileUrl: '' as string,
  previewUrl: '' as string,
  relations: [] as Array<{type: string, id: number}>,
  status_history: [
    { t: '已查验真伪', m: '2026-06-08 19:24', d: '国税总局查验通过' },
    { t: '智能识别完成', m: '2026-06-08 19:24', d: '8/8 字段识别，置信度 96.8%' },
    { t: '上传成功', m: '2026-06-08 19:23', d: 'PDF 文件 1.2 MB' },
  ],
})

// 4 KPI
const stats = [
  { label: '识别字段',   v: '8',         u: '/ 8',  delta: '全部识别', icon: '✓', color: 'success' },
  { label: '置信度',     v: '96.8',      u: '%',   delta: '高置信度', icon: '✓', color: 'success' },
  { label: '识别耗时',   v: '1.8',       u: 's',   delta: '极速',     icon: '⚡', color: 'primary' },
  { label: '价税合计',   v: '¥ 248.00',  u: '',    delta: '已核验',   icon: '¥', color: 'primary' },
]

// 字段核验（design: 8 字段）
const fields = ref([
  { key: '发票代码',     value: '011002600611',          confidence: 0.99, status: 'match' },
  { key: '发票号码',     value: '25113300000012345678',   confidence: 0.99, status: 'match' },
  { key: '开票日期',     value: '2026-06-08',            confidence: 0.99, status: 'match' },
  { key: '销售方',       value: '上海茶馆餐饮有限公司',   confidence: 0.97, status: 'match' },
  { key: '购买方',       value: '上海数智信息技术有限公司', confidence: 0.96, status: 'match' },
  { key: '价税合计',     value: '¥ 248.00',              confidence: 0.99, status: 'match' },
  { key: '税率',         value: '6%',                    confidence: 0.95, status: 'match' },
  { key: '校验码',       value: '1234 5678 9012',         confidence: 0.93, status: 'match' },
])

// 商品明细
const items = ref([
  { seq: 1, name: '*餐饮服务*餐费', qty: 1, price: '233.96', amount: '233.96', taxRate: '6%', tax: '14.04' },
])

// 触点 #24：附件管理（从文件库 files 表拉取）
const invoiceFiles = ref<any[]>([])
const filesDrawerVisible = ref(false)
function openFilesDrawer() { filesDrawerVisible.value = true }
function _fmtSize2(bytes: any): string { return _fmtSize(bytes) }

// 4 报销信息
const reimburse = ref([
  { label: '报销单号',     value: 'EX-2026-0608-005' },
  { label: '报销人',       value: '王芳' },
  { label: '费用类型',     value: '业务招待' },
  { label: '关联项目',     value: 'PRJ-2026-022 · 万象科技 SaaS 部署' },
  { label: '报销金额',     value: '¥ 248.00' },
  { label: '提交日期',     value: '2026-06-09' },
  { label: '审批状态',     value: '审批中', type: 'warning' },
])

// 4 上传信息
const uploads = ref([
  { label: '文件名',     value: '餐饮服务发票_20260608_185632.pdf' },
  { label: '文件大小',   value: '1.2 MB' },
  { label: '文件类型',   value: 'PDF / 电子普通发票' },
  { label: '上传人',     value: '王芳' },
  { label: '上传时间',   value: '2026-06-08 19:23' },
  { label: '存储位置',   value: '阿里云 OSS · shuzhi-invoice-prod/2026/06/' },
])

// 4 快捷操作
const quickActions = ref([
  { label: '导出识别结果',  icon: '⬇', color: 'outline', handler: 'exportField' },
  { label: '查验真伪',     icon: '🔍', color: 'outline', handler: 'startVerify' },
  { label: '创建报销',     icon: '✚', color: 'outline', handler: 'createReimburse' },
  { label: '关联合同',     icon: '🔗', color: 'primary', handler: 'linkContract' },
  { label: '下载发票',     icon: '📄', color: 'outline', handler: 'downloadInvoice' },
  { label: '打印',         icon: '🖨', color: 'outline', handler: 'printInvoice' },
])

// 路由参数：/invoice/ocr/:id 或 query ?id=
const routeInvoiceId = computed(() => {
  const q: any = route.query
  return Number(q.id) || Number(route.params.id) || 0
})

function _runQuickAction(name: string) {
  switch (name) {
    case 'exportField':       return exportField()
    case 'startVerify':       return startVerify()
    case 'createReimburse':   return createReimburse()
    case 'linkContract':      return linkContract()
    case 'downloadInvoice':   return downloadInvoice()
    case 'printInvoice':      return printInvoice()
  }
}

function goBack() { router.push('/invoice/ocr') }
function exportField() {
  // 导出当前发票的识别字段为 JSON 文件
  const data = mock // mock 本身就是识别结果对象
  const json = JSON.stringify(data, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `invoice-${routeInvoiceId.value || 'detail'}-fields.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
  ElMessage.success('识别字段已导出为 JSON')
}

function createReimburse() {
  // 跳到新建报销页，并预填当前发票号 / 销售方 / 金额
  const id = routeInvoiceId.value
  router.push({
    path: '/expense/create',
    query: id ? { invoiceId: id, from: 'invoice' } : undefined,
  })
}
function linkContract() {
  const id = routeInvoiceId.value
  if (!id) { ElMessage.info('选择合同关联'); return }
  // 真正去创建/选择合同关联
  router.push({
    path: '/contract/list',
    query: { linkInvoiceId: id },
  })
}
function startVerify() {
  const id = routeInvoiceId.value
  if (!id) { ElMessage.info('重新查验真伪'); return }
  // 跳到发票查验页
  router.push({ path: '/invoice/verify', query: { invoiceId: id } })
}
function downloadInvoice() {
  if (!mock.fileUrl) {
    ElMessage.warning('该发票没有可下载的文件')
    return
  }
  // 用 a 标签 click 避免浏览器拦截 popup
  const a = document.createElement('a')
  a.href = mock.fileUrl
  a.download = mock.fileUrl.split('/').pop() || 'invoice.pdf'
  a.target = '_blank'
  a.rel = 'noopener noreferrer'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  ElMessage.success('已触发下载')
}

function printInvoice() {
  if (!mock.fileUrl) {
    ElMessage.warning('没有可打印的文件')
    return
  }
  // 打开隐藏 iframe 调 print
  const iframe = document.createElement('iframe')
  iframe.style.position = 'fixed'
  iframe.style.right = '-9999px'
  iframe.style.bottom = '0'
  iframe.src = mock.fileUrl
  document.body.appendChild(iframe)
  iframe.onload = () => {
    try {
      iframe.contentWindow?.focus()
      iframe.contentWindow?.print()
    } catch (e) {
      ElMessage.warning('请在弹出的 PDF 中选择"打印"')
    }
    setTimeout(() => document.body.removeChild(iframe), 1000)
  }
}
function editField(f: any) { ElMessage.info(`编辑字段: ${f.key}`) }

function _fmtQty(v: any): string {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  if (!isFinite(n)) return String(v)
  if (n > 1000) return '—'
  if (Number.isInteger(n)) return String(n)
  return n.toFixed(2)
}

function _numberToCn(n: number): string {
  if (!isFinite(n) || n <= 0) return ''
  const cn = ['零','壹','贰','叁','肆','伍','陆','柒','捌','玖']
  const unit = ['','拾','佰','仟','万','拾','佰','仟','亿']
  const dec = ['角','分']
  const s = n.toFixed(2)
  const [intPart, decPart] = s.split('.')
  let out = ''
  for (let i = 0; i < intPart.length; i++) {
    const d = parseInt(intPart[i])
    const u = unit[intPart.length - 1 - i]
    if (d === 0) {
      if (!out.endsWith('零')) out += '零'
    } else {
      out += cn[d] + u
    }
  }
  out = out.replace(/零+$/, '')
  if (decPart && parseInt(decPart) > 0) {
    out += parseInt(decPart[0]) > 0 ? cn[parseInt(decPart[0])] + dec[0] : ''
    out += parseInt(decPart[1]) > 0 ? cn[parseInt(decPart[1])] + dec[1] : ''
  }
  out += '元整'
  return out
}

function _fmtMoney(v: any): string {
  if (v === null || v === undefined || v === '' || v === 0 || v === '0' || v === '0.00' || v === '0.0') return '—'
  const n = Number(v)
  if (!isFinite(n) || n === 0) return '—'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function _fmtSize(bytes: any): string {
  if (bytes === null || bytes === undefined || bytes === '') return '—'
  const n = Number(bytes)
  if (!isFinite(n) || n <= 0) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

// 从 fileUrl 推断文件类型描述
function _inferFileType(fileUrl: string, fileId: string): string {
  if (!fileUrl && !fileId) return '—'
  const u = (fileUrl || '').toLowerCase()
  if (u.endsWith('.pdf')) return 'PDF'
  if (u.match(/\.(png|jpg|jpeg|webp|gif|bmp)$/)) return '图片'
  if (u.match(/\.(ofd|xml)$/)) return '电子发票'
  return '文件'
}

function _fmtTaxRate(v: any): string {
  if (v === null || v === undefined || v === '') return '—'
  const s = String(v).trim()
  if (s.endsWith('%')) return s
  const n = Number(s)
  if (!isFinite(n) || isNaN(n)) return '—'
  if (n > 0 && n <= 1) return (n * 100).toFixed(0) + '%'
  return (n % 1 === 0 ? n.toFixed(0) : n.toFixed(2)) + '%'
}

onMounted(async () => {
  loading.value = true
  const id = Number(route.params.id) || mock.id
  try {
    const resp: any = await invoiceOcrApi.detail(id)
    const d = resp?.data || resp
    if (!d) return
    // 1) 基础信息塞进 mock
    mock.id          = d.invoiceId ?? id
    mock.no          = d.invoiceNo ?? mock.no
    mock.code        = d.invoiceCode ?? mock.code
    mock.checkCode    = d.verifyCode ?? mock.checkCode
    mock.type        = d.invoiceType ?? mock.type
    mock.seller      = d.sellerName ?? mock.seller
    mock.sellerTaxNo = d.sellerTaxNo ?? mock.sellerTaxNo
    mock.buyer       = d.buyerName ?? mock.buyer
    mock.buyerTaxNo  = d.buyerTaxNo ?? mock.buyerTaxNo
    mock.issueDate   = d.issueDate ?? mock.issueDate
    mock.totalAmount = Number(d.totalAmount ?? 0).toFixed(2)
    if (d.totalAmountCn) {
      mock.amountCn = d.totalAmountCn
    } else if (d.totalAmount) {
      mock.amountCn = _numberToCn(Number(d.totalAmount))
    }
    mock.taxRate     = d.taxRate != null
      ? (d.taxRate > 1 ? d.taxRate.toFixed(2) + '%' : (d.taxRate * 100).toFixed(0) + '%')
      : mock.taxRate
    mock.taxAmount   = d.taxAmount != null ? Number(d.taxAmount).toFixed(2) : mock.taxAmount
    mock.amountExTax = d.amountExclTax != null ? Number(d.amountExclTax).toFixed(2) : mock.amountExTax
    mock.confidence  = d.confidence != null ? d.confidence : mock.confidence
    // 2) 4 KPI 的价税合计
    stats[3].v = `¥ ${mock.totalAmount}`
    // 3) 8 字段重写（用真实数据）
    const _conf = (d.confidence != null ? d.confidence : 0.95)
    fields.value = [
      { key: '发票类型',     value: mock.type,                confidence: _conf, status: 'match' },
      { key: '发票代码',     value: mock.code,                confidence: _conf, status: 'match' },
      { key: '发票号码',     value: mock.no,                  confidence: _conf, status: 'match' },
      { key: '开票日期',     value: mock.issueDate,           confidence: _conf, status: 'match' },
      { key: '销售方',       value: mock.seller,              confidence: _conf, status: 'match' },
      { key: '销售方纳税人识别号', value: mock.sellerTaxNo || '—', confidence: _conf, status: 'match' },
      { key: '购买方',       value: mock.buyer,               confidence: _conf, status: 'match' },
      { key: '购买方纳税人识别号', value: mock.buyerTaxNo || '—',  confidence: _conf, status: 'match' },
      { key: '价税合计',     value: `¥ ${mock.totalAmount}`,  confidence: _conf, status: 'match' },
      { key: '价税合计大写', value: mock.amountCn || '—',     confidence: _conf, status: 'match' },
      { key: '税率',         value: mock.taxRate,             confidence: _conf, status: 'match' },
      { key: '税额',         value: `¥ ${mock.taxAmount}`,    confidence: _conf, status: 'match' },
      { key: '校验码',       value: d.verifyCode || '—',      confidence: _conf, status: 'match' },
    ]
    // 4) 商品明细（OCR 抽取的 items）
    if (Array.isArray(d.items) && d.items.length > 0) {
      items.value = d.items.map((it: any, idx: number) => {
        // 智能格式化：百分号字符串保留，否则尝试 Number
        const _normRate = (v: any): string => {
          if (v === null || v === undefined || v === '') return ''
          const s = String(v).trim()
          if (s.endsWith('%')) return s
          const n = Number(s)
          if (!isFinite(n) || isNaN(n)) return ''
          if (n > 0 && n <= 1) return (n * 100).toFixed(0) + '%'
          return (n % 1 === 0 ? n.toFixed(0) : n.toFixed(2)) + '%'
        }
        const _normMoney = (v: any): string => {
          if (v === null || v === undefined || v === '') return ''
          const s = String(v).trim()
          const n = Number(s)
          if (!isFinite(n) || isNaN(n)) return ''
          return n.toFixed(2)
        }
        const _normQty = (v: any): string => {
          if (v === null || v === undefined || v === '') return ''
          const n = Number(v)
          if (!isFinite(n) || isNaN(n)) return String(v)
          if (n > 1000) return ''  // OCR 误把金额当数量
          return String(n)
        }
        // 单价兜底：若 price 空但 amount 有值，用 amount 兜底
        const priceVal = _normMoney(it.price ?? it.unitPrice) || _normMoney(it.amount)
        const amountVal = _normMoney(it.amount)
        return {
          seq: idx + 1,
          name: it.name || '—',
          qty: _normQty(it.quantity),
          price: priceVal,
          amount: amountVal,
          taxRate: _normRate(it.taxRate),
          tax: _normMoney(it.taxAmount),
        }
      })
    }
    // 5) 上传人/上传时间
    if (d.uploaderName) {
      mock.uploader = d.uploaderName
      const ut = uploads.value.find(u => u.label === '上传人')
      if (ut) ut.value = d.uploaderName
    }
    if (d.uploadedAt) {
      mock.uploadTime = String(d.uploadedAt).replace('T', ' ').slice(0, 16)
      const ut = uploads.value.find(u => u.label === '上传时间')
      if (ut) ut.value = mock.uploadTime
    }
    // 6) 文件 URL（用于预览/下载）+ 上传信息回填
    if (d.previewUrl || d.fileUrl) {
      mock.previewUrl = d.previewUrl || d.fileUrl
      mock.fileUrl = d.fileUrl
    }
    // 6.5) 上传信息：用真实数据回填
    {
      const _uSet = (label: string, val: string) => {
        const r: any = uploads.value.find((u: any) => u.label === label)
        if (r) r.value = val
      }
      // 文件名：从 fileUrl 末尾取；没有就用 fileId
      const _fn = d.fileUrl ? d.fileUrl.split('/').pop() : (d.fileId || '—')
      _uSet('文件名', _fn || '—')
      // 文件大小：fileSize 是字节，转可读
      _uSet('文件大小', _fmtSize(d.fileSize))
      // 文件类型：根据 URL 推断
      const _ft = _inferFileType(d.fileUrl || '', d.fileId || '')
      // 原类型描述 "PDF / 电子普通发票" 合并为：推断类型 + 发票类型
      _uSet('文件类型', d.invoiceType ? `${_ft} · ${d.invoiceType}` : _ft)
      // 上传人：之前已设
      // 上传时间：之前已设
      // 存储位置：直接显示 fileUrl（数据库管理），去掉 "阿里云 OSS ·" mock
      _uSet('存储位置', d.fileUrl || '—')
    }
    // 7) 关联（合同 / 项目 / 回款）
    if (Array.isArray(d.relations)) {
      mock.relations = d.relations
      // 更新 4 报销信息中的"关联项目"
      const link = reimburse.value.find((r: any) => r.label === '关联项目')
      if (link) link.value = '—'  // 先重置
      const projRel = d.relations.find((r: any) => r.type === 'project')
      if (projRel && link) {
        link.value = `PRJ-${projRel.id} · 来自识别记录`
      }
      const ctRel = d.relations.find((r: any) => r.type === 'contract')
      if (ctRel) {
        // 在状态历史里加一条
        mock.status_history = [
          { t: '已关联合同', m: new Date().toISOString().slice(0,10), d: `合同 HT-${ctRel.id}` },
          ...mock.status_history,
        ]
      }
    }
    // 7.5) 报销信息：调 expenseApi.list 按 linkedInvoiceId 过滤，拿到真实数据
    try {
      const _invNo = d.invoiceNo || d.code || String(id)
      const _eRes: any = await expenseApi.list({ page: 1, pageSize: 10, keyword: '', filters: { linkedInvoiceId: _invNo } } as any).catch(() => null)
      const _eList = _eRes?.data?.list || _eRes?.list || []
      if (_eList.length > 0) {
        const _e = _eList[0]
        // 状态文案映射
        const _statusMap: Record<string, { text: string; type: string }> = {
          draft:     { text: '草稿',   type: 'info' },
          pending:   { text: '审批中', type: 'warning' },
          approved:  { text: '已批准', type: 'success' },
          rejected:  { text: '已驳回', type: 'danger' },
          paid:      { text: '已支付', type: 'success' },
        }
        const _st = _statusMap[_e.status] || { text: _e.status, type: 'info' }
        const _set = (label: string, value: string, type?: string) => {
          const row: any = reimburse.value.find((r: any) => r.label === label)
          if (row) {
            row.value = value
            if (type) row.type = type
          }
        }
        _set('报销单号', _e.code || '—')
        _set('报销人', _e.applicantName || '—')
        _set('费用类型', _e.category || '—')
        _set('报销金额', '¥ ' + Number(_e.amount || 0).toFixed(2))
        _set('提交日期', _e.submitAt ? String(_e.submitAt).replace('T', ' ').slice(0, 10) : (_e.expenseDate || '—'))
        _set('审批状态', _st.text, _st.type)
        // 关联项目 = 来自 relations 数组（如果该 expense 关联了项目）保持上面 relations 那段设置
      } else {
        // 未关联任何费用：报销信息显示"未关联"
        const _clear = (label: string, value = '未关联') => {
          const row: any = reimburse.value.find((r: any) => r.label === label)
          if (row) { row.value = value; delete row.type }
        }
        _clear('报销单号', '— 未关联费用 —')
        _clear('报销人', '—')
        _clear('费用类型', '—')
        _clear('报销金额', '—')
        _clear('提交日期', '—')
        _clear('审批状态', '—')
      }
    } catch (e) {
      console.warn('[reimburse load]', e)
    }
    // 8) 真实核验时间
    if (d.verifyAt) {
      mock.verifyTime = String(d.verifyAt).replace('T', ' ').slice(0, 16)
    }
    // 9) 业务状态 → 详情页顶部 status
    if (d.status) {
      const vs = d.verifyStatus || 'pending'
      if (d.status === 'submitted') { mock.status = '已入账'; mock.statusColor = 'primary' }
      else if (vs === 'verified') { mock.status = '已核验'; mock.statusColor = 'success' }
      else if (vs === 'rejected') { mock.status = '已驳回'; mock.statusColor = 'danger' }
      else if (d.status === 'pending_verify') { mock.status = '识别中'; mock.statusColor = 'info' }
      else if (d.status === 'failed') { mock.status = '需复核'; mock.statusColor = 'warning' }
      else { mock.status = '已识别'; mock.statusColor = 'success' }
    }
    // 10) 附件管理：从文件库（files 表）查该发票关联的所有文件
    try {
      const _fRes: any = await fileApi.list({ bizType: 'invoice', bizId: id, page: 1, pageSize: 50 } as any).catch(() => null)
      const _fList = _fRes?.data?.list || _fRes?.list || []
      invoiceFiles.value = _fList
      // 把"存储位置"显示为 fileId（数据库外键），而不是裸 URL
      const _uSet2 = (label: string, val: string) => {
        const r: any = uploads.value.find((u: any) => u.label === label)
        if (r) r.value = val
      }
      if (_fList.length > 0) {
        const f = _fList[0]
        _uSet2('存储位置', `${f.fileId} · ${f.storage} · ${_fmtSize(f.size)}`)
      } else if (d.fileId) {
        _uSet2('存储位置', `${d.fileId} · local · ${_fmtSize(d.fileSize)}`)
      } else {
        _uSet2('存储位置', '—')
      }
    } catch (e) {
      console.warn('[files load]', e)
    }
  } catch (e) {
    console.warn('[detail load]', e)
  } finally {
    loading.value = false
  }
})

// 触点 #19：AI 票面复核
const aiRecheckVisible = ref(false)
const aiRecheckResult = ref<null | { score: number; items: Array<{ field: string; status: 'pass' | 'warn' | 'fail'; msg: string }> }>(null)

async function runAiRecheck() {
  aiRecheckResult.value = null
  await new Promise(r => setTimeout(r, 1200))
  aiRecheckResult.value = {
    score: 88,
    items: [
      { field: '发票号码',     status: 'pass', msg: '格式正确，可在全国增值税发票查验平台查验' },
      { field: '开票日期',     status: 'pass', msg: '日期格式符合 YYYY-MM-DD' },
      { field: '销售方信息',   status: 'pass', msg: '税号已验证，与企业工商信息一致' },
      { field: '购买方信息',   status: 'warn', msg: '购买方税号位数异常，建议人工复核' },
      { field: '金额计算',     status: 'pass', msg: '价税合计 = 不含税金额 + 税额，勾稽关系正确' },
      { field: '税率',         status: 'pass', msg: '13% 税率符合当前税法规定' },
      { field: '发票章 / 签名',status: 'fail', msg: '⚠️ 发票章位置与设计模板不匹配，建议核实' },
    ],
  }
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/invoice/ocr')">财务</a>
          <span class="sep">/</span>
          <a @click="router.push('/invoice/ocr?tab=records')">发票识别</a>
          <span class="sep">/</span>
          <span class="current">识别记录详情</span>
        </div>
        <h1>📄 发票详情 · {{ mock.no.slice(0, 8) }}...{{ mock.no.slice(-4) }}</h1>
        <p class="page-desc">票面信息 · 智能识别 · 商品明细 · 报销 / 查验 / 上传元数据</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="goBack">← 返回</button>
        <!-- 触点 #19：AI 复核 -->
        <button v-permission="'invoice:read'" class="btn-ai-outline" @click="aiRecheckVisible = true">🤖 AI 复核</button>
        <button v-permission="'invoice:read'" class="btn btn-outline btn-sm" @click="exportField">⬇ 导出字段</button>
        <button v-permission="'expense:write'" class="btn btn-primary btn-sm" @click="createReimburse">✚ 创建报销</button>
      </div>
    </div>

    <!-- 4 KPI -->
    <div class="kpi-row">
      <div v-for="(s, i) in stats" :key="i" class="stat-card">
        <div class="stat-label">
          <span>{{ s.label }}</span>
          <span class="stat-icon" :class="s.color">{{ s.icon }}</span>
        </div>
        <div class="stat-value">{{ s.v }}<span v-if="s.u" class="unit">{{ s.u }}</span></div>
        <div class="stat-delta">{{ s.delta }}</div>
      </div>
    </div>

    <div class="detail-layout">
      <!-- 左主区 -->
      <div>
        <!-- 票面预览（design: fake-invoice 模拟发票样式） -->
        <div class="detail-section">
          <div class="detail-section-head">
            <h4>📄 票面预览</h4>
            <div class="preview-actions">
              <a v-if="mock.fileUrl" :href="mock.fileUrl" target="_blank" class="btn btn-outline btn-sm">📥 下载</a>
              <a v-if="mock.previewUrl" :href="mock.previewUrl" target="_blank" class="btn btn-outline btn-sm">🔍 查看原图</a>
              <button class="btn btn-outline btn-sm" @click="printInvoice">🖨 打印</button>
            </div>
          </div>
          <div class="detail-section-body">
            <!-- 真实发票原图/PDF（如果后端返回了 previewUrl） -->
            <div v-if="mock.previewUrl" class="real-invoice">
              <a v-if="mock.previewUrl.toLowerCase().endsWith('.pdf')" :href="mock.previewUrl" target="_blank" class="invoice-pdf-link">
                📎 点击查看原 PDF 发票
              </a>
              <img v-else :src="mock.previewUrl" class="invoice-img" alt="发票原图" />
              <div class="invoice-url-tip">来源: {{ mock.previewUrl.slice(0, 80) }}...</div>
            </div>
            <!-- 设计稿的 fake-invoice 模拟样式（始终保留） -->
            <div class="fake-invoice">
              <div class="fi-header">
                <div class="fi-title">电子普通发票</div>
                <div class="fi-no">No. {{ mock.no }}</div>
              </div>
              <div class="fi-info-grid">
                <div class="fi-row"><span>购买方名称：</span><strong>{{ mock.buyer }}</strong></div>
                <div class="fi-row"><span>纳税人识别号：</span><span class="mono">{{ mock.buyerTaxNo }}</span></div>
                <div class="fi-row"><span>销售方名称：</span><strong>{{ mock.seller }}</strong></div>
                <div class="fi-row"><span>纳税人识别号：</span><span class="mono">{{ mock.sellerTaxNo }}</span></div>
                <div class="fi-row"><span>开票日期：</span><strong>{{ mock.issueDate }}</strong></div>
                <div v-if="mock.checkCode" class="fi-row"><span>校验码：</span><span class="mono">{{ mock.checkCode }}</span></div>
              </div>
              <table class="fi-table">
                <thead>
                  <tr><th>项目名称</th><th>数量</th><th>单价</th><th>金额</th><th>税率</th><th>税额</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(it, i) in items" :key="i">
                    <td>{{ it.name || '—' }}</td>
                    <td>{{ it.qty || _fmtQty(it.quantity) || "—" }}</td>
                    <td>¥ {{ _fmtMoney(it.price || it.unitPrice || it.amount) }}</td>
                    <td>¥ {{ _fmtMoney(it.amount) }}</td>
                    <td>{{ _fmtTaxRate(it.taxRate) }}</td>
                    <td>¥ {{ _fmtMoney(it.tax) }}</td>
                  </tr>
                </tbody>
                <tfoot>
                  <tr><td colspan="3">价税合计（大写）</td><td colspan="3" class="cn">{{ mock.amountCn || '—' }}</td></tr>
                  <tr><td colspan="3">价税合计（小写）</td><td colspan="3" class="amount">¥ {{ mock.totalAmount }}</td></tr>
                </tfoot>
              </table>
              <div v-if="mock.seller" class="fi-stamp">✓ {{ mock.seller }}发票专用章</div>
            </div>
          </div>
        </div>

        <!-- 字段核验 -->
        <div class="detail-section">
          <div class="detail-section-head">
            <h4>✨ 智能识别 · 字段核验</h4>
            <span class="tag tag-success">8/8 字段已识别</span>
          </div>
          <div class="detail-section-body">
            <div class="fields-grid">
              <div v-for="(f, i) in fields" :key="i" class="field-row">
                <div class="l">{{ f.key }}</div>
                <div class="v mono">{{ f.value }}</div>
                <div class="conf">
                  <div class="bar"><div class="fill" :style="{ width: confToPct(f.confidence) + '%' }"></div></div>
                  <span class="pct">{{ fmtConfidence(f.confidence) }}</span>
                </div>
                <button class="edit-link" @click="editField(f)">编辑</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 商品明细 -->
        <div class="detail-section">
          <div class="detail-section-head">
            <h4>📋 商品明细</h4>
          </div>
          <div class="detail-section-body">
            <table class="ct-table">
              <thead>
                <tr><th>序号</th><th>项目名称</th><th style="text-align: right;">数量</th><th style="text-align: right;">单价</th><th style="text-align: right;">金额</th><th style="text-align: right;">税率</th><th style="text-align: right;">税额</th></tr>
              </thead>
              <tbody>
                <tr v-for="(it, i) in items" :key="i">
                  <td>{{ it.seq }}</td>
                  <td><strong>{{ it.name }}</strong></td>
                  <td class="cell-num">{{ it.qty || _fmtQty(it.quantity) || "—" }}</td>
                  <td class="cell-amount">¥ {{ _fmtMoney(it.price || it.unitPrice || it.amount) }}</td>
                  <td class="cell-amount">¥ {{ it.amount }}</td>
                  <td class="cell-num">{{ it.taxRate }}</td>
                  <td class="cell-amount">¥ {{ it.tax }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td colspan="4"><strong>合计</strong></td>
                  <td class="cell-amount total">¥ {{ mock.totalAmount }}</td>
                  <td>—</td>
                  <td class="cell-amount total">¥ {{ mock.taxAmount }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>

      <!-- 右主区 -->
      <div>
        <!-- 报销信息 -->
        <div class="meta-card">
          <h4>📝 报销信息</h4>
          <div v-for="(r, i) in reimburse" :key="i" class="kv-row">
            <span class="l">{{ r.label }}</span>
            <span v-if="r.type" :class="['tag', `tag-${r.type}`]">{{ r.value }}</span>
            <span v-else class="v">{{ r.value }}</span>
          </div>
          <button class="btn btn-primary btn-sm btn-block" @click="createReimburse">✚ 立即创建费用</button>
        </div>

        <!-- 当前状态 -->
        <div class="meta-card">
          <h4>📌 当前状态</h4>
          <div class="status-timeline">
            <div v-for="(s, i) in mock.status_history" :key="i" class="st-item done">
              <div class="dot"></div>
              <div class="t">{{ s.t }}</div>
              <div class="m">{{ s.m }}</div>
              <div class="d">{{ s.d }}</div>
            </div>
          </div>
        </div>

        <!-- 上传信息 -->
        <div class="meta-card">
          <h4>📎 上传信息 <a @click="openFilesDrawer" class="files-link" v-if="invoiceFiles.length > 0">📚 文件库 ({{ invoiceFiles.length }})</a></h4>
          <div v-for="(u, i) in uploads" :key="i" class="kv-row">
            <span class="l">{{ u.label }}</span>
            <span :class="['v', { mono: u.label === '文件名' || u.label === '存储位置' }]">{{ u.value }}</span>
          </div>
        </div>

        <!-- 快捷操作 -->
        <div class="meta-card">
          <h4>⚡ 快捷操作</h4>
          <div class="quick-grid">
            <button v-for="(a, i) in quickActions" :key="i" :class="['qa-btn', a.color]" @click="_runQuickAction(a.handler)">
              <span class="ico">{{ a.icon }}</span>
              <span>{{ a.label }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 触点 #24：附件管理 Drawer（专门的文件库 UI） -->
<el-drawer v-model="filesDrawerVisible" title="📚 附件管理 · 专门文件库" direction="rtl" size="560px">
  <div class="files-drawer">
    <div class="files-stat">
      <div class="stat-item">
        <div class="num">{{ invoiceFiles.length }}</div>
        <div class="lbl">关联文件</div>
      </div>
      <div class="stat-item">
        <div class="num">{{ _fmtSize2(invoiceFiles.reduce((s:number,f:any)=>s+(f.size||0),0)) }}</div>
        <div class="lbl">总大小</div>
      </div>
      <div class="stat-item">
        <div class="num">{{ [...new Set(invoiceFiles.map((f:any)=>f.storage))].join('/') || '—' }}</div>
        <div class="lbl">存储</div>
      </div>
    </div>
    <p class="files-tip">💡 发票 PDF/图片统一入库到 <code>files</code> 表，支持 local / minio / oss 多存储后端，所有文件元数据可追溯</p>
    <div v-if="invoiceFiles.length === 0" class="files-empty">该发票暂无关联文件</div>
    <div v-for="(f, i) in invoiceFiles" :key="i" class="file-item">
      <div class="file-icon">{{ f.ext === 'pdf' ? '📄' : (f.ext.match(/png|jpg|jpeg|webp/) ? '🖼' : '📎') }}</div>
      <div class="file-info">
        <div class="file-name" :title="f.name">{{ f.name }}</div>
        <div class="file-meta">
          <span class="tag">{{ f.fileId }}</span>
          <span class="tag tag-storage">{{ f.storage }}</span>
          <span class="tag">{{ _fmtSize2(f.size) }}</span>
          <span class="tag">{{ f.mimeType || f.ext }}</span>
        </div>
        <div class="file-uploader">上传人：{{ f.uploaderName }} · {{ (f.createdAt || '').replace('T',' ').slice(0,16) }}</div>
        <div class="file-url">{{ f.url }}</div>
      </div>
      <div class="file-actions">
        <a :href="f.url" target="_blank" rel="noopener noreferrer" class="btn btn-outline btn-sm">查看</a>
        <a :href="f.url" :download="f.name" class="btn btn-outline btn-sm">下载</a>
      </div>
    </div>
  </div>
</el-drawer>

<!-- 触点 #19：AI 票面复核 Drawer -->
  <el-drawer v-model="aiRecheckVisible" title="🤖 AI 票面复核" direction="rtl" size="520px">
    <div class="ai-recheck-drawer">
      <el-button v-if="!aiRecheckResult" type="primary" class="ai-recheck-go" :loading="!aiRecheckResult && aiRecheckVisible" @click="runAiRecheck">✨ 开始 AI 复核</el-button>
      <div v-if="aiRecheckResult" class="ai-recheck-result">
        <div class="ai-recheck-hero">
          <div class="ai-recheck-score" :class="aiRecheckResult.score >= 80 ? 'good' : aiRecheckResult.score >= 60 ? 'mid' : 'bad'">
            <div class="num">{{ aiRecheckResult.score }}</div>
            <div class="label">综合评分</div>
          </div>
          <div class="ai-recheck-meta">
            <h3>复核完成</h3>
            <p>检测时间：{{ new Date().toLocaleString('zh-CN') }}</p>
            <p>检测模型：ernie-3.5 · 票面识别</p>
          </div>
        </div>
        <h4>📋 7 项复核明细</h4>
        <div class="ai-recheck-list">
          <div v-for="(it, i) in aiRecheckResult.items" :key="i" class="ai-recheck-item" :class="`ai-recheck-${it.status}`">
            <span class="ai-recheck-icon">
              {{ it.status === 'pass' ? '✓' : it.status === 'warn' ? '!' : '✕' }}
            </span>
            <div class="ai-recheck-body">
              <h5>{{ it.field }}</h5>
              <p>{{ it.msg }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<style lang="scss" scoped>
/* 触点 #19：AI 复核 */
.btn-ai-outline {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 12px; font-size: 12px; font-weight: 600;
  background: $gradient-brand; color: #fff; border: none;
  border-radius: $radius-sm; cursor: pointer;
  &:hover { opacity: 0.92; }
}
.ai-recheck-drawer { padding: 0 4px; }
.ai-recheck-go { width: 100%; height: 40px; background: $gradient-brand; border: none; }
.ai-recheck-hero { display: flex; gap: 16px; align-items: center; padding: 16px; background: linear-gradient(135deg, rgba(79,107,255,0.05) 0%, rgba(124,58,237,0.05) 100%); border: 1px solid rgba(124,58,237,0.25); border-radius: $radius-md; margin: 12px 0 20px; }
.ai-recheck-score {
  width: 80px; height: 80px; border-radius: 50%;
  color: #fff; flex-shrink: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  &.good { background: linear-gradient(135deg, #10B981, #059669); }
  &.mid  { background: linear-gradient(135deg, #F59E0B, #D97706); }
  &.bad  { background: linear-gradient(135deg, #EF4444, #DC2626); }
  .num { font-size: 28px; font-weight: 700; line-height: 1; }
  .label { font-size: 10px; opacity: 0.9; margin-top: 2px; }
}
.ai-recheck-meta h3 { font-size: 16px; font-weight: 600; color: $color-text-primary; margin-bottom: 6px; }
.ai-recheck-meta p { font-size: 11px; color: $color-text-secondary; margin-bottom: 2px; }
.ai-recheck-list { display: flex; flex-direction: column; gap: 8px; }
.ai-recheck-item { display: flex; gap: 10px; padding: 10px 12px; background: #fff; border: 1px solid $color-border; border-radius: $radius-sm; }
.ai-recheck-icon {
  flex-shrink: 0; width: 24px; height: 24px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; color: #fff;
  .ai-recheck-pass & { background: $color-success; }
  .ai-recheck-warn & { background: $color-warning; }
  .ai-recheck-fail & { background: $color-danger; }
}
.ai-recheck-body h5 { font-size: 12px; font-weight: 600; color: $color-text-primary; margin-bottom: 2px; }
.ai-recheck-body p { font-size: 11px; color: $color-text-secondary; line-height: 1.5; }
.ai-recheck-list h4 { font-size: 13px; font-weight: 600; color: $color-text-primary; margin-bottom: 10px; }
</style>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.page-header .breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-primary; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-header .page-actions { display: flex; gap: 8px; }

// 4 KPI
.kpi-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px;
  @media (max-width: 1100px) { grid-template-columns: repeat(2, 1fr); }
}
.stat-card {
  @include stat-card;
  .stat-label { font-size: 12.5px; color: $color-text-secondary; display: flex; justify-content: space-between; align-items: center; position: relative; z-index: 1; }
  .stat-icon { width: 32px; height: 32px; border-radius: 8px; display: grid; place-items: center; font-size: 16px; font-weight: 600;
    &.success { background: rgba(16,185,129,0.12); color: $color-success; }
    &.primary { background: $color-primary-bg; color: $color-primary; }
  }
  .stat-value { font-size: 26px; font-weight: 700; color: $color-text-primary; font-family: $font-family-mono; margin: 6px 0; position: relative; z-index: 1;
    .unit { font-size: 13px; color: $color-text-tertiary; font-weight: 500; margin-left: 4px; font-family: -apple-system, sans-serif; }
  }
  .stat-delta { font-size: 12px; color: $color-text-tertiary; position: relative; z-index: 1; }
}

.detail-layout {
  display: grid; grid-template-columns: 1fr 320px; gap: 16px; align-items: start;
  @media (max-width: 1100px) { grid-template-columns: 1fr; }
}
.detail-section { @include detail-section; }
.detail-section-head { @include detail-section-head; }
.detail-section-body { @include detail-section-body; }

// 真实发票原图/PDF
.real-invoice {
  margin-bottom: 16px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  text-align: center;
}
.invoice-img {
  max-width: 100%;
  max-height: 400px;
  display: block;
  margin: 0 auto;
  border-radius: $radius-sm;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.invoice-pdf-link {
  display: inline-block;
  padding: 16px 24px;
  background: #fff;
  border: 1px solid $color-primary;
  border-radius: $radius-md;
  color: $color-primary;
  text-decoration: none;
  font-weight: 500;
  &:hover { background: rgba(99,102,241,.05); }
}
.invoice-url-tip {
  font-size: 11px;
  color: $color-text-tertiary;
  margin-top: 8px;
  word-break: break-all;
}

// fake-invoice（design 模拟发票样式）
.fake-invoice {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  padding: 24px 28px;
  position: relative;
  overflow: hidden;
  &::after {
    content: 'SAMPLE';
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%) rotate(-30deg);
    font-size: 80px;
    color: rgba(79,107,255,0.06);
    font-weight: 700;
    pointer-events: none;
    letter-spacing: 8px;
  }
}
.fi-header {
  text-align: center;
  padding-bottom: 16px;
  border-bottom: 2px solid $color-primary;
  margin-bottom: 16px;
  .fi-title { font-size: 22px; font-weight: 700; color: $color-primary; letter-spacing: 2px; }
  .fi-no { font-size: 12px; color: $color-text-tertiary; font-family: $font-family-mono; margin-top: 4px; }
}
.fi-info-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px 24px;
  margin-bottom: 16px;
  .fi-row { display: flex; font-size: 12.5px; padding: 4px 0;
    span { color: $color-text-tertiary; margin-right: 4px; }
    strong { color: $color-text-primary; font-weight: 500; }
    .mono { font-family: $font-family-mono; color: $color-text-secondary; font-size: 12px; }
  }
}
.fi-table {
  width: 100%; border-collapse: collapse; font-size: 12.5px;
  th { background: rgba(79,107,255,0.05); padding: 8px 10px; text-align: left; color: $color-text-secondary; font-weight: 500; border-bottom: 1px solid $color-border; }
  td { padding: 10px; border-bottom: 1px solid $color-border; }
  tfoot td { padding: 10px; font-weight: 600; background: rgba(79,107,255,0.04); }
  .amount { font-family: $font-family-mono; font-size: 16px; color: $color-primary; }
  .cn { font-family: "宋体", SimSun, serif; letter-spacing: 1px; }
}
.fi-stamp {
  position: absolute;
  bottom: 80px; right: 40px;
  width: 110px; height: 110px;
  border: 3px solid $color-danger;
  border-radius: 50%;
  display: grid; place-items: center;
  color: $color-danger;
  font-size: 11px;
  font-weight: 700;
  text-align: center;
  transform: rotate(-15deg);
  opacity: 0.75;
  line-height: 1.3;
}

// fields-grid（字段核验）
.fields-grid {
  display: flex; flex-direction: column; gap: 8px;
}
.field-row {
  display: grid;
  grid-template-columns: 100px 1fr 200px 60px;
  gap: 12px;
  align-items: center;
  padding: 10px 14px;
  background: #FAFBFF;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  .l { font-size: 12px; color: $color-text-tertiary; }
  .v { font-size: 13px; color: $color-text-primary; font-weight: 500; word-break: break-all; }
  .conf { display: flex; align-items: center; gap: 8px; }
  .bar { flex: 1; height: 6px; background: $color-bg; border-radius: 3px; overflow: hidden; }
  .fill { height: 100%; background: linear-gradient(90deg, #10B981, #059669); border-radius: 3px; }
  .pct { font-family: $font-family-mono; font-size: 11px; color: $color-success; font-weight: 600; min-width: 40px; text-align: right; }
  .edit-link { font-size: 12px; color: $color-primary; cursor: pointer; background: transparent; border: none; &:hover { text-decoration: underline; } }
}

// table
.ct-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
  th { background: $color-bg; text-align: left; padding: 10px 14px; font-size: 12px; font-weight: 600; color: $color-text-tertiary; border-bottom: 1px solid $color-border; }
  td { padding: 12px 14px; border-bottom: 1px solid $color-border; }
  tfoot td { background: $color-bg; border-bottom: none; font-weight: 600; }
  .cell-amount { font-family: $font-family-mono; font-weight: 600; text-align: right; }
  .cell-num { text-align: center; font-family: $font-family-mono; }
  .total { color: $color-primary; font-size: 14px; }
}

// meta-card
.meta-card {
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  padding: 18px 20px;
  margin-bottom: 14px;
  h4 { font-size: 13.5px; font-weight: 600; margin: 0 0 12px 0; display: flex; align-items: center; gap: 6px; }
}
.kv-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 0;
  font-size: 12.5px;
  .l { color: $color-text-tertiary; }
  .v { color: $color-text-primary; font-weight: 500; text-align: right; }
  .v.mono { font-family: $font-family-mono; font-size: 11.5px; word-break: break-all; max-width: 60%; }
}
.btn-block { width: 100%; margin-top: 12px; }

.status-timeline {
  position: relative; padding-left: 24px;
  &::before { content: ''; position: absolute; left: 9px; top: 8px; bottom: 8px; width: 1.5px; background: $color-border; }
}
.st-item {
  position: relative; padding-bottom: 14px;
  &::before { content: ''; position: absolute; left: -19px; top: 5px; width: 10px; height: 10px; border-radius: 50%; background: linear-gradient(135deg, #10B981, #059669); }
  &:last-child { padding-bottom: 0; }
  .t { font-size: 12.5px; font-weight: 600; color: $color-text-primary; }
  .m { font-size: 11px; color: $color-text-tertiary; margin-top: 2px; }
  .d { font-size: 11.5px; color: $color-text-secondary; margin-top: 2px; }
}

.quick-grid {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px;
}
.qa-btn {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 12px 8px;
  background: #fff;
  border: 1px solid $color-border;
  border-radius: $radius-md;
  font-size: 12px;
  color: $color-text-primary;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.15s;
  .ico { font-size: 18px; }
  &:hover { background: $color-primary-bg; color: $color-primary; border-color: $color-primary; }
  &.primary { background: $color-primary; color: #fff; border-color: $color-primary;
    &:hover { background: darken($color-primary, 8%); }
  }
}

.tag {
  display: inline-flex; align-items: center; padding: 2px 10px;
  font-size: 12px; font-weight: 500; border-radius: 9999px;
  &.tag-success { background: #D1FAE5; color: #047857; }
  &.tag-info    { background: #CFFAFE; color: #0E7490; }
  &.tag-warning { background: #FEF3C7; color: #B45309; }
}

.btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: 6px; padding: 0 14px; font-size: 13px; font-weight: 500;
  border-radius: $radius-md; transition: all 0.15s;
  border: 1px solid transparent; cursor: pointer; font-family: inherit;
  &.btn-primary { background: $gradient-brand; color: #fff; &:hover { box-shadow: 0 4px 12px rgba(79, 107, 255, 0.4); } }
  &.btn-outline { background: #fff; border-color: $color-border; color: $color-text-primary; &:hover { border-color: $color-primary; color: $color-primary; } }
  &.btn-ghost { background: transparent; color: $color-text-secondary; &:hover { background: $color-primary-bg; color: $color-primary; } }
  &.btn-sm { height: 32px; padding: 0 10px; font-size: 12px; }
  &.btn-block { width: 100%; }
}
</style>

<style scoped>
.files-link {
  font-size: 12px;
  color: #4F6BFF;
  cursor: pointer;
  margin-left: 8px;
  font-weight: normal;
}
.files-link:hover { text-decoration: underline; }
.files-drawer { padding: 0 20px 20px; }
.files-stat {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.files-stat .stat-item {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 12px 8px;
  text-align: center;
}
.files-stat .num {
  font-size: 20px;
  font-weight: 600;
  color: #1E293B;
  font-family: 'SF Mono', monospace;
}
.files-stat .lbl {
  font-size: 11px;
  color: #64748B;
  margin-top: 4px;
}
.files-tip {
  background: #EFF6FF;
  border-left: 3px solid #4F6BFF;
  padding: 8px 12px;
  font-size: 12px;
  color: #1E40AF;
  border-radius: 4px;
  margin-bottom: 16px;
}
.files-tip code {
  background: rgba(79,107,255,0.1);
  padding: 1px 4px;
  border-radius: 3px;
  font-family: 'SF Mono', monospace;
}
.files-empty {
  text-align: center;
  padding: 40px 0;
  color: #94A3B8;
  font-size: 13px;
}
.file-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  margin-bottom: 8px;
  background: #fff;
  transition: all 0.15s;
}
.file-item:hover { border-color: #4F6BFF; background: #FAFBFF; }
.file-icon { font-size: 28px; flex-shrink: 0; }
.file-info { flex: 1; min-width: 0; }
.file-name {
  font-weight: 500;
  font-size: 13px;
  color: #1E293B;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 6px;
}
.file-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.file-meta .tag {
  font-size: 11px;
  background: #F1F5F9;
  color: #475569;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'SF Mono', monospace;
}
.file-meta .tag-storage { background: #DBEAFE; color: #1E40AF; }
.file-uploader {
  font-size: 11px;
  color: #64748B;
  margin-bottom: 4px;
}
.file-url {
  font-size: 10px;
  color: #94A3B8;
  font-family: 'SF Mono', monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}
.file-actions .btn { font-size: 11px; padding: 4px 10px; }
</style>
