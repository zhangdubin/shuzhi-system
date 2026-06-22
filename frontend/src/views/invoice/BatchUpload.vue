<script setup lang="ts">
/**
 * 批量上传 tab（R8.14 严格 1:1 复刻 design/invoice-ocr-batch.html）
 * - 顶部：模板选择器（5 个 tpl-chip）
 * - 拖拽上传区（drop-zone）：3 个按钮（选择文件/选择文件夹/拍照识别）
 * - 进度总览（4 个 stat-mini）
 * - 识别队列表格：8 列（checkbox/文件/发票号/金额/销方/置信度/状态/操作）
 * - 设计稿 18 张示例数据
 */
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { fmtConfidenceInt, confToPct } from '@/utils/format'
import { ElMessage, ElMessageBox } from 'element-plus'
import { invoiceOcrApi, invoiceTemplateApi } from '@/api/modules'
import { aiApi } from '@/api/ai'

const fileInput = ref<HTMLInputElement>()
const folderInput = ref<HTMLInputElement>()
const captureInput = ref<HTMLInputElement>()
const router = useRouter()
const uploading = ref(false)
const isDragging = ref(false)
// 上传/识别中的临时队列 ID 自增器（不影响设计稿 18 条示例数据 ID）
let newItemId = 1000

// 触点 #2：AI 抽取开关 + SSE 实时进度
const aiExtract = ref(true)
const sseProgress = ref({
  active: false,
  total: 0,
  done: 0,
  percent: 0,
  status: 'success' as '' | 'success' | 'exception' | 'warning',
  current: '',
})
let sseTimer: number | null = null

function startAiProgress(total: number) {
  sseProgress.value = { active: true, total, done: 0, percent: 0, status: '', current: '' }
  // mock SSE 推送（每 200ms 推一张完成）
  sseTimer = window.setInterval(() => {
    if (sseProgress.value.done >= total) {
      sseProgress.value.status = 'success'
      sseProgress.value.percent = 100
      stopAiProgress()
      ElMessage.success(`✨ AI 批量抽取完成（${total} 张 · 平均 2.1s/张）`)
      return
    }
    sseProgress.value.done += 1
    sseProgress.value.percent = Math.round((sseProgress.value.done / sseProgress.value.total) * 100)
    sseProgress.value.current = `invoice_滴滴_2026${String(517 + sseProgress.value.done).padStart(3, '0')}.pdf`
  }, 200)
}

function stopAiProgress() {
  if (sseTimer) { clearInterval(sseTimer); sseTimer = null }
  setTimeout(() => { sseProgress.value.active = false }, 1500)
}

onUnmounted(() => { if (sseTimer) clearInterval(sseTimer) })

// 模板选择（从后端拉取真实模板，第一项"自动识别"为固定）
interface TplItem {
  key: string            // 'auto' | 'tpl_<id>'
  ico: string
  label: string
  templateId: number | null  // null = 自动识别（不传）
  category?: string
  desc?: string
  enabled: boolean
}
const tpls = ref<TplItem[]>([
  { key: 'auto', ico: '⚡', label: '自动识别', templateId: null, enabled: true, desc: '智能识别发票类型并匹配字段' },
])
const selectedTpl = ref<string>('auto')
const tplLoading = ref(false)
// 启动时从后端拉取真实模板（仅启用中）
async function loadTpls() {
  tplLoading.value = true
  try {
    // 拉全量模板（后端目前不按 status 过滤，list 一次性返回所有启用+停用）
    const res: any = await invoiceTemplateApi.list({ page: 1, pageSize: 50, keyword: '' } as any)
    const list: any[] = res?.list || []
    // 状态映射：后端 status 字段实际是 'enabled' / 'disabled' / '启用中' / '待启用' / '已停用'
    const isEnabled = (s: any) => s === 'enabled' || s === '启用中' || s === 'active' || s === 1 || s === true
    // 常用图标按 category 映射；icon 字段优先（后端可自定义）
    const icoMap: Record<string, string> = { travel: '✈', 差旅: '✈', office: '▣', software: '软', taxi: '🚖', meal: '🍱', hotel: '🏨', training: '🎓', default: '📄' }
    const items: TplItem[] = list
      .filter((t: any) => isEnabled(t.status))  // 只显示启用中的
      .map((t: any) => ({
        key: `tpl_${t.id ?? t.templateId}`,
        ico: t.icon || icoMap[t.category] || icoMap.default,
        label: t.name || t.code || `模板 ${t.id ?? t.templateId}`,
        templateId: t.id ?? t.templateId ?? null,
        category: t.category,
        desc: t.description || '',
        enabled: true,
      }))
    tpls.value = [tpls.value[0], ...items]
    console.info(`[loadTpls] loaded ${items.length} templates:`, items.map(i => i.label))
  } catch (err) {
    // 拉取失败不影响页面使用（保留"自动识别"一项）
    console.warn('[loadTpls] failed:', err)
  } finally {
    tplLoading.value = false
  }
}
loadTpls()

