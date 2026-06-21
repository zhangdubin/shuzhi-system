<script setup lang="ts">
/**
 * InvoiceTemplateEdit · 发票模板编辑（真实可用）
 * - 三栏布局：左字段库 / 中画布 / 右属性面板
 * - 拖拽 + 点击添加、画布字段选中、× 移除
 * - 保存草稿 / 发布模板 真实调 save API
 */
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { invoiceTemplateApi } from '@/api/modules'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const saving = ref(false)
const activeView = ref<'desktop' | 'mobile'>('desktop')
const previewVisible = ref(false)
const previewView = ref<'desktop' | 'mobile'>('desktop')

// 模板 ID
const templateId = computed(() => Number(route.params.id || 0))

// 模板基础信息
const form = reactive({
  templateId: 0 as number,
  code: '',
  name: '标准销售发票模板 v2.1',
  description: '适用于一次性销售，含服务内容、付款、保密等 8 项标准条款',
  category: '差旅',
  defaultTaxRate: 6,
  icon: '📄',
  iconColors: '#4F6BFF,#7C3AED',
})

// 字段库（来自后端 field-library）
interface LibField {
  icon: string
  label: string
  key: string
  type: string
  refType?: string
}
const libGroups = ref<Array<{ name: string; items: LibField[] }>>([])

// 画布字段（每段为一组）
interface CanvasField {
  uiKey: string                 // 前端唯一 key
  label: string
  key: string
  type: string
  required: boolean
  ai: boolean
  defaultValue?: any
  refType?: string
  options?: any
  full?: boolean                // 跨整行
  group: 'base' | 'amount' | 'business' | 'extra'   // 自动归类
}
const canvasSections = reactive<Array<{ title: string; group: CanvasField['group']; fields: CanvasField[] }>>([
  { title: '📌 票面信息（OCR 自动识别）', group: 'base',     fields: [] },
  { title: '💰 金额信息',                group: 'amount',   fields: [] },
  { title: '📋 业务信息（人工填写）',    group: 'business', fields: [] },
  { title: '📝 附加信息',                group: 'extra',    fields: [] },
])

// 当前选中
const selectedKey = ref<string | null>(null)
const selectedField = computed<CanvasField | null>(() => {
  if (!selectedKey.value) return null
  for (const s of canvasSections) {
    const f = s.fields.find(x => x.uiKey === selectedKey.value)
    if (f) return f
  }
  return null
})
const selectedSection = computed(() => {
  if (!selectedKey.value) return null
  for (const s of canvasSections) {
    if (s.fields.find(x => x.uiKey === selectedKey.value)) return s
  }
  return null
})

// AI 开关
const aiFieldEnabled = ref(false)
watch(selectedField, (f) => { aiFieldEnabled.value = !!(f && f.ai) })

const fieldCount = computed(() =>
  canvasSections.reduce((s, sec) => s + sec.fields.length, 0)
)

// 字段归类规则
function groupFor(type: string, key: string): CanvasField['group'] {
  if (['invoiceType', 'invoiceCode', 'invoiceNo', 'issueDate', 'sellerName', 'sellerTaxNo', 'buyerName', 'buyerTaxNo'].includes(key)) return 'base'
  if (['totalAmount', 'taxRate', 'taxAmount', 'amountExclTax'].includes(key) || type === 'amount' || type === 'rate') return 'amount'
  if (type === 'textarea') return 'extra'
  return 'business'
}

let _uiSeq = 0
function nextUiKey() { return `ui_${Date.now()}_${++_uiSeq}` }

// ========== 数据加载 ==========
async function loadDetail() {
  if (!templateId.value) return
  loading.value = true
  try {
    const res: any = await invoiceTemplateApi.detail(templateId.value)
    const d = res?.data || res
    if (!d || (!d.templateId && !d.id)) {
      ElMessage.error('模板不存在')
      return
    }
    form.templateId = d.templateId || d.id
    form.code = d.code || ''
    form.name = d.name || ''
    form.description = d.description || ''
    form.category = d.category || ''
    form.defaultTaxRate = Number(d.defaultTaxRate || 0)

    // 清空画布
    canvasSections.forEach(s => s.fields = [])

    // 字段映射
    const fields: CanvasField[] = (d.fields || []).map((f: any) => ({
      uiKey: nextUiKey(),
      label: f.label,
      key: f.key,
      type: f.type,
      required: !!f.required,
      ai: !!(f.aiSupport || f.aiExtractEnabled),
      defaultValue: f.defaultValue ?? null,
      refType: f.refType || undefined,
      options: f.options || undefined,
      full: ['remark', 'note'].includes(f.key) || f.type === 'textarea',
      group: groupFor(f.type, f.key),
    }))
    fields.forEach(f => {
      const sec = canvasSections.find(s => s.group === f.group) || canvasSections[2]
      sec.fields.push(f)
    })
    if (fields.length === 0) seedMockFields()
    ElMessage.success('已加载模板')
  } catch (e: any) {
    console.error(e)
    ElMessage.error(e?.message || '加载失败')
    seedMockFields()
  } finally {
    loading.value = false
  }
}

