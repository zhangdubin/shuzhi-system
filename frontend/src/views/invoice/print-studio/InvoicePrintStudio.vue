<script setup lang="ts">
/**
 * InvoicePrintStudio · 发票原件打印工作台
 * 三栏布局：发票列表 | 打印预览 | 打印参数
 * 支持：原件打印 / 拼版打印 / PDF导出 / 模板管理 / 打印历史
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { http } from '@/utils/request'

const router = useRouter()

// ===== 工具栏模式 =====
type ToolMode = 'print' | 'pdf' | 'layout' | 'template' | 'history'
const toolMode = ref<ToolMode>('print')

// ===== 发票列表 =====
const invoices = ref<any[]>([])
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(50)
const totalCount = ref(0)

const filteredInvoices = computed(() => {
  if (!searchQuery.value) return invoices.value
  const q = searchQuery.value.toLowerCase()
  return invoices.value.filter(inv =>
    (inv.invoiceNo || '').toLowerCase().includes(q) ||
    (inv.sellerName || '').toLowerCase().includes(q)
  )
})

// 选中的发票 ID
const selectedIds = ref<Set<number>>(new Set())
const selectedInvoices = computed(() =>
  invoices.value.filter(inv => selectedIds.value.has(inv.invoiceId))
)

function toggleSelect(id: number) {
  const s = new Set(selectedIds.value)
  s.has(id) ? s.delete(id) : s.add(id)
  selectedIds.value = s
}
function selectAll() { selectedIds.value = new Set(invoices.value.map(i => i.invoiceId)) }
function deselectAll() { selectedIds.value = new Set() }

async function loadInvoices() {
  loading.value = true
  try {
    const r: any = await http.post('/invoice/ocr/list', {
      page: currentPage.value, pageSize: pageSize.value,
      keyword: searchQuery.value, filters: {},
    })
    if (r?.list) {
      invoices.value = r.list
      totalCount.value = r.total || 0
    }
  } catch (e) {
    console.warn('[PrintStudio] load invoices failed', e)
  } finally {
    loading.value = false
  }
}

// ===== 打印参数 =====
const settings = ref({
  paper: 'A4',
  orientation: 'portrait' as 'portrait' | 'landscape',
  scaleMode: 'fit' as 'fit' | 'fitWidth' | 'fitHeight' | 'original',
  marginTop: 10,
  marginRight: 10,
  marginBottom: 10,
  marginLeft: 10,
  layoutCols: 1,
  layoutRows: 1,
  copies: 1,
  duplex: false,
  autoRotate: true,
  autoCenter: true,
  headerText: '',
  footerText: '',
  showQrcodeMargin: true,
})

const papers = ['A4', 'A3', 'A5', 'Letter', 'Legal']
const scaleModes = [
  { value: 'fit', label: '适应纸张' },
  { value: 'fitWidth', label: '适应宽度' },
  { value: 'fitHeight', label: '适应高度' },
  { value: 'original', label: '原尺寸' },
]
const layoutOptions = [
  { cols: 1, rows: 1, label: '1 张/页' },
  { cols: 2, rows: 1, label: '2 张/页（横排）' },
  { cols: 1, rows: 2, label: '2 张/页（竖排）' },
  { cols: 2, rows: 2, label: '4 张/页' },
  { cols: 3, rows: 2, label: '6 张/页' },
  { cols: 2, rows: 3, label: '6 张/页（竖排）' },
  { cols: 4, rows: 2, label: '8 张/页' },
]
function setLayout(cols: number, rows: number) {
  settings.value.layoutCols = cols
  settings.value.layoutRows = rows
}

// ===== 预览 =====
const previewHtml = ref('')
const previewLoading = ref(false)

function previewImageUrl(fileId: string) {
  return fileId ? '/api/v1/common/files/preview-image?fileId=' + encodeURIComponent(fileId) + '&dpi=100' : ''
}

function generatePreviewHtml() {
  const invs = selectedInvoices.value
  if (!invs.length) {
    previewHtml.value = '<div style="text-align:center;padding:60px;color:#94A3B8;">请从左侧选择要打印的发票</div>'
    return
  }
  const { layoutCols, layoutRows, marginTop, marginRight, marginBottom, marginLeft } = settings.value
  const perPage = layoutCols * layoutRows
  const pages: string[] = []

  for (let i = 0; i < invs.length; i += perPage) {
    const batch = invs.slice(i, i + perPage)
    const cells = batch.map(inv => {
      const url = previewImageUrl(inv.fileId)
      return url
        ? `<div class="pv-cell"><img src="${url}" style="width:100%;height:100%;object-fit:contain;" /><div class="pv-cell-label">${inv.invoiceNo || ''}</div></div>`
        : `<div class="pv-cell empty">无原件</div>`
    }).join('')
    const empty = Array(perPage - batch.length).fill('<div class="pv-cell empty"></div>').join('')
    pages.push(`<div class="pv-page" style="padding:${marginTop}mm ${marginRight}mm ${marginBottom}mm ${marginLeft}mm;"><div class="pv-grid" style="grid-template-columns:repeat(${layoutCols},1fr);grid-template-rows:repeat(${layoutRows},1fr);">${cells}${empty}</div></div>`)
  }
  previewHtml.value = pages.join('')
}

watch([selectedIds, settings], () => { generatePreviewHtml() }, { deep: true })

// ===== 打印 =====
async function doPrint() {
  if (!selectedInvoices.value.length) { ElMessage.warning('请先选择发票'); return }
  const iframe = document.createElement('iframe')
  iframe.style.cssText = 'position:fixed;left:-9999px;top:0;width:210mm;height:297mm;'
  document.body.appendChild(iframe)
  const doc = iframe.contentDocument!
  doc.open()
  doc.write(`<!DOCTYPE html><html><head><style>
    @page { size: ${settings.value.paper}; margin: 0; }
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:sans-serif; }
    .pv-page { width:100%; height:100vh; page-break-after:always; display:flex; }
    .pv-page:last-child { page-break-after:auto; }
    .pv-grid { display:grid; gap:2mm; width:100%; height:100%; }
    .pv-cell { border:0.3px solid #E5E7EB; overflow:hidden; display:flex; flex-direction:column; position:relative; }
    .pv-cell img { flex:1; object-fit:contain; width:100%; }
    .pv-cell-label { font-size:7px; color:#6B7280; padding:1mm; text-align:center; }
    .pv-cell.empty { border-style:dashed; }
  </style></head><body>${previewHtml.value}</body></html>`)
  doc.close()
  setTimeout(() => {
    iframe.contentWindow?.focus()
    iframe.contentWindow?.print()
    setTimeout(() => document.body.removeChild(iframe), 2000)
  }, 1500)
  // 写入打印历史
  try {
    await http.post('/invoice/print/batch', {
      invoiceIds: selectedInvoices.value.map(i => i.invoiceId),
      mode: 'layout',
      layoutDesc: `${settings.value.layoutCols}x${settings.value.layoutRows}`,
      copies: settings.value.copies,
    })
  } catch {}
}

// ===== PDF 导出 =====
async function doExportPdf() {
  if (!selectedInvoices.value.length) { ElMessage.warning('请先选择发票'); return }
  ElMessage.info('PDF 导出功能开发中')
}

// ===== 模板 =====
const templates = ref<any[]>([])
async function loadTemplates() {
  try {
    const r: any = await http.get('/invoice/print/templates')
    if (r?.list) templates.value = r.list
  } catch {}
}

// ===== 打印历史 =====
const history = ref<any[]>([])
async function loadHistory() {
  try {
    const r: any = await http.get('/invoice/print/history', { params: { page: 1, pageSize: 50 } })
    if (r?.list) history.value = r.list
  } catch {}
}

onMounted(() => {
  loadInvoices()
  loadTemplates()
  loadHistory()
})
</script>

<template>
  <div class="ips-container">
    <!-- 工具栏 -->
    <div class="ips-toolbar">
      <div class="ips-tools">
        <button :class="['ips-tool', { active: toolMode === 'print' }]" @click="toolMode = 'print'">🖨 原件打印</button>
        <button :class="['ips-tool', { active: toolMode === 'layout' }]" @click="toolMode = 'layout'">📐 拼版打印</button>
        <button :class="['ips-tool', { active: toolMode === 'pdf' }]" @click="toolMode = 'pdf'">📄 PDF 导出</button>
        <button :class="['ips-tool', { active: toolMode === 'template' }]" @click="toolMode = 'template'">📋 打印模板</button>
        <button :class="['ips-tool', { active: toolMode === 'history' }]" @click="toolMode = 'history'">📜 打印历史</button>
      </div>
      <div class="ips-actions">
        <span class="ips-count">已选 {{ selectedIds.size }} / {{ invoices.length }}</span>
        <button class="ips-btn ips-btn-primary" @click="doPrint" :disabled="!selectedIds.size">🖨 打印</button>
        <button class="ips-btn ips-btn-outline" @click="doExportPdf" :disabled="!selectedIds.size">📄 PDF</button>
      </div>
    </div>

    <!-- 三栏主体 -->
    <div class="ips-body">
      <!-- 左栏：发票列表 -->
      <div class="ips-left">
        <div class="ips-left-head">
          <input v-model="searchQuery" class="ips-search" placeholder="搜索发票号/销售方…" @input="loadInvoices" />
          <div class="ips-select-actions">
            <a @click="selectAll">全选</a>
            <a @click="deselectAll">清空</a>
          </div>
        </div>
        <div class="ips-invoice-list">
          <div v-if="loading" class="ips-loading">加载中…</div>
          <div
            v-for="inv in filteredInvoices"
            :key="inv.invoiceId"
            :class="['ips-inv', { selected: selectedIds.has(inv.invoiceId) }]"
            @click="toggleSelect(inv.invoiceId)"
          >
            <input type="checkbox" :checked="selectedIds.has(inv.invoiceId)" />
            <div class="ips-inv-body">
              <div class="ips-inv-no">{{ inv.invoiceNo || '—' }}</div>
              <div class="ips-inv-meta">{{ inv.sellerName || '—' }}</div>
              <div class="ips-inv-amt">¥ {{ (Number(inv.totalAmount || 0) / 100).toFixed(2) }}</div>
            </div>
            <span v-if="!inv.fileId" class="ips-inv-nofile">无原件</span>
          </div>
        </div>
      </div>

      <!-- 中栏：预览 -->
      <div class="ips-center">
        <div class="ips-preview-head">
          <span>A4 预览 · {{ settings.layoutCols }}×{{ settings.layoutRows }}</span>
          <span>{{ selectedIds.size }} 张</span>
        </div>
        <div class="ips-preview-body" v-html="previewHtml"></div>
      </div>

      <!-- 右栏：参数 -->
      <div class="ips-right">
        <!-- 拼版 -->
        <div class="ips-param-section">
          <h3>拼版方式</h3>
          <div class="ips-layout-grid">
            <div
              v-for="lo in layoutOptions"
              :key="lo.label"
              :class="['ips-lo', { active: settings.layoutCols === lo.cols && settings.layoutRows === lo.rows }]"
              @click="setLayout(lo.cols, lo.rows)"
            >
              <div class="ips-lo-icon" :style="{ display:'grid', gridTemplateColumns:`repeat(${Math.min(lo.cols,4)},1fr)`, gridTemplateRows:`repeat(${Math.min(lo.rows,3)},1fr)` }">
                <div v-for="n in lo.cols * lo.rows" :key="n" class="ips-lo-dot"></div>
              </div>
              <span>{{ lo.label }}</span>
            </div>
          </div>
        </div>

        <!-- 纸张 -->
        <div class="ips-param-section">
          <h3>纸张</h3>
          <div class="ips-param-row">
            <select v-model="settings.paper" class="ips-select">
              <option v-for="p in papers" :key="p" :value="p">{{ p }}</option>
            </select>
            <select v-model="settings.orientation" class="ips-select">
              <option value="portrait">纵向</option>
              <option value="landscape">横向</option>
            </select>
          </div>
        </div>

        <!-- 缩放 -->
        <div class="ips-param-section">
          <h3>缩放</h3>
          <select v-model="settings.scaleMode" class="ips-select ips-full">
            <option v-for="s in scaleModes" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>

        <!-- 页边距 -->
        <div class="ips-param-section">
          <h3>页边距 (mm)</h3>
          <div class="ips-margin-grid">
            <label>上 <input type="number" v-model.number="settings.marginTop" min="0" max="50" class="ips-num" /></label>
            <label>右 <input type="number" v-model.number="settings.marginRight" min="0" max="50" class="ips-num" /></label>
            <label>下 <input type="number" v-model.number="settings.marginBottom" min="0" max="50" class="ips-num" /></label>
            <label>左 <input type="number" v-model.number="settings.marginLeft" min="0" max="50" class="ips-num" /></label>
          </div>
        </div>

        <!-- 选项 -->
        <div class="ips-param-section">
          <h3>选项</h3>
          <label class="ips-check"><input type="checkbox" v-model="settings.autoRotate" /> 自动旋转</label>
          <label class="ips-check"><input type="checkbox" v-model="settings.autoCenter" /> 自动居中</label>
          <label class="ips-check"><input type="checkbox" v-model="settings.showQrcodeMargin" /> 保留二维码边距</label>
        </div>

        <!-- 份数 -->
        <div class="ips-param-section">
          <h3>份数</h3>
          <input type="number" v-model.number="settings.copies" min="1" max="999" class="ips-num ips-full" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.ips-container { display:flex; flex-direction:column; height:calc(100vh - 60px); background:#F1F5F9; }

// 工具栏
.ips-toolbar { display:flex; justify-content:space-between; align-items:center; padding:8px 16px; background:#fff; border-bottom:1px solid #E2E8F0; flex-shrink:0; }
.ips-tools { display:flex; gap:4px; }
.ips-tool { padding:6px 14px; border:1px solid #E2E8F0; border-radius:6px; background:#fff; cursor:pointer; font-size:12px; font-weight:500; color:#475569; font-family:inherit; transition:all .15s; &:hover { border-color:#4F6BFF; color:#4F6BFF; } &.active { background:#EEF2FF; border-color:#4F6BFF; color:#4F6BFF; } }
.ips-actions { display:flex; align-items:center; gap:10px; }
.ips-count { font-size:12px; color:#64748B; }
.ips-btn { padding:0 14px; height:32px; font-size:12px; font-weight:500; border-radius:6px; cursor:pointer; border:1px solid transparent; font-family:inherit; transition:all .15s; }
.ips-btn-primary { background:linear-gradient(135deg,#4F6BFF,#3D5BE0); color:#fff; box-shadow:0 2px 6px rgba(79,107,255,.3); &:disabled { opacity:.5; cursor:not-allowed; } }
.ips-btn-outline { background:#fff; border-color:#E2E8F0; color:#374151; &:hover { border-color:#4F6BFF; color:#4F6BFF; } &:disabled { opacity:.5; cursor:not-allowed; } }

// 三栏
.ips-body { display:flex; flex:1; min-height:0; gap:1px; background:#E2E8F0; }

// 左栏
.ips-left { width:280px; background:#fff; display:flex; flex-direction:column; overflow:hidden; }
.ips-left-head { padding:10px 12px; border-bottom:1px solid #E2E8F0; display:flex; flex-direction:column; gap:6px; }
.ips-search { width:100%; padding:6px 10px; border:1px solid #E2E8F0; border-radius:6px; font-size:12px; font-family:inherit; &:focus { outline:none; border-color:#4F6BFF; } }
.ips-select-actions { display:flex; gap:10px; justify-content:flex-end; a { font-size:11px; color:#4F6BFF; cursor:pointer; } }
.ips-invoice-list { flex:1; overflow-y:auto; padding:6px; }
.ips-loading { text-align:center; padding:30px; color:#94A3B8; font-size:13px; }
.ips-inv { display:flex; align-items:center; gap:8px; padding:6px 8px; border-radius:6px; cursor:pointer; transition:all .15s; &:hover { background:#F8FAFC; } &.selected { background:#EEF2FF; } }
.ips-inv input { accent-color:#4F6BFF; }
.ips-inv-body { flex:1; min-width:0; }
.ips-inv-no { font-size:11px; font-weight:600; color:#0F172A; font-family:'SF Mono',monospace; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ips-inv-meta { font-size:10px; color:#64748B; margin-top:1px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.ips-inv-amt { font-size:10px; color:#DC2626; font-weight:500; margin-top:1px; }
.ips-inv-nofile { font-size:9px; color:#DC2626; white-space:nowrap; }

// 中栏
.ips-center { flex:1; display:flex; flex-direction:column; background:#F1F5F9; overflow:hidden; }
.ips-preview-head { display:flex; justify-content:space-between; padding:8px 14px; background:#fff; border-bottom:1px solid #E2E8F0; font-size:12px; color:#475569; }
.ips-preview-body { flex:1; overflow-y:auto; padding:14px; }
.ips-preview-body :deep(.pv-page) { background:#fff; box-shadow:0 1px 4px rgba(0,0,0,.08); border-radius:4px; margin-bottom:12px; aspect-ratio:210/297; overflow:hidden; }
.ips-preview-body :deep(.pv-grid) { display:grid; gap:2mm; width:100%; height:100%; }
.ips-preview-body :deep(.pv-cell) { border:0.5px solid #E5E7EB; overflow:hidden; display:flex; flex-direction:column; border-radius:2px; }
.ips-preview-body :deep(.pv-cell.empty) { border-style:dashed; background:#FAFBFC; }
.ips-preview-body :deep(.pv-cell img) { flex:1; object-fit:contain; width:100%; }
.ips-preview-body :deep(.pv-cell-label) { font-size:8px; color:#6B7280; padding:1mm; text-align:center; }

// 右栏
.ips-right { width:240px; background:#fff; overflow-y:auto; padding:12px; display:flex; flex-direction:column; gap:14px; }
.ips-param-section { h3 { font-size:12px; font-weight:600; color:#0F172A; margin-bottom:8px; } }
.ips-param-row { display:flex; gap:6px; }
.ips-select { width:100%; padding:5px 8px; border:1px solid #E2E8F0; border-radius:5px; font-size:12px; font-family:inherit; background:#fff; &:focus { outline:none; border-color:#4F6BFF; } }
.ips-full { width:100%; }
.ips-num { width:60px; padding:5px 8px; border:1px solid #E2E8F0; border-radius:5px; font-size:12px; font-family:inherit; &:focus { outline:none; border-color:#4F6BFF; } }
.ips-margin-grid { display:grid; grid-template-columns:1fr 1fr; gap:6px; label { font-size:11px; color:#475569; display:flex; align-items:center; gap:4px; } }
.ips-check { display:flex; align-items:center; gap:6px; font-size:12px; color:#475569; cursor:pointer; margin-bottom:4px; input { accent-color:#4F6BFF; } }

.ips-layout-grid { display:flex; flex-direction:column; gap:4px; }
.ips-lo { display:flex; align-items:center; gap:8px; padding:5px 8px; border:1px solid #E2E8F0; border-radius:5px; cursor:pointer; font-size:11px; color:#475569; transition:all .15s; &:hover { border-color:#4F6BFF; } &.active { background:#EEF2FF; border-color:#4F6BFF; color:#4F6BFF; font-weight:500; } }
.ips-lo-icon { width:24px; height:24px; gap:1px; }
.ips-lo-dot { background:#CBD5E1; border-radius:1px; }
.ips-lo.active .ips-lo-dot { background:#4F6BFF; }
</style>
