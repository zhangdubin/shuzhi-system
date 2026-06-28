<!--
  AdminPrintTemplateEditor · 模板编辑器（M3 阶段 1）
  - 三栏布局：左基础设置 / 中 JSON 编辑器 / 右实时预览
  - 路由：/admin/print-template/editor/:id? （id 缺省 = 新建）
  - 实时预览：输入停止 600ms 后自动调 /print/preview-schema
  - 业务数据下拉：复用 AdminPrintTemplate 的 fetchBusinessList 逻辑
  - 不上：拖拽、属性面板、坐标定位（推到 M3+ 阶段 2+）
-->
<template>
  <div class="editor-page">
    <!-- 顶部工具栏 -->
    <div class="editor-header">
      <div class="header-left">
        <el-button link @click="goBack">← 返回列表</el-button>
        <span class="header-title">
          {{ isNew ? '新建打印模板' : `编辑模板 · ${form.name || form.code}` }}
        </span>
        <el-tag v-if="!isNew" :type="(STATUS_TAG[status] || {}).type as any" size="small">
          {{ (STATUS_TAG[status] || {}).label || status }}
        </el-tag>
        <el-tag v-if="!isNew" type="info" size="small">v{{ version }}</el-tag>
      </div>
      <div class="header-right">
        <el-button v-if="isNew" @click="excelImportOpen = true">📥 导入 Excel</el-button>
        <el-button v-if="isNew" @click="docxImportOpen = true">📥 导入 Word</el-button>
        <el-button :disabled="!isDirty || saving" @click="resetForm">↺ 撤销</el-button>
        <el-button type="primary" :loading="saving" @click="save">{{ isNew ? '创建（draft）' : '保存' }}</el-button>
        <el-button v-if="!isNew && status === 'draft'" type="success" :loading="publishing" @click="publish">发布</el-button>
      </div>
    </div>

    <div class="editor-body">
      <!-- 左：基础设置 -->
      <div class="editor-pane editor-pane-left">
        <div class="pane-section">
          <h3 class="pane-title">基础信息</h3>
          <el-form :model="form" label-width="80px" size="default">
            <el-form-item label="code" required>
              <el-input v-model="form.code" :disabled="!isNew" placeholder="例：custom_contract_v1" />
            </el-form-item>
            <el-form-item label="name" required>
              <el-input v-model="form.name" placeholder="例：合同模板 V1" />
            </el-form-item>
            <el-form-item label="业务类型" required>
              <el-select v-model="form.docType" :disabled="!isNew" style="width:100%">
                <el-option v-for="t in DOC_TYPES" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="纸型">
              <el-select v-model="form.paper" style="width:100%">
                <el-option label="A4" value="A4" />
                <el-option label="A3" value="A3" />
                <el-option label="A5" value="A5" />
              </el-select>
            </el-form-item>
            <el-form-item label="方向">
              <el-radio-group v-model="form.orientation">
                <el-radio value="portrait">纵向</el-radio>
                <el-radio value="landscape">横向</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="form.description" type="textarea" :rows="2" />
            </el-form-item>
          </el-form>
        </div>

        <div class="pane-section">
          <h3 class="pane-title">数据绑定</h3>
          <el-form label-width="80px" size="default">
            <el-form-item label="预览数据">
              <el-select v-model="previewBusinessId" :loading="bizLoading" placeholder="请选择一条业务记录" style="width:100%">
                <el-option
                  v-for="opt in previewBusinessOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
          </el-form>
          <div class="hint">
            <p>💡 可用变量：<code v-pre>{{ contract.code }}</code> <code v-pre>{{ invoice.no }}</code> <code v-pre>{{ printTime }}</code></p>
            <p>📦 支持 filter：<code v-pre>{{ x | money }}</code> <code v-pre>{{ x | chinese_money }}</code> <code v-pre>{{ x | default(VALUE) }}</code></p>
            <p>📚 元素类型：<code>title</code> / <code>text</code> / <code>spacer</code> / <code>line</code> / <code>table</code></p>
          </div>
        </div>
      </div>

      <!-- 中：JSON / 可视化 双模式 -->
      <div class="editor-pane editor-pane-center">
        <el-tabs v-model="editorMode" class="editor-tabs">
          <!-- 📝 JSON 模式 (M3 阶段 1 原版完全保留) -->
          <el-tab-pane label="📝 JSON" name="json">
            <div class="pane-toolbar">
              <span class="pane-title">模板 JSON (schemaJson)</span>
              <div class="toolbar-right">
                <span v-if="jsonError" class="err-flag">⚠ JSON 错误</span>
                <span v-else-if="previewBusy" class="ok-flag">⏳ 渲染中…</span>
                <span v-else-if="previewElapsed" class="ok-flag">✓ {{ previewElapsed }}ms</span>
                <el-button link size="small" @click="formatJson">格式化</el-button>
                <el-button link size="small" @click="loadPreset">📋 加载预置</el-button>
              </div>
            </div>
            <el-input
              v-model="jsonRaw"
              type="textarea"
              :rows="22"
              spellcheck="false"
              class="json-editor"
              @input="onJsonChange"
            />
            <div v-if="jsonError" class="json-err">⚠ {{ jsonError }}</div>
          </el-tab-pane>

          <!-- 🎨 可视化模式 (M3 阶段 3 新增) -->
          <el-tab-pane label="🎨 可视化" name="visual">
            <div class="visual-layout">
              <ComponentPalette @add="onVisualAdd" />
              <div class="visual-main">
                <VisualCanvas
                  :body="visualBody"
                  :selected-index="visualSelectedIndex"
                  @select="(i: number) => visualSelectedIndex = i"
                  @remove="onVisualRemove"
                  @move="onVisualMove"
                  @add="onVisualAddByComp"
                />
                <PropertyPanel
                  :component="visualSelectedComp"
                  :doc-type="form.docType"
                  @update="onVisualUpdate"
                />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 右：实时预览 -->
      <div class="editor-pane editor-pane-right">
        <div class="pane-toolbar">
          <span class="pane-title">实时预览</span>
          <el-button link size="small" @click="reloadPreview">🔄 刷新</el-button>
        </div>
        <div class="preview-wrap">
          <iframe
            v-if="previewHtml"
            :srcdoc="previewHtml"
            class="preview-iframe"
            sandbox="allow-same-origin"
          />
          <div v-else-if="previewBusy" class="preview-empty">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>渲染中…</span>
          </div>
          <div v-else-if="previewError" class="preview-error">
            <el-alert :title="previewError" type="error" :closable="false" show-icon />
          </div>
          <div v-else class="preview-empty">
            <p>👈 编辑左侧 JSON 后会自动预览</p>
            <p class="muted">或点上方「刷新」手动触发</p>
          </div>
        </div>
      </div>
    </div>

    <ExcelImportDialog
      v-model="excelImportOpen"
      @success="onImportSuccess"
    />

    <WordImportDialog
      v-model="docxImportOpen"
      @success="onImportSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { printApi } from '@/api/print'
