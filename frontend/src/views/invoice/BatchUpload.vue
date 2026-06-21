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
import { fmtConfidenceInt, confToPct } from '@/utils/format'
import { ElMessage } from 'element-plus'
import { invoiceOcrApi } from '@/api/modules'
import { aiApi } from '@/api/ai'

const fileInput = ref<HTMLInputElement>()
const uploading = ref(false)
const isDragging = ref(false)

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

// 模板选择
type TplKey = 'auto' | 'travel' | 'office' | 'software' | 'more'
const tpls: { key: TplKey; ico: string; label: string }[] = [
  { key: 'auto',     ico: '⚡', label: '自动识别' },
  { key: 'travel',   ico: '✈', label: '差旅报销模板' },
  { key: 'office',   ico: '▣', label: '办公采购模板' },
  { key: 'software', ico: '软', label: '软件服务费模板' },
  { key: 'more',     ico: '+', label: '更多模板' },
]
const selectedTpl = ref<TplKey>('auto')

// 进度总览
const progress = ref({ total: 18, done: 12, recognizing: 4, failed: 2 })

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
}
const queue = ref<QueueItem[]>([
  { id: 1, fileName: 'invoice_滴滴_20260517.pdf', thumb: '#4F6BFF', invoiceNo: '26112000001961698396', amount: 248.00, seller: '北京逐鹿茶艺有限责任公司西直门店', confidence: 0.94, status: 'success', selected: true },
  { id: 2, fileName: 'invoice_京东_20260518.pdf',   thumb: '#EF4444', invoiceNo: '01100260071120260518',     amount: 1280.00, seller: '京东商城',     confidence: 0.91, status: 'success', selected: true },
  { id: 3, fileName: 'invoice_美团_20260519.pdf',   thumb: '#F59E0B', invoiceNo: '01100200051120260519',     amount: 86.50,   seller: '美团',         confidence: 0.88, status: 'warning', selected: true },
  { id: 4, fileName: 'invoice_携程_20260520.pdf',   thumb: '#10B981', invoiceNo: '01100260071120260520',     amount: 2340.00, seller: '携程计算机技术（上海）有限公司', confidence: 0.96, status: 'success', selected: false },
  { id: 5, fileName: 'invoice_用友_20260521.pdf',   thumb: '#7C3AED', invoiceNo: '01100200051120260521',     amount: 5800.00, seller: '用友网络科技股份有限公司',     confidence: 0.92, status: 'success', selected: false },
  { id: 6, fileName: 'invoice_滴滴_20260522.pdf',   thumb: '#4F6BFF', invoiceNo: '26112000001961698322',     amount: 156.30,   seller: '滴滴出行科技有限公司',         confidence: 0.85, status: 'recognizing', selected: false },
  { id: 7, fileName: 'invoice_阿里_20260523.pdf',   thumb: '#EF4444', invoiceNo: '01100260071120260523',     amount: 3200.00, seller: '阿里云计算有限公司',         confidence: 0.79, status: 'warning', selected: false },
  { id: 8, fileName: 'invoice_百度_20260524.pdf',   thumb: '#7C3AED', invoiceNo: '01100200051120260524',     amount: 450.00,   seller: '百度',           confidence: 0.91, status: 'success', selected: false },
  { id: 9, fileName: 'invoice_华为_20260525.pdf',   thumb: '#EF4444', invoiceNo: '01100260071120260525',     amount: 8800.00, seller: '华为',           confidence: 0.93, status: 'success', selected: false },
  { id: 10, fileName: 'invoice_小米_20260526.pdf',  thumb: '#F59E0B', invoiceNo: '01100200051120260526',     amount: 199.00,  seller: '小米',           confidence: 0.87, status: 'danger',  selected: false },
  { id: 11, fileName: 'invoice_苹果_20260527.pdf',  thumb: '#10B981', invoiceNo: '01100260071120260527',     amount: 9999.00, seller: '苹果',           confidence: 0.95, status: 'success', selected: false },
  { id: 12, fileName: 'invoice_联想_20260528.pdf',  thumb: '#4F6BFF', invoiceNo: '01100200051120260528',     amount: 6500.00, seller: '联想',           confidence: 0.90, status: 'success', selected: false },
  { id: 13, fileName: 'invoice_滴滴_20260529.pdf',  thumb: '#4F6BFF', invoiceNo: '26112000001961698329',     amount: 88.00,   seller: '滴滴',           confidence: 0.65, status: 'recognizing', selected: false },
  { id: 14, fileName: 'invoice_万达_20260530.pdf',  thumb: '#EF4444', invoiceNo: '01100260071120260530',     amount: 320.00,  seller: '万达',           confidence: 0.93, status: 'success', selected: false },
  { id: 15, fileName: 'invoice_海底捞_20260601.pdf', thumb: '#10B981', invoiceNo: '01100200051120260601',     amount: 480.00,  seller: '海底捞',         confidence: 0.91, status: 'success', selected: false },
  { id: 16, fileName: 'invoice_国美_20260602.pdf',  thumb: '#7C3AED', invoiceNo: '01100260071120260602',     amount: 2300.00, seller: '国美',           confidence: 0.88, status: 'success', selected: false },
  { id: 17, fileName: 'invoice_顺丰_20260603.pdf',  thumb: '#F59E0B', invoiceNo: '01100200051120260603',     amount: 35.00,   seller: '顺丰',           confidence: 0.82, status: 'warning', selected: false },
  { id: 18, fileName: 'invoice_网易_20260604.pdf',  thumb: '#EF4444', invoiceNo: '01100260071120260604',     amount: 1200.00, seller: '网易',           confidence: 0.55, status: 'uploading', selected: false },
])

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
  ElMessage.info('拖拽文件检测到，请用"选择文件"按钮（演示用）')
}
function onFileSelect() {
  fileInput.value?.click()
  // 触点 #2：选择文件后，若开启 AI 抽取则启动 SSE 实时进度
  if (aiExtract.value) {
    const total = queue.value.length
    if (total > 0) startAiProgress(total)
  }
}
function onFolderSelect() {
  ElMessage.info('选择文件夹：浏览器限制，需要通过 webkitdirectory 属性实现')
}
function onCapture() {
  ElMessage.info('拍照识别：暂未实装')
}
async function retryItem(item: QueueItem) {
  ElMessage.info(`重新识别: ${item.fileName}`)
  item.status = 'recognizing'
  await new Promise(r => setTimeout(r, 1500))
  item.status = 'success'
  item.confidence = 0.92
}
function submitSelected() {
  const selected = queue.value.filter(i => i.selected)
  if (selected.length === 0) {
    ElMessage.warning('请先勾选要入账的发票')
    return
  }
  ElMessage.success(`已批量提交入账：${selected.length} 张`)
}
function selectTpl(k: TplKey) {
  selectedTpl.value = k
  ElMessage.info(`已选模板: ${tpls.find(t => t.key === k)?.label}`)
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
        :class="['tpl-chip', { active: selectedTpl === t.key }]"
        @click="selectTpl(t.key)"
      >
        <span class="ico">{{ t.ico }}</span>{{ t.label }}
      </span>
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
      <input ref="fileInput" type="file" accept="image/*,.pdf" multiple hidden @change="onFileSelect" />
      <div class="ico">⇪</div>
      <h3>拖拽发票文件到此处 / 点击选择文件</h3>
      <p>支持单张/批量上传，可拖拽整个文件夹。OCR 自动识别并归类。</p>
      <div class="actions">
        <button class="btn btn-primary" @click="onFileSelect">📁 选择文件</button>
        <button class="btn btn-outline" @click="onFolderSelect">📂 选择文件夹</button>
        <button class="btn btn-ghost" @click="onCapture">📸 拍照识别</button>
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
          <button class="btn btn-ghost btn-sm" @click="ElMessage.info('重新识别失败项')">↻ 重新识别失败项</button>
          <button class="btn btn-primary btn-sm" @click="submitSelected">✓ 批量提交入账</button>
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
              <button v-else class="btn btn-ghost btn-sm">查看</button>
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