function seedMockFields() {
  // 新建时给一组示例
  const samples: Array<Omit<CanvasField, 'uiKey' | 'group'>> = [
    { label: '发票类型', key: 'invoiceType', type: 'text', required: true, ai: true },
    { label: '发票代码', key: 'invoiceCode', type: 'text', required: true, ai: true },
    { label: '发票号码', key: 'invoiceNo',   type: 'text', required: true, ai: true },
    { label: '开票日期', key: 'issueDate',   type: 'date', required: true, ai: true },
    { label: '销售方',   key: 'sellerName',  type: 'text', required: true, ai: true },
    { label: '购买方',   key: 'buyerName',   type: 'text', required: true, ai: true },
    { label: '价税合计', key: 'totalAmount', type: 'amount', required: true, ai: true },
    { label: '税率',     key: 'taxRate',     type: 'rate', required: false, ai: false },
    { label: '税额',     key: 'taxAmount',   type: 'amount', required: false, ai: false },
    { label: '不含税金额', key: 'amountExclTax', type: 'amount', required: false, ai: false },
    { label: '报销人',   key: 'reimburserId', type: 'user', required: true, ai: false },
    { label: '部门',     key: 'departmentId', type: 'text', required: false, ai: false },
    { label: '关联合同', key: 'contractId',  type: 'ref', refType: 'contract', required: false, ai: false },
    { label: '关联项目', key: 'projectId',   type: 'ref', refType: 'project', required: false, ai: false },
    { label: '成本中心', key: 'costCenter',  type: 'ref', refType: 'costCenter', required: false, ai: false },
    { label: '费用类型', key: 'expenseType', type: 'text', required: false, ai: false },
    { label: '备注',     key: 'remark',      type: 'textarea', required: false, ai: false, full: true },
  ]
  samples.forEach(s => {
    const f: CanvasField = { ...s, uiKey: nextUiKey(), group: groupFor(s.type, s.key) }
    const sec = canvasSections.find(x => x.group === f.group) || canvasSections[2]
    sec.fields.push(f)
  })
}

async function loadFieldLibrary() {
  try {
    const res: any = await invoiceTemplateApi.fieldLibrary()
    const groups = res?.data?.groups || res?.groups || []
    if (groups.length === 0) {
      seedFieldLibrary()
      return
    }
    libGroups.value = groups.map((g: any) => ({
      name: g.name,
      items: (g.fields || []).map((f: any) => ({
        icon: f.icon || '📄',
        label: f.label,
        key: f.key,
        type: f.type,
        refType: f.refType,
      })),
    }))
  } catch {
    seedFieldLibrary()
  }
}

function seedFieldLibrary() {
  libGroups.value = [
    { name: '基础信息', items: [
      { icon: '📄', label: '发票类型', key: 'invoiceType', type: 'text' },
      { icon: '🔢', label: '发票代码', key: 'invoiceCode', type: 'text' },
      { icon: '#',  label: '发票号码', key: 'invoiceNo',   type: 'text' },
      { icon: '📅', label: '开票日期', key: 'issueDate',   type: 'date' },
      { icon: '💼', label: '销售方名称', key: 'sellerName', type: 'text' },
      { icon: '🪪', label: '纳税人识别号', key: 'sellerTaxNo', type: 'text' },
    ]},
    { name: '金额信息', items: [
      { icon: '💰', label: '价税合计', key: 'totalAmount', type: 'amount' },
      { icon: '%',  label: '税率', key: 'taxRate', type: 'rate' },
      { icon: '¥',  label: '税额', key: 'taxAmount', type: 'amount' },
      { icon: '💵', label: '不含税金额', key: 'amountExclTax', type: 'amount' },
    ]},
    { name: '业务字段', items: [
      { icon: '👤', label: '报销人', key: 'reimburserId', type: 'user' },
      { icon: '🏢', label: '部门', key: 'departmentId', type: 'text' },
      { icon: '📂', label: '关联合同', key: 'contractId', type: 'ref', refType: 'contract' },
      { icon: '📂', label: '关联项目', key: 'projectId', type: 'ref', refType: 'project' },
      { icon: '📂', label: '成本中心', key: 'costCenter', type: 'ref', refType: 'costCenter' },
      { icon: '📝', label: '备注', key: 'remark', type: 'textarea' },
    ]},
  ]
}