import { contractApi, invoiceOcrApi, expenseApi, reimburseApi } from '@/api/modules'
import ComponentPalette from '@/components/admin/print/ComponentPalette.vue'
import VisualCanvas from '@/components/admin/print/VisualCanvas.vue'
import PropertyPanel from '@/components/admin/print/PropertyPanel.vue'
import { cloneComp, type CompMeta, findMeta } from '@/components/admin/print/compTemplates'
import ExcelImportDialog from '@/components/admin/print/ExcelImportDialog.vue'
import WordImportDialog from '@/components/admin/print/WordImportDialog.vue'

const route = useRoute()
const router = useRouter()

const isNew = computed(() => !route.params.id)
const editingId = computed(() => route.params.id ? Number(route.params.id) : 0)

const DOC_TYPES = [
  { label: '合同', value: 'contract' },
  { label: '发票', value: 'invoice' },
  { label: '报销单', value: 'reimbursement' },
  { label: '费用', value: 'expense' },
]

const STATUS_TAG: Record<string, { label: string; type: string }> = {
  active:   { label: '已发布', type: 'success' },
  draft:    { label: '草稿',   type: 'warning' },
  archived: { label: '已归档', type: 'info' },
}

const form = reactive({
  code: '',
  name: '',
  docType: 'contract',
  paper: 'A4',
  orientation: 'portrait',
  description: '',
  schemaJson: { body: [] } as any,
})