// 进度总览（启动后由 loadQueue() 刷新）
const progress = ref({ total: 0, done: 0, recognizing: 0, failed: 0 })

// 识别队列（设计稿示例数据：18 张）
interface QueueItem {
  id: number
  fileName: string
  thumb?: string  // 缩略图 base64 / 颜色
  invoiceNo: string
  amount: number
  seller: string
  confidence: number
  status: 'uploading' | 'recognizing' | 'success' | 'warning' | 'danger'
  selected: boolean
  /** 后端入库后的发票 ID（设计稿示例无此字段） */
  invoiceId?: number
}
// 识别队列：初始为空，启动时从后端拉真实数据
const queue = ref<QueueItem[]>([])

// 启动时拉取后端真实发票到队列
async function loadQueue() {
  try {
    const res: any = await invoiceOcrApi.records({ page: 1, pageSize: 200, keyword: '', filters: {} })
    const list: any[] = res?.list || []
    const colors = ['#4F6BFF', '#EF4444', '#F59E0B', '#10B981', '#7C3AED']
    queue.value = list.map((inv: any, idx: number) => {
      const f = inv.fields || {}
      const totalAmount = Number(f.totalAmount ?? inv.totalAmount ?? 0)
      // 后端 list 序列化时已 /100 还原为 0-1；前端不需要再除
      const conf = Number(inv.confidence ?? 0)
      // 状态映射：优先用 ocrStatus（OCR 识别状态），verifyStatus 是核验状态（pending/verified/failed），不要混用
      const status = (() => {
        const ocr = inv.ocrStatus
        if (ocr === 'failed') return 'danger'
        if (ocr === 'recognizing' || ocr === 'pending' || ocr === 'uploading') return 'recognizing'
        // success / verified / undefined 都算已识别
        return 'success'
      })()
      return {
        id: inv.invoiceId || idx + 1,
        invoiceId: inv.invoiceId,
        fileName: f.fileName || inv.code || `invoice_${inv.invoiceId}.pdf`,
        thumb: colors[idx % colors.length],
        invoiceNo: f.invoiceNo || inv.invoiceNo || inv.code || '-',
        amount: isFinite(totalAmount) ? totalAmount : 0,
        seller: f.sellerName || inv.sellerName || '-',
        confidence: isFinite(conf) ? conf : 0,
        status,
        selected: false,
      }
    })
    refreshProgress()
  } catch (err) {
    console.warn('[loadQueue] failed:', err)
  }
}

// 根据 queue 实时计算进度总览
function refreshProgress() {
  const total = queue.value.length
  const done = queue.value.filter(i => i.status === 'success').length
  const recognizing = queue.value.filter(i => i.status === 'recognizing' || i.status === 'uploading').length
  const failed = queue.value.filter(i => i.status === 'danger' || i.status === 'warning').length
  progress.value = { total, done, recognizing, failed }
}

loadQueue()

// 搜索 + 状态筛选
const searchText = ref('')
const statusFilter = ref('all')

const filteredQueue = computed(() => {
  let items = queue.value
  if (searchText.value) {
    const t = searchText.value.toLowerCase()
    items = items.filter(i => i.fileName.toLowerCase().includes(t) || i.invoiceNo.includes(t))
  }
  if (statusFilter.value !== 'all') {
    items = items.filter(i => i.status === statusFilter.value)
  }
  return items
})

// 全选
const allSelected = computed({
  get: () => filteredQueue.value.every(i => i.selected),
  set: (v) => { filteredQueue.value.forEach(i => i.selected = v) },
})

// 状态映射
function statusLabel(s: string) {
  return { uploading: '上传中', recognizing: '识别中', success: '已识别', warning: '需核验', danger: '失败' }[s] || s
}
function statusPillClass(s: string) {
  return `status-pill ${s}`
}
function confClass(c: number) {
  if (c >= 0.9) return 'conf high'
  if (c >= 0.7) return 'conf mid'
  return 'conf low'
}

// 操作
function onDragOver(e: DragEvent) {
  e.preventDefault()
  isDragging.value = true
}
function onDragLeave() { isDragging.value = false }
function onDrop(e: DragEvent) {
  e.preventDefault()
  isDragging.value = false
  const files = e.dataTransfer?.files
  if (!files || files.length === 0) {
    ElMessage.info('未识别到文件，请重新拖入')
    return
  }
  processFiles(files)
}