// ========== 画布交互 ==========
function selectField(key: string) {
  selectedKey.value = key
}

function addField(item: LibField) {
  // 同 key 防重复
  for (const s of canvasSections) {
    if (s.fields.some(f => f.key === item.key)) {
      ElMessage.warning(`字段「${item.label}」已在画布中`)
      selectField(canvasSections.find(s => s.fields.some(f => f.key === item.key))!.fields.find(f => f.key === item.key)!.uiKey)
      return
    }
  }
  const group = groupFor(item.type, item.key)
  const sec = canvasSections.find(s => s.group === group) || canvasSections[2]
  const f: CanvasField = {
    uiKey: nextUiKey(),
    label: item.label,
    key: item.key,
    type: item.type,
    refType: item.refType,
    required: false,
    ai: ['invoiceType', 'invoiceCode', 'invoiceNo', 'issueDate', 'sellerName', 'buyerName', 'totalAmount'].includes(item.key),
    full: item.type === 'textarea',
    group,
  }
  sec.fields.push(f)
  selectedKey.value = f.uiKey
  ElMessage.success(`已添加字段：${item.label}`)
}

function removeField(section: typeof canvasSections[number], f: CanvasField) {
  section.fields = section.fields.filter(x => x.uiKey !== f.uiKey)
  if (selectedKey.value === f.uiKey) selectedKey.value = null
  ElMessage.success(`已移除字段：${f.label}`)
}

function onDragStart(e: DragEvent, item: LibField) {
  e.dataTransfer?.setData('text/plain', JSON.stringify(item))
  e.dataTransfer!.effectAllowed = 'copy'
}
function onDragOver(e: DragEvent) {
  e.preventDefault()
  e.dataTransfer!.dropEffect = 'copy'
}
function onDrop(e: DragEvent, section: typeof canvasSections[number]) {
  e.preventDefault()
  const raw = e.dataTransfer?.getData('text/plain')
  if (!raw) return
  try {
    const item = JSON.parse(raw) as LibField
    addFieldToSection(item, section)
  } catch {}
}
function addFieldToSection(item: LibField, section: typeof canvasSections[number]) {
  for (const s of canvasSections) {
    if (s.fields.some(f => f.key === item.key)) {
      ElMessage.warning(`字段「${item.label}」已在画布中`)
      return
    }
  }
  const f: CanvasField = {
    uiKey: nextUiKey(),
    label: item.label,
    key: item.key,
    type: item.type,
    refType: item.refType,
    required: false,
    ai: ['invoiceType', 'invoiceCode', 'invoiceNo', 'issueDate', 'sellerName', 'buyerName', 'totalAmount'].includes(item.key),
    full: item.type === 'textarea',
    group: section.group,
  }
  section.fields.push(f)
  selectedKey.value = f.uiKey
  ElMessage.success(`已添加到「${section.title.replace(/^[^一-龥]+/, '')}」`)
}

// ========== 属性面板 ==========
function updateSelected(patch: Partial<CanvasField>) {
  if (!selectedField.value) return
  Object.assign(selectedField.value, patch)
  if (patch.ai !== undefined) aiFieldEnabled.value = !!patch.ai
}

function onAiFieldToggle(val: string | number | boolean) {
  if (!selectedField.value) return
  selectedField.value.ai = !!val
  if (val) ElMessage.success(`✨ 已为「${selectedField.value.label}」开启 AI 自动识别`)
  else ElMessage.info('已关闭 AI 自动识别')
}

function sampleValue(f: CanvasField): string {
  const map: Record<string, string> = {
    invoiceType: '增值税电子普通发票',
    invoiceCode: '011002600611',
    invoiceNo: '25113300000012345678',
    issueDate: '2026-06-08',
    sellerName: '上海数智信息技术有限公司',
    sellerTaxNo: '91310000XXXXXXXXXX',
    buyerName: '万象科技有限公司',
    buyerTaxNo: '91110000XXXXXXXXXX',
    totalAmount: '¥ 28,000.00',
    taxRate: '6%',
    taxAmount: '¥ 1,584.91',
    amountExclTax: '¥ 26,415.09',
    reimburserId: '陈思琪',
    departmentId: '销售部',
    contractId: 'HT-2026-028',
    projectId: 'PRJ-2026-018',
    costCenter: 'CC-2026-008',
    expenseType: '差旅',
    remark: '第二季度服务费尾款...',
  }
  return map[f.key] || f.defaultValue || '—'
}