// M3 阶段 3: 可视化模式状态
const editorMode = ref<'json' | 'visual'>('visual')  // 默认可视化
const visualBody = ref<Record<string, any>[]>([])
const visualSelectedIndex = ref<number>(-1)
const visualSelectedComp = computed(() => {
  if (visualSelectedIndex.value < 0 || visualSelectedIndex.value >= visualBody.value.length) return null
  return visualBody.value[visualSelectedIndex.value]
})
let syncingFromJson = false  // 防止循环同步
const excelImportOpen = ref(false)
const docxImportOpen = ref(false)

const jsonRaw = ref<string>('{\n  "body": []\n}')
const jsonError = ref<string | null>(null)
const status = ref('draft')
const version = ref(1)
const saving = ref(false)
const publishing = ref(false)
const isDirty = ref(false)

// 业务数据下拉
const previewBusinessOptions = ref<Array<{ label: string; value: number }>>([])
const previewBusinessId = ref<number | null>(null)
const bizLoading = ref(false)

// 预览
const previewHtml = ref<string>('')
const previewBusy = ref(false)
const previewError = ref<string | null>(null)
const previewElapsed = ref(0)

let previewTimer: any = null
let initialJson = ''

function goBack() {
  if (isDirty.value) {
    ElMessageBox.confirm('有未保存的修改，确定离开？', '提示', { type: 'warning' })
      .then(() => router.push('/admin/print-template'))
      .catch(() => null)
  } else {
    router.push('/admin/print-template')
  }
}

function formatJson() {
  try {
    const obj = JSON.parse(jsonRaw.value)
    jsonRaw.value = JSON.stringify(obj, null, 2)
    jsonError.value = null
  } catch (e: any) {
    jsonError.value = 'JSON 解析失败: ' + e.message
  }
}

function resetForm() {
  if (initialJson) {
    jsonRaw.value = initialJson
    isDirty.value = false
    jsonError.value = null
  }
}

function onJsonChange() {
  isDirty.value = (jsonRaw.value !== initialJson)
  // 校验 JSON
  let parsed: any
  try {
    parsed = JSON.parse(jsonRaw.value)
    jsonError.value = null
  } catch (e: any) {
    jsonError.value = e.message
    return  // JSON 错就不预览
  }
  // M3 阶段 3: 同步到 visualBody (避免循环)
  if (!syncingFromJson) {
    syncingFromJson = true
    try {
      const body = (parsed && Array.isArray(parsed.body)) ? parsed.body : []
      // 给每个组件补一个 id (如果没有)
      visualBody.value = body.map((c: any) => c.id ? c : { id: 'restored_' + Math.random().toString(36).slice(2, 8), ...c })
      // 选中态保留或重置
      if (visualSelectedIndex.value >= visualBody.value.length) {
        visualSelectedIndex.value = visualBody.value.length > 0 ? 0 : -1
      }
    } finally {
      syncingFromJson = false
    }
  }
  // 防抖 600ms 后预览
  if (previewTimer) clearTimeout(previewTimer)
  previewTimer = setTimeout(reloadPreview, 600)
}

// ===== M3 阶段 3: 可视化模式操作 =====

/** 从组件库点击 / 拖入: 插入到当前选中之后, 或末尾 */
function onVisualAdd(meta: CompMeta) {
  onVisualAddByComp(cloneComp(meta))
}
function onVisualAddByComp(comp: Record<string, any>) {
  const arr = [...visualBody.value]
  const insertAt = visualSelectedIndex.value >= 0 ? visualSelectedIndex.value + 1 : arr.length
  arr.splice(insertAt, 0, comp)
  visualBody.value = arr
  visualSelectedIndex.value = insertAt
  syncVisualToJson()
}

/** 删除选中 */
function onVisualRemove(index: number) {
  const arr = [...visualBody.value]
  arr.splice(index, 1)
  visualBody.value = arr
  if (visualSelectedIndex.value >= arr.length) {
    visualSelectedIndex.value = arr.length - 1
  }
  syncVisualToJson()
}

/** 上下移动 (dir = -1 上移, +1 下移) */
function onVisualMove(index: number, dir: number) {
  const newIdx = index + dir
  if (newIdx < 0 || newIdx >= visualBody.value.length) return
  const arr = [...visualBody.value]
  const [item] = arr.splice(index, 1)
  arr.splice(newIdx, 0, item)
  visualBody.value = arr
  visualSelectedIndex.value = newIdx
  syncVisualToJson()
}