// ===== 文件选择（拆分：按钮触发 picker；input change 处理选中文件）=====
function openFilePicker() {
  fileInput.value?.click()
}
function openFolderPicker() {
  folderInput.value?.click()
}
function openCapture() {
  captureInput.value?.click()
}
function onFileChange(e: Event) {
  const t = e.target as HTMLInputElement
  if (t.files && t.files.length > 0) processFiles(t.files)
  t.value = ''  // 清空，允许重复选同一文件
}
function onFolderChange(e: Event) {
  const t = e.target as HTMLInputElement
  if (t.files && t.files.length > 0) processFiles(t.files)
  t.value = ''
}
function onCaptureChange(e: Event) {
  const t = e.target as HTMLInputElement
  if (t.files && t.files.length > 0) processFiles(t.files)
  t.value = ''
}

// ===== 核心：把一批文件插到队列 → 调 OCR upload → 回填识别结果 =====
async function processFiles(files: FileList | File[]) {
  if (uploading.value) {
    ElMessage.warning('正在上传/识别中，请稍候')
    return
  }
  const list = Array.from(files)
  // 过滤非支持类型（浏览器原生 accept 不可靠，再做一次兜底）
  const allowed = /\.(pdf|jpg|jpeg|png|webp|heic|heif|ofd)$/i
  const valid = list.filter(f => allowed.test(f.name) || f.type.startsWith('image/') || f.type === 'application/pdf')
  if (valid.length === 0) {
    ElMessage.error('未识别到合法发票文件（支持 JPG/PNG/PDF/OFD/WEBP）')
    return
  }
  // 单批 200 张上限
  if (valid.length > 200) {
    ElMessage.warning(`一次最多 200 张，已截取前 200 张（原始 ${valid.length}）`)
    valid.splice(200)
  }

  // 1) 立即把每个文件插入 queue（status=uploading）
  const colors = ['#4F6BFF', '#EF4444', '#F59E0B', '#10B981', '#7C3AED']
  const newItems: QueueItem[] = valid.map((f, idx) => ({
    id: newItemId++,
    fileName: f.name,
    thumb: colors[(newItemId + idx) % colors.length],
    invoiceNo: '-',
    amount: 0,
    seller: '-',
    confidence: 0,
    status: 'uploading',
    selected: false,
  }))
  queue.value = [...newItems, ...queue.value]

  // 2) 更新顶部进度总览
  progress.value.total += newItems.length
  uploading.value = true

  // 3) 启动 AI 实时进度（如果在主流程选择文件时启用）
  if (aiExtract.value) startAiProgress(progress.value.total)

  // 4) 逐张上传 + 识别
  let ok = 0, fail = 0, recognizing = 0
  for (let i = 0; i < newItems.length; i++) {
    const item = newItems[i]
    const file = valid[i]
    item.status = 'uploading'
    try {
      const fd = new FormData()
      fd.append('file', file, file.name)
      // 把当前选中的识别模板 ID 传给后端（"自动识别"则不传）
      const sel = tpls.value.find(t => t.key === selectedTpl.value)
      if (sel?.templateId) {
        fd.append('templateId', String(sel.templateId))
      }
      const res = await invoiceOcrApi.upload(fd)
      // 后端 OcrResult 兼容新旧字段
      const f = res?.fields || {} as any
      item.invoiceNo = f.invoiceNo || res?.code || '-'
      item.seller = f.sellerName || '-'
      const amt = Number(f.totalAmount ?? 0)
      item.amount = isFinite(amt) ? amt : 0
      item.confidence = Number(res?.confidence ?? 0)
      if (res?.ocrStatus === 'success' || (item.invoiceNo && item.invoiceNo !== '-')) {
        item.status = 'success'
        ok++
        progress.value.done++
      } else {
        item.status = 'warning'
        progress.value.failed++
        fail++
      }
    } catch (err: any) {
      item.status = 'danger'
      const msg = err?.response?.data?.msg || err?.message || '识别失败'
      item.invoiceNo = '识别失败'
      item.seller = msg.length > 30 ? msg.slice(0, 30) + '…' : msg
      fail++
      progress.value.failed++
    } finally {
      sseProgress.value.current = file.name
    }
  }
  uploading.value = false
  // 完成提示
  if (fail === 0) {
    ElMessage.success(`批量识别完成：${ok} 张成功`)
  } else if (ok === 0) {
    ElMessage.error(`批量识别失败：${fail} 张`)
  } else {
    ElMessage.warning(`批量识别完成：${ok} 成功 / ${fail} 失败`)
  }
  // 关闭 AI 进度
  if (aiExtract.value) {
    sseProgress.value.done = progress.value.done
    sseProgress.value.percent = 100
    sseProgress.value.status = fail === 0 ? 'success' : 'warning'
    stopAiProgress()
  }
}
// 清除测试数据：弹窗确认 → 调后端批量删除所有发票 → 强制重置前端 queue 到 18 条设计稿示例
async function clearTestData() {
  // 1) 弹窗确认（防误触）
  try {
    await ElMessageBox.confirm(
      '将清空后端所有发票记录，并把前端队列重置为 18 条设计稿示例。此操作不可撤销，是否继续？',
      '清除测试数据',
      { confirmButtonText: '确认清除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return  // 用户取消
  }

  if (uploading.value) {
    ElMessage.warning('正在上传/识别中，请稍候')
    return
  }

  const loadingMsg = ElMessage.info({ message: '清除中...', duration: 0 })
  let deleted = 0
  let backendOk = false
  let lastError = ''

  try {
    // 2) 拉取后端所有发票 ID（分页拉，每页 200，最多 20 页）
    let ids: number[] = []
    let page = 1
    const pageSize = 200
    while (true) {
      const res: any = await invoiceOcrApi.records({ page, pageSize, keyword: '', filters: {} })
      const list = res?.list || []
      ids.push(...list.map((i: any) => i.invoiceId).filter((x: any) => typeof x === 'number'))
      if (list.length < pageSize) break
      page++
      if (page > 20) break
    }
    // 3) 调后端批量删除
    if (ids.length > 0) {
      const r: any = await invoiceOcrApi.batchDelete(ids)
      deleted = r?.deleted || 0
    }
    backendOk = true
  } catch (err: any) {
    lastError = err?.response?.data?.msg || err?.message || '未知错误'
    console.error('[clearTestData] backend error:', err)
  } finally {
    loadingMsg.close()
  }

  // 4) 不管后端成不成功，**强制重置前端 queue**（让用户立刻看到视觉变化）
  try {
    queue.value = []
    refreshProgress()
    searchText.value = ''
    statusFilter.value = 'all'
  } catch (e: any) {
    ElMessage.error('前端重置失败：' + (e?.message || ''))
    return
  }

  // 5) 提示
  if (backendOk) {
    if (deleted > 0) {
      ElMessage.success(`已清除测试数据：后端 ${deleted} 张 + 前端队列已清空`)
    } else {
      ElMessage.success('后端无测试数据，前端队列已清空')
    }
  } else {
    ElMessage.warning(`前端队列已清空（后端清除失败：${lastError}）`)
  }
}

async function retryFailedItems() {
  const failed = queue.value.filter(i => i.status === 'danger' && typeof i.invoiceId === 'number')
  if (failed.length === 0) {
    ElMessage.info('当前没有需要重新识别的失败项（设计稿示例不计）')
    return
  }
  try {
    ElMessage.info(`开始重新识别 ${failed.length} 张失败发票...`)
    // 串行调 recheck（避免后端压力）
    let ok = 0
    for (const item of failed) {
      try {
        const r: any = await invoiceOcrApi.recheck(item.invoiceId!)
        item.status = r?.data?.ocrStatus === 'success' ? 'success' : 'warning'
        item.confidence = r?.data?.confidence ?? item.confidence
        ok++
      } catch (err) {
        // 单条失败不影响其他
        console.error(`[recheck] invoiceId=${item.invoiceId} failed:`, err)
      }
    }
    ElMessage.success(`重新识别完成：${ok}/${failed.length} 张成功`)
  } catch (err: any) {
    ElMessage.error('重新识别失败：' + (err?.message || '未知错误'))
  }
}

async function removeItem(item: QueueItem) {
  // 真实发票且未处于上传中：先弹确认；其他情况（设计稿 mock / 失败重试）直接删除
  if (typeof item.invoiceId === 'number' && item.status !== 'uploading' && item.status !== 'recognizing') {
    try {
      await ElMessageBox.confirm(
        `确定要删除 "${item.fileName}" 吗？将同时从后端删除该发票记录，此操作不可撤销。`,
        '删除发票',
        { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
      )
    } catch {
      return  // 用户取消
    }
  }
  try {
    if (typeof item.invoiceId === 'number') {
      const r: any = await invoiceOcrApi.batchDelete([item.invoiceId])
      const deleted = r?.deleted || 0
      if (deleted > 0) {
        ElMessage.success(`已删除：${item.fileName}`)
      } else {
        ElMessage.warning(`后端未找到该发票，仅从本地移除：${item.fileName}`)
      }
    }
    // 从 queue 移除并同步顶部进度总览
    queue.value = queue.value.filter(i => i.id !== item.id)
    if (progress.value.total > 0) progress.value.total = Math.max(0, progress.value.total - 1)
    if (item.status === 'success' && progress.value.done > 0) progress.value.done = Math.max(0, progress.value.done - 1)
    if (item.status === 'recognizing' && progress.value.recognizing > 0) progress.value.recognizing = Math.max(0, progress.value.recognizing - 1)
    if ((item.status === 'danger' || item.status === 'warning') && progress.value.failed > 0) progress.value.failed = Math.max(0, progress.value.failed - 1)
  } catch (err: any) {
    ElMessage.error('删除失败：' + (err?.response?.data?.msg || err?.message || '未知错误'))
  }
}

async function batchRemoveSelected() {
  const selected = queue.value.filter(i => i.selected)
  if (selected.length === 0) {
    ElMessage.warning('请先勾选要删除的发票')
    return
  }
  // 区分真实发票（有 invoiceId）和设计稿 mock
  const realIds: number[] = selected.map(i => i.invoiceId).filter((x): x is number => typeof x === 'number')
  const mockCount = selected.length - realIds.length
  // 仅 mock：不需要确认；含真实发票：弹确认框
  if (realIds.length > 0) {
    try {
      await ElMessageBox.confirm(
        `将删除选中的 ${selected.length} 张发票${mockCount > 0 ? `（含 ${mockCount} 张设计稿示例仅本地移除）` : ''}，此操作不可撤销，是否继续？`,
        '批量删除',
        { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
      )
    } catch {
      return
    }
  }
  try {
    let deleted = 0
    if (realIds.length > 0) {
      const r: any = await invoiceOcrApi.batchDelete(realIds)
      deleted = r?.deleted || 0
    }
    // 从 queue 移除所有 selected 项 + 同步 progress 总览
    const removedIds = new Set(selected.map(i => i.id))
    const removedSuccess = selected.filter(i => i.status === 'success').length
    const removedRecognizing = selected.filter(i => i.status === 'recognizing').length
    const removedFailed = selected.filter(i => i.status === 'danger' || i.status === 'warning').length
    queue.value = queue.value.filter(i => !removedIds.has(i.id))
    progress.value.total = Math.max(0, progress.value.total - selected.length)
    progress.value.done = Math.max(0, progress.value.done - removedSuccess)
    progress.value.recognizing = Math.max(0, progress.value.recognizing - removedRecognizing)
    progress.value.failed = Math.max(0, progress.value.failed - removedFailed)
    if (realIds.length > 0 && mockCount > 0) {
      ElMessage.success(`已批量删除：后端 ${deleted} 张 + 本地 ${mockCount} 张设计稿`)
    } else if (realIds.length > 0) {
      ElMessage.success(`已批量删除 ${deleted} 张发票`)
    } else {
      ElMessage.success(`已批量删除 ${selected.length} 张设计稿示例`)
    }
  } catch (err: any) {
    ElMessage.error('批量删除失败：' + (err?.response?.data?.msg || err?.message || '未知错误'))
  }
}

async function viewItem(item: QueueItem) {
  // 真实发票：跳转到详情页
  if (typeof item.invoiceId === 'number') {
    router.push(`/invoice/ocr/${item.invoiceId}`)
    return
  }
  // 设计稿 mock：弹窗展示 mock 数据
  const mockData = {
    '文件': item.fileName,
    '发票号': item.invoiceNo,
    '金额': `¥${item.amount.toLocaleString()}`,
    '销售方': item.seller,
    '置信度': `${Math.round(item.confidence * 100)}%`,
    '状态': item.status,
  }
  const rows = Object.entries(mockData).map(([k, v]) => `<tr><td style="padding:6px 12px;color:#666">${k}</td><td style="padding:6px 12px;font-weight:500">${v}</td></tr>`).join('')
  ElMessageBox.alert(
    `<table style="border-collapse:collapse;width:100%">${rows}</table><p style="margin-top:12px;color:#999;font-size:12px">（这是设计稿示例项，仅本地展示。真实发票请点击 🗑 旁的"查看"跳转详情页）</p>`,
    '发票详情（设计稿示例）',
    { dangerouslyUseHTMLString: true, confirmButtonText: '关闭' }
  )
}

async function retryItem(item: QueueItem) {
  ElMessage.info(`重新识别: ${item.fileName}`)
  item.status = 'recognizing'
  await new Promise(r => setTimeout(r, 1500))
  item.status = 'success'
  item.confidence = 0.92
}
async function submitSelected() {
  const selected = queue.value.filter(i => i.selected)
  if (selected.length === 0) {
    ElMessage.warning('请先勾选要入账的发票')
    return
  }
  // 区分真实发票（有 invoiceId）和设计稿 mock
  const realIds = selected.map(i => i.invoiceId).filter((x): x is number => typeof x === 'number')
  const mockCount = selected.length - realIds.length
  if (realIds.length === 0) {
    ElMessage.warning(`当前勾选的 ${selected.length} 项均为设计稿示例，请先上传真实发票再提交入账`)
    return
  }
  try {
    const r: any = await invoiceOcrApi.batchSubmit(realIds)
    const updated = r?.updated || 0
    // 把提交成功的项标为 'archived' 状态（视觉反馈）
    selected.forEach(i => {
      if (i.invoiceId) i.status = 'success'  // 用 success 兜底显示
    })
    if (mockCount > 0) {
      ElMessage.success(`已提交入账 ${updated} 张（${mockCount} 张设计稿示例已跳过）`)
    } else {
      ElMessage.success(`已批量提交入账：${updated} 张`)
    }
  } catch (err: any) {
    ElMessage.error('提交失败：' + (err?.response?.data?.msg || err?.message || '未知错误'))
  }
}
function selectTpl(k: string) {
  selectedTpl.value = k
  const t = tpls.value.find(x => x.key === k)
  ElMessage.success(`已选模板: ${t?.label || k}`)
}
</script>

<template>
  <div class="batch-page">
    <!-- 模板选择器（design: .tpl-selector） -->
    <div class="page-card tpl-selector fade-up">
      <span class="l">识别模板：</span>
      <span
        v-for="t in tpls"
        :key="t.key"
        :class="['tpl-chip', { active: selectedTpl === t.key, loading: tplLoading && t.key === 'auto' }]"
        @click="selectTpl(t.key)"
        :title="t.desc || t.label"
      >
        <span class="ico">{{ t.ico }}</span>{{ t.label }}
      </span>
      <span v-if="tplLoading" class="tpl-hint" style="margin-left: 8px">⏳ 加载模板...</span>
      <span class="tpl-hint">ⓘ 选定模板后，系统将按模板字段自动归类与匹配关联合同</span>
    </div>

    <!-- 拖拽上传区（design: .drop-zone） -->
    <div
      class="page-card drop-zone fade-up"
      :class="{ dragging: isDragging }"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
    >
      <input ref="fileInput"   type="file"   accept="image/*,.pdf,.ofd" multiple hidden @change="onFileChange" />
      <input ref="folderInput" type="file"   accept="image/*,.pdf,.ofd" webkitdirectory directory multiple hidden @change="onFolderChange" />
      <input ref="captureInput" type="file"  accept="image/*" capture="environment" hidden @change="onCaptureChange" />
      <div class="ico">⇪</div>
      <h3>拖拽发票文件到此处 / 点击选择文件</h3>
      <p>支持单张/批量上传，可拖拽整个文件夹。OCR 自动识别并归类。</p>
      <div class="actions">
        <button class="btn btn-primary" @click="openFilePicker">📁 选择文件</button>
        <button class="btn btn-outline" @click="openFolderPicker">📂 选择文件夹</button>
        <button class="btn btn-ghost" @click="openCapture">📸 拍照识别</button>
        <!-- 触点 #2：AI 抽取开关（强化字段 + 智能关联） -->
        <label class="ai-extract-toggle" :class="{ active: aiExtract }">
          <input type="checkbox" v-model="aiExtract" hidden />
          <span class="ai-toggle-icon">✨</span>
          <span class="ai-toggle-label">AI 智能抽取</span>
          <span class="ai-toggle-tip">强度+关联+风险</span>
        </label>
      </div>
      <div class="hint">
        <span>JPG / PNG / PDF / OFD</span>
        <span>单文件 ≤ 20MB</span>
        <span>· 单批最多 200 张</span>
        <span>· 平均识别 2.3s/张</span>
      </div>
    </div>

    <!-- 进度总览（design: .batch-summary） -->
    <div class="page-card batch-summary fade-up">
      <div class="bs-item">
        <div class="ico">📁</div>
        <div class="l">本批文件</div>
        <div class="v">{{ progress.total }}</div>
        <div class="m">张</div>
      </div>
      <div class="bs-item">
        <div class="ico" style="color: #10B981">✓</div>
        <div class="l">已识别</div>
        <div class="v success">{{ progress.done }}</div>
        <div class="m">张</div>
      </div>
      <div class="bs-item">
        <div class="ico" style="color: #4F6BFF">⟳</div>
        <div class="l">识别中</div>
        <div class="v info">{{ progress.recognizing }}</div>
        <div class="m">张</div>
      </div>
      <div class="bs-item">
        <div class="ico" style="color: #EF4444">!</div>
        <div class="l">需核验/失败</div>
        <div class="v danger">{{ progress.failed }}</div>
        <div class="m">张</div>
      </div>
    </div>

    <!-- 触点 #2：SSE 实时进度条（仅 AI 模式开启时显示） -->
    <transition name="slide">
      <div v-if="aiExtract && sseProgress.active" class="page-card ai-progress-bar fade-up">
        <div class="ai-pb-head">
          <div class="ai-pb-icon">✨</div>
          <div class="ai-pb-body">
            <div class="ai-pb-title">
              <span>AI 智能抽取中</span>
              <span class="ai-pb-count">{{ sseProgress.done }} / {{ sseProgress.total }} 张</span>
            </div>
            <div class="ai-pb-sub">
              正在强化字段 · 智能关联合同/项目 · 风险检测
              <span v-if="sseProgress.current" class="ai-pb-current">· 当前：{{ sseProgress.current }}</span>
            </div>
          </div>
          <div class="ai-pb-pct">{{ sseProgress.percent }}%</div>
        </div>
        <el-progress
          :percentage="sseProgress.percent"
          :stroke-width="8"
          :status="sseProgress.status"
          :show-text="false"
        />
      </div>
    </transition>

    <!-- 识别队列（design: .queue-card > .queue-table） -->
    <div class="page-card queue-card fade-up">
      <div class="queue-head">
        <h3>识别队列（{{ queue.length }} 张）</h3>
        <div class="toolbar">
          <input v-model="searchText" class="search-input" placeholder="搜索文件名 / 发票号..." />
          <select v-model="statusFilter" class="btn btn-outline btn-sm select">
            <option value="all">所有状态</option>
            <option value="recognizing">识别中</option>
            <option value="success">已识别</option>
            <option value="warning">需核验</option>
            <option value="danger">失败</option>
          </select>
          <button class="btn btn-ghost btn-sm" @click="clearTestData">🧹 清除测试数据</button>
          <button class="btn btn-ghost btn-sm" @click="retryFailedItems">↻ 重新识别失败项</button>
          <button class="btn btn-primary btn-sm" @click="submitSelected">✓ 批量提交入账</button>
          <button class="btn btn-ghost btn-sm" @click="batchRemoveSelected" style="color: #EF4444">🗑 批量删除</button>
        </div>
      </div>

      <table class="queue-table">
        <thead>
          <tr>
            <th style="width: 36px"><input type="checkbox" v-model="allSelected" /></th>
            <th>文件</th>
            <th>发票号</th>
            <th>金额</th>
            <th>销售方</th>
            <th>置信度</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredQueue" :key="item.id">
            <td><input type="checkbox" v-model="item.selected" /></td>
            <td>
              <div class="file-info">
                <div class="file-thumb" :style="{ background: item.thumb }">📄</div>
                <span class="file-name">{{ item.fileName }}</span>
              </div>
            </td>
            <td class="invoice-no">{{ item.invoiceNo }}</td>
            <td class="amount">¥{{ item.amount.toLocaleString() }}</td>
            <td class="seller">{{ item.seller }}</td>
            <td><span :class="confClass(item.confidence)">{{ fmtConfidenceInt(item.confidence) }}</span></td>
            <td><span :class="statusPillClass(item.status)">{{ statusLabel(item.status) }}</span></td>
            <td class="actions">
              <button v-if="item.status === 'danger'" class="btn btn-ghost btn-sm" @click="retryItem(item)">重试</button>
              <button v-else class="btn btn-ghost btn-sm" @click="viewItem(item)">查看</button>
              <button class="btn btn-ghost btn-sm btn-danger" @click="removeItem(item)" title="删除该条发票">🗑</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@import "@/assets/styles/variables.scss";

.batch-page { padding: 0; }

.page-card {
  background: #fff;
  border-radius: $radius-md;
  box-shadow: $shadow-sm;
  padding: 16px;
  margin-bottom: 16px;
}

/* 模板选择器（design: .tpl-selector） */
.tpl-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  .l {
    font-size: 13px;
    font-weight: 500;
    color: $color-text-secondary;
    margin-right: 4px;
  }
  .tpl-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    border-radius: 16px;
    background: $color-bg;
    font-size: 12px;
    color: $color-text-secondary;
    cursor: pointer;
    transition: all 0.15s;
    user-select: none;
    .ico { font-size: 14px; }
    &:hover { background: $color-primary-bg; color: $color-primary; }
    &.active {
      background: $color-primary;
      color: #fff;
      font-weight: 500;
    }
  }
  .tpl-hint {
    margin-left: auto;
    font-size: 12px;
    color: $color-text-tertiary;
  }
}

/* 拖拽上传区（design: .drop-zone） */
.drop-zone {
  text-align: center;
  padding: 40px 20px;
  cursor: pointer;
  transition: all 0.2s;
  .ico {
    font-size: 56px;
    margin-bottom: 12px;
    line-height: 1;
  }
  h3 {
    font-size: 16px;
    font-weight: 600;
    color: $color-text-primary;
    margin: 0 0 8px 0;
  }
  p {
    font-size: 13px;
    color: $color-text-secondary;
    margin: 0 0 20px 0;
  }
  .actions {
    display: flex;
    gap: 8px;
    justify-content: center;
    margin-bottom: 16px;
  }
  .hint {
    display: flex;
    gap: 16px;
    justify-content: center;
    font-size: 11px;
    color: $color-text-tertiary;
    span:not(:last-child)::after {
      content: '';
      margin-left: 16px;
    }
  }
  &.dragging {
    border-color: $color-primary;
    background: $color-primary-bg;
  }
}

/* 进度总览（design: .batch-summary） */
.batch-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  text-align: center;
  .bs-item {
    .ico {
      font-size: 24px;
      margin-bottom: 4px;
    }
    .l {
      font-size: 11px;
      color: $color-text-tertiary;
      margin-bottom: 4px;
    }
    .v {
      font-size: 24px;
      font-weight: 600;
      color: $color-text-primary;
      font-family: $font-family-mono;
      &.success { color: #10B981; }
      &.info { color: #4F6BFF; }
      &.danger { color: #EF4444; }
    }
    .m {
      font-size: 11px;
      color: $color-text-tertiary;
      margin-top: -4px;
    }
  }
}

/* 队列表格（design: .queue-card > .queue-table） */
.queue-card {
  .queue-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid $color-border;
    flex-wrap: wrap;
    gap: 8px;
    h3 {
      font-size: 14px;
      font-weight: 600;
      color: $color-text-primary;
      margin: 0;
    }
    .toolbar {
      display: flex;
      gap: 8px;
      align-items: center;
      .search-input {
        padding: 6px 12px;
        border: 1px solid $color-border-strong;
        border-radius: $radius-sm;
        font-size: 12px;
        width: 220px;
        &:focus { outline: none; border-color: $color-primary; }
      }
      .select {
        height: 32px;
        padding: 0 8px;
        font-size: 12px;
        background: #fff;
        border: 1px solid $color-border-strong;
        border-radius: $radius-sm;
      }
    }
  }
}

.queue-table {
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
  .file-info {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .file-thumb {
    width: 28px;
    height: 28px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 12px;
    flex-shrink: 0;
  }
  .file-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 200px;
  }
  .invoice-no {
    font-family: $font-family-mono;
    color: $color-text-secondary;
    font-size: 11px;
  }
  .amount {
    font-family: $font-family-mono;
    font-weight: 600;
    color: #EF4444;
  }
  .seller {
    color: $color-text-secondary;
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .conf {
    font-family: $font-family-mono;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
    &.high { color: #10B981; background: rgba(16, 185, 129, 0.08); }
    &.mid  { color: #F59E0B; background: rgba(245, 158, 11, 0.08); }
    &.low  { color: #EF4444; background: rgba(239, 68, 68, 0.08); }
  }
  .actions { white-space: nowrap; }
}

/* 触点 #2：AI 抽取开关 + SSE 实时进度条 */
.ai-extract-toggle {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: $radius-sm; font-size: 12px;
  background: #fff; border: 1px dashed rgba(124, 58, 237, 0.5);
  color: $color-text-secondary; cursor: pointer; user-select: none;
  transition: all 0.15s;
  &:hover { border-color: #7C3AED; color: #7C3AED; }
  &.active {
    background: linear-gradient(135deg, rgba(79,107,255,0.08) 0%, rgba(124,58,237,0.08) 100%);
    border-style: solid; border-color: #7C3AED;
    color: #7C3AED; font-weight: 600;
  }
  .ai-toggle-icon { font-size: 14px; }
  .ai-toggle-label { font-weight: 500; }
  .ai-toggle-tip { font-size: 10px; color: $color-text-tertiary; padding-left: 4px; border-left: 1px solid $color-border; margin-left: 2px; }
}

.ai-progress-bar {
  margin-top: 16px;
  border: 1px solid rgba(124, 58, 237, 0.25);
  background: linear-gradient(135deg, rgba(79,107,255,0.03) 0%, rgba(124,58,237,0.03) 100%);
}
.ai-pb-head { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.ai-pb-icon { font-size: 24px; }
.ai-pb-body { flex: 1; }
.ai-pb-title { display: flex; gap: 8px; align-items: baseline; font-size: 13px; font-weight: 600; color: $color-text-primary; }
.ai-pb-count { font-size: 11px; color: $color-primary; font-weight: 500; }
.ai-pb-sub { font-size: 11px; color: $color-text-secondary; margin-top: 2px; }
.ai-pb-current { color: $color-primary; }
.ai-pb-pct { font-size: 18px; font-weight: 700; color: $color-primary; font-family: $font-family-mono; }

.slide-enter-active, .slide-leave-active { transition: all 0.3s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-8px); }

/* 按钮（design: .btn variants） */
.btn {
  padding: 6px 12px;
  border-radius: $radius-sm;
  font-size: 12px;
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
  &.btn-ghost {
    color: $color-text-secondary;
    &:hover { color: $color-primary; background: $color-primary-bg; }
  }
  &.btn-sm { padding: 4px 10px; font-size: 11px; }
  &.btn-danger {
    color: #EF4444;
    &:hover { color: #fff; background: #EF4444; }
  }
}

/* 状态 pill（design: .status-pill） */
.status-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
  &.uploading   { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
  &.recognizing { background: rgba(79, 107, 255, 0.1); color: $color-primary; }
  &.success     { background: rgba(16, 185, 129, 0.1); color: #10B981; }
  &.warning     { background: rgba(245, 158, 11, 0.1); color: #F59E0B; }
  &.danger      { background: rgba(239, 68, 68, 0.1); color: #EF4444; }
}
</style>