const typeLabelMap: Record<string, string> = {
  text: '文本', date: '日期', amount: '金额', rate: '百分比',
  user: '用户选择器', ref: '关联引用', textarea: '多行文本',
}

function moveFieldTo(group: CanvasField['group']) {
  if (!selectedField.value || !selectedSection.value) return
  if (selectedSection.value.group === group) return
  const target = canvasSections.find(sec => sec.group === group)
  if (!target) return
  const f = selectedField.value
  selectedSection.value.fields = selectedSection.value.fields.filter(x => x.uiKey !== f.uiKey)
  f.group = group
  target.fields.push(f)
  ElMessage.success(`已移动到「${target.title.replace(/^[^一-龥]+/, '')}」`)
}

// ========== 顶部操作 ==========
function selectView(v: 'desktop' | 'mobile') { activeView.value = v }

function buildSavePayload() {
  const allFields = canvasSections.flatMap(s => s.fields)
  return {
    name: form.name,
    category: form.category,
    description: form.description,
    defaultTaxRate: form.defaultTaxRate,
    icon: form.icon,
    iconColors: form.iconColors,
    fields: allFields.map((f, i) => ({
      label: f.label, key: f.key, type: f.type,
      required: f.required, aiSupport: f.ai,
      defaultValue: f.defaultValue ?? null,
      linkedField: null, refType: f.refType || null,
      options: f.options || null,
    })),
  }
}