/** 属性面板修改: 改 component 字段 */
function onVisualUpdate(key: string, value: any) {
  if (visualSelectedIndex.value < 0) return
  const arr = [...visualBody.value]
  const comp = { ...arr[visualSelectedIndex.value], [key]: value }
  arr[visualSelectedIndex.value] = comp
  visualBody.value = arr
  syncVisualToJson()
}

/** 画布变化后 → 同步到 jsonRaw (避免循环) */
function syncVisualToJson() {
  if (syncingFromJson) return
  // 深拷贝, 剔除 id 字段 (保存时不带临时 id)
  const body = visualBody.value.map(c => {
    const { id, ...rest } = c
    return rest
  })
  const obj = { body }
  jsonRaw.value = JSON.stringify(obj, null, 2)
  jsonError.value = null
  isDirty.value = (jsonRaw.value !== initialJson)
  // 防抖 600ms 后预览
  if (previewTimer) clearTimeout(preloadPreview)
}

function onImportSuccess(templateId: number) {
  // 导入成功后跳到编辑模式
  router.replace('/admin/print-template/editor/' + templateId)
}

function preloadPreview() {
  if (previewTimer) clearTimeout(previewTimer)
  previewTimer = setTimeout(reloadPreview, 600)
}

async function loadPreset() {
  try {
    const presets: Record<string, any> = {
      contract: { "body": [
        { "type": "title", "text": "合 同 摘 要", "fontSize": 20, "align": "center" },
        { "type": "text", "text": "合同编号：{{ contract.code }}", "fontSize": 12 },
        { "type": "text", "text": "客户：{{ contract.client.name | default('—') }}", "fontSize": 12 },
        { "type": "text", "text": "金额：{{ contract.amount | money }}", "fontSize": 12, "color": "#DC2626" },
        { "type": "spacer", "height": 6 },
        { "type": "line" },
        { "type": "text", "text": "打印时间：{{ printTime }} | 打印人：{{ printUser }}", "fontSize": 9, "align": "center", "color": "#9CA3AF" }
      ]},
      invoice: { "body": [
        { "type": "title", "text": "发 票 详 情", "fontSize": 20, "align": "center" },
        { "type": "text", "text": "发票号：{{ invoice.invoiceNo }}", "fontSize": 12 },
        { "type": "text", "text": "销方：{{ invoice.sellerName }}", "fontSize": 12 },
        { "type": "text", "text": "购方：{{ invoice.buyerName }}", "fontSize": 12 },
        { "type": "text", "text": "金额（含税）：{{ invoice.totalAmount | money }}", "fontSize": 12, "color": "#DC2626" }
      ]},
      expense: { "body": [
        { "type": "title", "text": "费 用 申 请 单", "fontSize": 20, "align": "center" },
        { "type": "text", "text": "编号：{{ expense.code }}", "fontSize": 12 },
        { "type": "text", "text": "费用名称：{{ expense.title }}", "fontSize": 12 },
        { "type": "text", "text": "申请人：{{ expense.applicant.name | default('—') }}", "fontSize": 12 },
        { "type": "text", "text": "金额：{{ expense.amount | money }}", "fontSize": 12, "color": "#DC2626" }
      ]},
      reimbursement: { "body": [
        { "type": "title", "text": "费 用 报 销 单", "fontSize": 20, "align": "center" },
        { "type": "text", "text": "报销编号：{{ reimbursement.formNo }}", "fontSize": 12 },
        { "type": "text", "text": "申请人：{{ reimbursement.applicant.name | default('—') }}", "fontSize": 12 },
        { "type": "text", "text": "报销金额：{{ reimbursement.totalAmount | money }}", "fontSize": 12, "color": "#DC2626" }
      ]},
    }
    const preset = presets[form.docType]
    if (!preset) {
      ElMessage.warning('该业务类型暂未预置模板')
      return
    }
    jsonRaw.value = JSON.stringify(preset, null, 2)
    onJsonChange()
    ElMessage.success('已加载 ' + form.docType + ' 预置模板')
  } catch (e: any) {
    ElMessage.error('加载预置失败: ' + e.message)
  }
}