async function saveDraft() {
  if (!form.name?.trim()) { ElMessage.warning('请填写模板名称'); return }
  saving.value = true
  try {
    const payload: any = buildSavePayload()
    if (form.templateId) payload.templateId = form.templateId
    const res: any = await invoiceTemplateApi.create(payload)
    const d = res?.data || res
    if (d && (d.templateId || d.id)) {
      form.templateId = d.templateId || d.id
      form.code = d.code || form.code
    }
    ElMessage.success(res?.message || '草稿已保存')
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function publishTemplate() {
  if (!form.name?.trim()) { ElMessage.warning('请填写模板名称'); return }
  if (fieldCount.value === 0) { ElMessage.warning('画布为空，请先添加字段'); return }
  saving.value = true
  try {
    const payload: any = buildSavePayload()
    if (form.templateId) payload.templateId = form.templateId
    const res: any = await invoiceTemplateApi.create(payload)
    const d = res?.data || res
    if (d && (d.templateId || d.id)) {
      form.templateId = d.templateId || d.id
    }
    ElMessage.success(res?.message || '模板已发布')
    setTimeout(() => router.push(`/invoice/template/${form.templateId}`), 600)
  } catch (e: any) {
    ElMessage.error(e?.message || '发布失败')
  } finally {
    saving.value = false
  }
}

function cancelEdit() {
  router.push(form.templateId ? `/invoice/template/${form.templateId}` : '/invoice/template')
}

function previewTemplate() { previewVisible.value = true }

onMounted(async () => {
  await loadFieldLibrary()
  await loadDetail()
})
</script>

<template>
  <div class="page-container" v-loading="loading">
    <div class="page-header">
      <div>
        <div class="breadcrumb">
          <a @click="router.push('/invoice/template')">财务</a>
          <span class="sep">/</span>
          <a @click="router.push('/invoice/template')">发票模板</a>
          <span class="sep">/</span>
          <span class="current">{{ form.templateId ? '编辑模板' : '新建模板' }}</span>
        </div>
        <h1>✎ {{ form.templateId ? '编辑模板：' : '新建模板：' }}{{ form.name || '未命名' }}</h1>
        <p class="page-desc">{{ form.description || '请填写描述' }} · 共 {{ fieldCount }} 个字段</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-ghost btn-sm" @click="cancelEdit">← 返回</button>
        <button class="btn btn-outline btn-sm" :disabled="saving" @click="saveDraft">💾 保存草稿</button>
        <button class="btn btn-primary btn-sm" :disabled="saving" @click="publishTemplate">⚡ 发布模板</button>
      </div>
    </div>

    <!-- 基础信息条 -->
    <div class="meta-bar">
      <div class="meta-item">
        <label>模板名称</label>
        <el-input v-model="form.name" size="default" placeholder="如：标准销售发票模板" maxlength="60" show-word-limit />
      </div>
      <div class="meta-item">
        <label>分类</label>
        <el-input v-model="form.category" size="default" placeholder="如：差旅" maxlength="20" />
      </div>
      <div class="meta-item meta-desc">
        <label>描述</label>
        <el-input v-model="form.description" type="textarea" :rows="2" placeholder="适用场景简述" maxlength="200" show-word-limit />
      </div>
    </div>

    <!-- tip-box -->
    <div class="tip-box">
      <div class="ico">ⓘ</div>
      <div>
        <strong>设计器：</strong>
        从左侧字段库<strong>拖拽</strong>字段到画布任一区域，或<strong>点击</strong>字段库中的字段直接添加到默认区域。点击画布中已有字段可编辑属性，点击 × 移除。带 <span class="ai-mini">AI</span> 标签的字段将由 OCR 自动填充。
      </div>
    </div>

    <!-- 三栏 -->
    <div class="tpl-edit-grid">
      <!-- 左：字段库 -->
      <div class="lib">
        <div class="lib-head">
          <h3>🧩 字段库</h3>
          <span class="count">{{ libGroups.reduce((s, g) => s + g.items.length, 0) }} 个字段</span>
        </div>
        <div class="lib-body">
          <div v-for="(g, gi) in libGroups" :key="gi" class="lib-group">
            <div class="g">{{ g.name }}</div>
            <div
              v-for="(it, ii) in g.items"
              :key="ii"
              class="lib-item"
              draggable="true"
              @dragstart="onDragStart($event, it)"
              @click="addField(it)"
              title="拖拽到画布或点击添加"
            >
              <span class="ico">{{ it.icon }}</span>
              <span class="lbl">{{ it.label }}</span>
              <span class="type">{{ it.type }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 中：画布 -->
      <div class="canvas">
        <div class="canvas-head">
          <h3>画布预览</h3>
          <div class="view-toggle">
            <button :class="['toggle', { active: activeView === 'mobile' }]" @click="selectView('mobile')">📱 移动端</button>
            <button :class="['toggle', { active: activeView === 'desktop' }]" @click="selectView('desktop')">🖥 桌面</button>
          </div>
        </div>
        <div class="canvas-body" :class="activeView">
          <div class="tpl-canvas">
            <div
              v-for="(sec, si) in canvasSections"
              :key="si"
              class="canvas-section"
              @dragover="onDragOver"
              @drop="onDrop($event, sec)"
            >
              <div class="tpl-section-title">{{ sec.title }}</div>
              <div class="tpl-row">
                <div
                  v-for="f in sec.fields"
                  :key="f.uiKey"
                  :class="['tpl-field', { required: f.required, full: f.full, active: selectedKey === f.uiKey }]"
                  @click.stop="selectField(f.uiKey)"
                >
                  <span class="l">{{ f.label }}<span v-if="f.required" class="req">*</span></span>
                  <span class="v">{{ sampleValue(f) }}</span>
                  <span v-if="f.ai" class="ai-tag">AI</span>
                  <button class="del" @click.stop="removeField(sec, f)">×</button>
                </div>
                <div v-if="sec.fields.length === 0" class="tpl-empty">+ 拖拽字段到此处</div>
              </div>
            </div>
          </div>
          <div class="canvas-hint">提示：拖拽字段到任意区域，或点击字段库中的字段直接添加</div>
        </div>
      </div>

      <!-- 右：属性面板 -->
      <div class="props">
        <div class="props-head">
          <h4>⚙️ 当前选中：{{ selectedField ? selectedField.label : '未选中' }}</h4>
        </div>
        <div class="props-body">
          <template v-if="selectedField">
            <div class="props-section">
              <div class="t">基础属性</div>
              <div class="props-row form-row">
                <span class="l">字段名</span>
                <el-input v-model="selectedField.label" size="small" maxlength="20" />
              </div>
              <div class="props-row form-row">
                <span class="l">字段标识</span>
                <el-input v-model="selectedField.key" size="small" placeholder="英文字段 key" />
              </div>
              <div class="props-row form-row">
                <span class="l">字段类型</span>
                <el-select v-model="selectedField.type" size="small" style="flex:1; width: 100%">
                  <el-option label="文本" value="text" />
                  <el-option label="日期" value="date" />
                  <el-option label="金额" value="amount" />
                  <el-option label="百分比" value="rate" />
                  <el-option label="用户选择器" value="user" />
                  <el-option label="关联引用" value="ref" />
                  <el-option label="多行文本" value="textarea" />
                </el-select>
              </div>
            </div>
            <div class="props-section">
              <div class="t">验证规则</div>
              <div class="props-row form-row">
                <span class="l">是否必填</span>
                <el-switch v-model="selectedField.required" />
              </div>
              <div class="props-row form-row">
                <span class="l">占满整行</span>
                <el-switch v-model="selectedField.full" />
              </div>
              <div class="props-row form-row ai-row">
                <span class="l">AI 自动识别</span>
                <el-switch v-model="aiFieldEnabled" inline-prompt active-text="开" inactive-text="关" @change="onAiFieldToggle" />
              </div>
              <transition name="ai-field-fade">
                <div v-if="aiFieldEnabled" class="ai-field-hint">
                  <span class="ai-field-icon">✨</span>
                  <span>AI 将自动识别 <strong>{{ selectedField.label }}</strong>，置信度 ≥ 80% 时自动填入，&lt; 80% 时提醒人工复核</span>
                </div>
              </transition>
            </div>
            <div class="props-section">
              <div class="t">位置</div>
              <div class="props-row">
                <span class="l">所在区域</span>
                <span class="v">{{ selectedSection?.title }}</span>
              </div>
              <div class="props-row form-row">
                <span class="l">移动到</span>
                <el-select
                  :model-value="selectedSection?.group"
                  size="small"
                  style="flex:1; width: 100%"
                  @change="(g: any) => moveFieldTo(g)"
                >
                  <el-option label="票面信息" value="base" />
                  <el-option label="金额信息" value="amount" />
                  <el-option label="业务信息" value="business" />
                  <el-option label="附加信息" value="extra" />
                </el-select>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="props-empty">
              <div class="eico">👆</div>
              <p>点击画布中任一字段<br/>在此编辑属性</p>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 底部操作条 -->
    <div class="form-foot">
      <div>
        <button class="btn btn-ghost btn-sm" :disabled="saving" @click="saveDraft">💾 保存草稿</button>
        <button class="btn btn-outline btn-sm" @click="cancelEdit">取消</button>
      </div>
      <div>
        <button class="btn btn-outline btn-sm" :disabled="fieldCount === 0" @click="previewTemplate">👁 预览</button>
        <button class="btn btn-primary btn-sm" :disabled="saving" @click="publishTemplate">⚡ 发布模板</button>
      </div>
    </div>
  </div>

  <!-- 预览抽屉 -->
  <el-drawer
    v-model="previewVisible"
    title="👁 模板预览"
    direction="rtl"
    size="520px"
  >
    <div class="prev-toolbar">
      <span class="prev-label">预览视图：</span>
      <div class="view-toggle">
        <button :class="['toggle', { active: previewView === 'mobile' }]" @click="previewView = 'mobile'">📱 移动端</button>
        <button :class="['toggle', { active: previewView === 'desktop' }]" @click="previewView = 'desktop'">🖥 桌面</button>
      </div>
    </div>
    <div class="prev-body" :class="previewView">
      <div class="prev-form">
        <div v-for="(sec, si) in canvasSections" :key="si">
          <div v-if="sec.fields.length" class="prev-section">
            <div class="prev-section-title">{{ sec.title }}</div>
            <div class="prev-fields">
              <div
                v-for="f in sec.fields"
                :key="f.uiKey"
                :class="['prev-field', { full: f.full, required: f.required }]"
              >
                <label class="prev-label">{{ f.label }}<span v-if="f.required" class="req">*</span></label>
                <div class="prev-value">
                  <span class="prev-placeholder">请填写{{ f.label }}</span>
                </div>
                <span v-if="f.ai" class="ai-badge">AI</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="prev-footer">
      <el-button @click="previewVisible = false">关闭</el-button>
      <el-button type="primary" :loading="saving" @click="publishTemplate">⚡ 发布模板</el-button>
    </div>
  </el-drawer>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables.scss" as *;
@use "@/assets/styles/mixins.scss" as *;

.page-header h1 { @include page-title-h1; margin: 0; }
.page-header .page-desc { color: $color-text-secondary; font-size: 13px; margin: 4px 0 0 0; }
.page-header .breadcrumb { font-size: 12px; color: $color-text-tertiary; margin-bottom: 4px; a { cursor: pointer; } a:hover { color: $color-primary; } .sep { margin: 0 6px; opacity: 0.5; } .current { color: $color-text-secondary; } }
.page-header .page-actions { display: flex; gap: 8px; }

.meta-bar {
  display: grid; grid-template-columns: 1fr 200px; gap: 12px;
  background: #fff; border: 1px solid $color-border; border-radius: $radius-lg;
  padding: 14px 16px; margin-bottom: 12px;
  .meta-item { display: flex; flex-direction: column; gap: 6px; }
  .meta-item label { font-size: 12px; color: $color-text-tertiary; font-weight: 500; }
  .meta-desc { grid-column: 1 / -1; }
}

.tip-box {
  display: flex; gap: 10px;
  padding: 12px 14px;
  background: rgba(79,107,255,0.05);
  border: 1px solid rgba(79,107,255,0.2);
  border-radius: $radius-md;
  font-size: 12.5px; color: $color-text-secondary; line-height: 1.6;
  margin-bottom: 16px;
  .ico { color: $color-primary; font-size: 16px; flex-shrink: 0; }
  strong { color: $color-text-primary; }
  .ai-mini {
    display: inline-block; padding: 0 4px;
    background: $gradient-brand; color: #fff;
    border-radius: 3px; font-size: 9.5px; font-weight: 600; letter-spacing: 0.3px;
  }
}

.tpl-edit-grid {
  display: grid;
  grid-template-columns: 240px 1fr 280px;
  gap: 12px; align-items: start; margin-bottom: 16px;
  @media (max-width: 1100px) { grid-template-columns: 200px 1fr; .props { display: none; } }
  @media (max-width: 800px)  { grid-template-columns: 1fr; }
}

.lib {
  background: #fff; border: 1px solid $color-border;
  border-radius: $radius-lg; overflow: hidden;
  position: sticky; top: 16px;
}
.lib-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; border-bottom: 1px solid $color-border; background: #FAFBFF;
  h3 { font-size: 13.5px; font-weight: 600; margin: 0; }
  .count { font-size: 11px; color: $color-text-tertiary; }
}
.lib-body { padding: 8px; max-height: 700px; overflow-y: auto; }
.lib-group { margin-bottom: 12px; }
.lib-group .g {
  font-size: 11px; color: $color-text-tertiary; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.5px; padding: 6px 8px;
}
.lib-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: $radius-sm;
  cursor: grab; font-size: 12.5px; transition: all 0.15s;
  user-select: none;
  .ico { font-size: 14px; flex-shrink: 0; }
  .lbl { flex: 1; min-width: 0; color: $color-text-primary; }
  .type {
    font-family: $font-family-mono; font-size: 10px;
    color: $color-text-tertiary; background: $color-bg;
    padding: 1px 4px; border-radius: 3px;
  }
  &:hover { background: $color-primary-bg; .lbl { color: $color-primary; } }
  &:active { cursor: grabbing; }
}

.canvas {
  background: #fff; border: 1px solid $color-border;
  border-radius: $radius-lg; overflow: hidden;
}
.canvas-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 20px; border-bottom: 1px solid $color-border; background: #FAFBFF;
  h3 { font-size: 14px; font-weight: 600; margin: 0; }
}
.view-toggle { display: flex; gap: 4px; background: $color-bg; border-radius: $radius-md; padding: 2px; }
.toggle {
  padding: 5px 12px; border-radius: $radius-sm;
  font-size: 12px; color: $color-text-secondary;
  background: transparent; border: none; cursor: pointer;
  &.active { background: #fff; color: $color-primary; box-shadow: $shadow-sm; }
  &:hover:not(.active) { color: $color-text-primary; }
}
.canvas-body { padding: 20px; &.mobile { max-width: 375px; margin: 0 auto; } }
.canvas-section { margin-bottom: 16px; min-height: 60px; }
.tpl-canvas {
  background: #FCFCFD; border: 1px dashed $color-border-strong;
  border-radius: $radius-md; padding: 16px;
}
.tpl-section-title {
  font-size: 12.5px; font-weight: 600; color: $color-text-primary;
  margin-bottom: 8px; padding: 4px 0;
}
.tpl-row {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
  @media (max-width: 700px) { grid-template-columns: 1fr; }
}
.tpl-field {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; background: #fff;
  border: 1.5px solid $color-border; border-radius: $radius-sm;
  position: relative; cursor: pointer; transition: all 0.15s;
  &.required { border-color: rgba(79,107,255,0.3); }
  &.required::after {
    content: '*'; position: absolute; top: 4px; right: 4px;
    color: $color-danger; font-size: 10px;
  }
  &.full { grid-column: 1 / -1; }
  &.active { border-color: $color-primary; box-shadow: 0 0 0 3px rgba(79,107,255,0.15); }
  &:hover { border-color: $color-primary; }
  .l {
    font-size: 12px; color: $color-text-tertiary; flex-shrink: 0;
    .req { color: $color-danger; margin-left: 2px; }
  }
  .v {
    font-size: 12.5px; color: $color-text-primary; font-weight: 500; flex: 1;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .ai-tag {
    display: inline-block; padding: 1px 6px;
    background: $gradient-brand; color: #fff;
    border-radius: 9999px; font-size: 9.5px; font-weight: 600; letter-spacing: 0.3px;
    flex-shrink: 0;
  }
  .del {
    width: 22px; height: 22px; border-radius: 50%;
    color: $color-text-tertiary; background: transparent;
    border: none; cursor: pointer; font-size: 14px; flex-shrink: 0;
    &:hover { background: $color-danger-bg; color: $color-danger; }
  }
}
.tpl-empty {
  grid-column: 1 / -1;
  padding: 16px; text-align: center; color: #CBD5E1;
  border: 1.5px dashed #E2E8F0; border-radius: $radius-sm; font-size: 12px;
}
.canvas-hint { text-align: center; margin-top: 12px; font-size: 12px; color: $color-text-tertiary; }

.props {
  background: #fff; border: 1px solid $color-border;
  border-radius: $radius-lg; overflow: hidden;
  position: sticky; top: 16px;
}
.props-head {
  padding: 12px 16px; border-bottom: 1px solid $color-border; background: #FAFBFF;
  h4 { font-size: 13.5px; font-weight: 600; margin: 0; }
}
.props-body { padding: 12px 16px; }
.props-section {
  margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid $color-border;
  &:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
  .t { font-size: 11.5px; color: $color-text-tertiary; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
}
.props-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 5px 0; font-size: 12.5px;
  .l { color: $color-text-tertiary; }
  .v { color: $color-text-primary; font-weight: 500; text-align: right; }
  &.form-row { gap: 8px; }
}
.props-row.ai-row {
  background: linear-gradient(90deg, rgba(124,58,237,0.04), transparent);
  border-left: 2px solid #7C3AED; padding-left: 10px; margin-left: -10px;
}
.props-empty {
  text-align: center; padding: 40px 20px; color: $color-text-tertiary;
  .eico { font-size: 36px; margin-bottom: 8px; opacity: 0.6; }
  p { font-size: 12.5px; line-height: 1.7; margin: 0; }
}
.ai-field-hint {
  display: flex; gap: 6px; align-items: flex-start;
  margin-top: 8px; padding: 8px 10px;
  background: linear-gradient(135deg, rgba(79,107,255,0.04) 0%, rgba(124,58,237,0.04) 100%);
  border-radius: $radius-sm; font-size: 11px;
  color: $color-text-secondary; line-height: 1.5;
  .ai-field-icon { font-size: 14px; flex-shrink: 0; }
  strong { color: $color-primary; }
}
.ai-field-fade-enter-active, .ai-field-fade-leave-active { transition: all 0.3s; }
.ai-field-fade-enter-from, .ai-field-fade-leave-to { opacity: 0; transform: translateY(-4px); }

.form-foot {
  position: sticky; bottom: 0; background: #fff;
  border-top: 1px solid $color-border; padding: 14px 0;
  display: flex; justify-content: space-between; align-items: center;
  z-index: 10; box-shadow: 0 -2px 8px rgba(15, 23, 42, 0.04);
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
}

.prev-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding-bottom: 14px; border-bottom: 1px solid $color-border; }
.prev-label { font-size: 12.5px; color: $color-text-secondary; font-weight: 500; }
.prev-body { padding: 4px; &.mobile { .prev-form { max-width: 375px; margin: 0 auto; } } }
.prev-form { background: #FCFCFD; border: 1.5px dashed $color-border-strong; border-radius: $radius-md; padding: 16px; }
.prev-section { margin-bottom: 16px; &:last-child { margin-bottom: 0; } }
.prev-section-title { font-size: 12.5px; font-weight: 600; color: $color-text-primary; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid $color-border; }
.prev-fields { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; @media (max-width: 480px) { grid-template-columns: 1fr; } }
.prev-field {
  display: flex; flex-direction: column; gap: 5px; padding: 8px 10px;
  background: #fff; border: 1px solid $color-border; border-radius: $radius-sm; position: relative;
  &.required { border-color: rgba(79,107,255,0.3); }
  &.full { grid-column: 1 / -1; }
}
.prev-label { font-size: 11.5px; color: $color-text-tertiary; .req { color: $color-danger; margin-left: 2px; } }
.prev-value { display: flex; align-items: center; min-height: 20px; }
.prev-placeholder { font-size: 12px; color: #CBD5E1; font-style: italic; }
.ai-badge { display: inline-block; width: fit-content; font-size: 9.5px; padding: 1px 5px; background: $gradient-brand; color: #fff; border-radius: 9999px; font-weight: 600; letter-spacing: 0.3px; margin-top: 2px; }
.prev-footer { display: flex; justify-content: flex-end; gap: 10px; padding-top: 16px; margin-top: 16px; border-top: 1px solid $color-border; }
</style>