async function fetchBusinessOptions() {
  bizLoading.value = true
  try {
    const out: Array<{ label: string; value: number }> = []
    if (form.docType === 'contract') {
      const r: any = await contractApi.list({ page: 1, pageSize: 30 }).catch(() => null)
      const rows = r?.list || r?.data?.list || []
      for (const r of rows) out.push({ label: `${r.code || ''} ${r.name || ''}`.trim() || `#${r.contractId || r.id}`, value: r.contractId || r.id })
    } else if (form.docType === 'invoice') {
      const r: any = await invoiceOcrApi.records({ page: 1, pageSize: 30 }).catch(() => null)
      const rows = r?.list || r?.data?.list || []
      for (const r of rows) out.push({ label: r.invoiceNo || r.sellerName || `#${r.invoiceId || r.id}`, value: r.invoiceId || r.id })
    } else if (form.docType === 'expense') {
      const r: any = await expenseApi.list({ page: 1, pageSize: 30 }).catch(() => null)
      const rows = r?.list || r?.data?.list || []
      for (const r of rows) out.push({ label: r.code || r.title || `#${r.expenseId || r.id}`, value: r.expenseId || r.id })
    } else if (form.docType === 'reimbursement') {
      const r: any = await reimburseApi.list({ page: 1, pageSize: 30 }).catch(() => null)
      const rows = r?.list || r?.data?.list || []
      for (const r of rows) out.push({ label: r.formNo || r.title || `#${r.formId || r.id}`, value: r.formId || r.id })
    }
    previewBusinessOptions.value = out
    if (out.length > 0 && previewBusinessId.value === null) {
      previewBusinessId.value = out[0].value
    }
  } catch (e) {
    console.error(e)
  } finally {
    bizLoading.value = false
  }
}

async function reloadPreview() {
  if (jsonError.value) return
  let schemaObj: any
  try {
    schemaObj = JSON.parse(jsonRaw.value)
  } catch (e: any) {
    return
  }
  previewBusy.value = true
  previewError.value = null
  try {
    const r = await printApi.previewSchema({
      docType: form.docType,
      schemaJson: schemaObj,
      data: previewBusinessId.value !== null ? { _resolver: String(previewBusinessId.value) } : {},
      options: { sourceModule: form.docType, sourceId: previewBusinessId.value !== null ? String(previewBusinessId.value) : undefined },
    })
    previewHtml.value = r.html
    previewElapsed.value = r.elapsedMs
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    let msg = e?.response?.data?.message || e?.message || '渲染失败'
    if (Array.isArray(detail) && detail.length > 0) {
      const d = detail[0]
      msg = `${d.loc?.join('.') || ''}: ${d.msg || ''}`.replace(/^: /, '')
    }
    previewError.value = msg
  } finally {
    previewBusy.value = false
  }
}

async function loadTemplate() {
  if (isNew.value) return
  try {
    const t: any = await printApi.getTemplate(editingId.value).catch(() => null)
    if (!t) {
      ElMessage.error('模板不存在')
      router.push('/admin/print-template')
      return
    }
    form.code = t.code
    form.name = t.name
    form.docType = t.docType
    form.paper = t.paper
    form.orientation = t.orientation
    form.description = t.description || ''
    form.schemaJson = t.schemaJson || { body: [] }
    status.value = t.status
    version.value = t.version
    jsonRaw.value = JSON.stringify(form.schemaJson, null, 2)
    initialJson = jsonRaw.value
    isDirty.value = false
    // M3 阶段 3: 同步到 visualBody
    onJsonChange()
    await fetchBusinessOptions()
    reloadPreview()
  } catch (e: any) {
    ElMessage.error('加载模板失败: ' + e.message)
  }
}

async function save() {
  if (!form.code || !form.name) {
    ElMessage.warning('请填写 code 和 name')
    return
  }
  let schemaObj: any
  try {
    schemaObj = JSON.parse(jsonRaw.value)
  } catch (e: any) {
    ElMessage.error('JSON 解析失败: ' + e.message)
    return
  }
  saving.value = true
  try {
    if (isNew.value) {
      const r: any = await printApi.createTemplate({
        code: form.code,
        name: form.name,
        docType: form.docType,
        paper: form.paper,
        orientation: form.orientation,
        description: form.description,
        schemaJson: schemaObj,
      })
      ElMessage.success('已创建（draft 状态）')
      // 跳到编辑模式
      router.replace('/admin/print-template/editor/' + r.id)
    } else {
      await printApi.updateTemplate(editingId.value, {
        name: form.name,
        paper: form.paper,
        orientation: form.orientation,
        description: form.description,
        schemaJson: schemaObj,
      })
      ElMessage.success('已保存')
      await loadTemplate()
    }
  } catch (e: any) {
    ElMessage.error('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

async function publish() {
  if (isNew.value) return
  try {
    await printApi.publishTemplate(editingId.value)
    ElMessage.success('已发布')
    await loadTemplate()
  } catch (e: any) {
    ElMessage.error('发布失败: ' + e.message)
  }
}

// 监听 docType 变化重新拉业务数据
watch(() => form.docType, () => {
  previewBusinessId.value = null
  previewBusinessOptions.value = []
  if (!isNew.value) fetchBusinessOptions()
})

// 监听业务数据变化重渲染
watch(previewBusinessId, () => {
  reloadPreview()
})

onMounted(async () => {
  if (!isNew.value) {
    await loadTemplate()
  } else {
    initialJson = jsonRaw.value
  }
})
</script>

<style scoped>
.editor-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #F5F7FA;
}
.editor-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 24px; background: #FFFFFF;
  border-bottom: 1px solid #E5E7EB;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-title { font-size: 16px; font-weight: 600; color: #0F172A; }
.header-right { display: flex; gap: 8px; }
.editor-body {
  flex: 1; display: flex; overflow: hidden;
}
.editor-pane {
  display: flex; flex-direction: column;
  background: #FFFFFF;
  border-right: 1px solid #E5E7EB;
  overflow: hidden;
}
.editor-pane-left { width: 340px; flex-shrink: 0; overflow-y: auto; }
.editor-pane-center { flex: 1; min-width: 0; }
.editor-pane-right { width: 42%; flex-shrink: 0; }
.pane-section { padding: 16px; border-bottom: 1px solid #F1F5F9; }
.pane-title { font-size: 13px; font-weight: 600; color: #0F172A; margin: 0 0 12px 0; }
.pane-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; border-bottom: 1px solid #F1F5F9;
  background: #FAFBFC;
}
.toolbar-right { display: flex; align-items: center; gap: 12px; }
.err-flag { color: #DC2626; font-size: 12px; }
.ok-flag { color: #10B981; font-size: 12px; }
.hint p { font-size: 12px; color: #4B5563; line-height: 1.7; margin: 0; }
.hint code { background: #F1F5F9; padding: 1px 6px; border-radius: 4px; font-size: 11px; color: #4F6BFF; margin-right: 4px; }

.json-editor :deep(textarea) {
  font-family: 'SF Mono', Menlo, monospace !important;
  font-size: 13px !important;
  line-height: 1.6 !important;
  border: none !important;
  border-radius: 0 !important;
  background: #1E293B !important;
  color: #E2E8F0 !important;
  padding: 16px !important;
  resize: none !important;
  height: 100% !important;
}
.json-err {
  background: #FEF2F2; color: #DC2626; padding: 8px 16px;
  font-size: 12px; font-family: 'SF Mono', Menlo, monospace;
  border-top: 1px solid #FECACA;
}

.preview-wrap { flex: 1; overflow: auto; background: #F5F7FA; }
.preview-iframe { width: 100%; height: 100%; min-height: 600px; border: none; background: #FFFFFF; }
.preview-empty {
  height: 100%; min-height: 600px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: #6B7280; font-size: 13px; gap: 8px;
}
.preview-empty .muted { color: #9CA3AF; font-size: 12px; }
.preview-error { padding: 16px; }
/* M3 阶段 3: 可视化编辑器样式 */
.editor-tabs { height: 100%; }
.editor-tabs :deep(.el-tabs__nav-wrap) { padding: 0 12px; background: #FAFBFC; }
.editor-tabs :deep(.el-tabs__header) { margin-bottom: 0; background: #FAFBFC; border-bottom: 1px solid #E5E7EB; }
.editor-tabs :deep(.el-tabs__content) { height: calc(100% - 41px); padding: 0; }
.editor-tabs :deep(.el-tab-pane) { height: 100%; }
.visual-layout {
  display: flex; height: 100%; min-height: 0;
  gap: 0;
}
.visual-main {
  flex: 1; display: flex; flex-direction: column; min-width: 0; min-height: 0;
  padding: 12px; gap: 8px; overflow: hidden;
}
</style>
