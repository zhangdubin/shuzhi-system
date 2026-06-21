<script setup lang="ts">
/**
 * 报销模板管理
 * - 内置 4 个不可改/删，可复制
 * - 自定义可新建 / 编辑 / 删除 / 上传识别 / 复制内置
 */
import { ref, computed, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reimburseApi } from '@/api/modules'

const loading = ref(false)
const templates = ref<any[]>([])

const builtinList = computed(() => templates.value.filter((t) => t.isSystem))
const customList  = computed(() => templates.value.filter((t) => !t.isSystem))

async function load() {
  loading.value = true
  try {
    const r: any = await reimburseApi.templates()
    templates.value = Array.isArray(r) ? r : (r?.data || [])
  } catch (e: any) {
    ElMessage.error('加载失败：' + (e?.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

onMounted(load)

// ============ 新建 / 编辑 ============
const editVisible = ref(false)
const editMode = ref<'create' | 'edit'>('create')
const editForm = reactive({
  templateId: null as number | null,
  name: '',
  type: 'custom',
  icon: '📋',
  color: '#4F6BFF',
  description: '',
  schemaRaw: '{}' as string,
})
const editBusy = ref(false)
const editErr = ref('')

function openCreate() {
  editMode.value = 'create'
  editForm.templateId = null
  editForm.name = ''
  editForm.type = 'custom'
  editForm.icon = '📋'
  editForm.color = '#4F6BFF'
  editForm.description = ''
  editForm.schemaRaw = JSON.stringify(_defaultSchema('自定义报销单'), null, 2)
  editErr.value = ''
  editVisible.value = true
}

function openEdit(t: any) {
  editMode.value = 'edit'
  editForm.templateId = t.id
  editForm.name = t.name
  editForm.type = t.type
  editForm.icon = t.icon
  editForm.color = t.color
  editForm.description = t.description || ''
  editForm.schemaRaw = JSON.stringify(t.schema, null, 2)
  editErr.value = ''
  editVisible.value = true
}

async function saveEdit() {
  editErr.value = ''
  let schema: any
  try { schema = JSON.parse(editForm.schemaRaw) }
  catch (e: any) { editErr.value = 'JSON 解析失败：' + e.message; return }
  editBusy.value = true
  try {
    if (editMode.value === 'create') {
      await reimburseApi.createTemplate({
        name: editForm.name,
        type: editForm.type,
        icon: editForm.icon,
        color: editForm.color,
        description: editForm.description,
        schema,
      } as any)
      ElMessage.success('已创建自定义模板')
    } else {
      await reimburseApi.updateTemplate(editForm.templateId!, {
        name: editForm.name, type: editForm.type, icon: editForm.icon,
        color: editForm.color, description: editForm.description, schema,
      })
      ElMessage.success('已更新')
    }
    editVisible.value = false
    load()
  } catch (e: any) {
    editErr.value = e?.response?.data?.message || e?.message || '保存失败'
  } finally {
    editBusy.value = false
  }
}

// ============ 复制内置 ============
async function cloneBuiltin(t: any) {
  try {
    const r: any = await reimburseApi.cloneTemplate(t.code)
    ElMessage.success('已复制为：' + (r?.name || t.name))
    load()
  } catch (e: any) {
    ElMessage.error('复制失败：' + (e?.response?.data?.message || e?.message))
  }
}

// ============ 删除自定义 ============


// ============ 预览 ============
const previewVisible = ref(false)
const previewTpl = ref<any>(null)


function onPreviewPrint() {
  const el = document.getElementById('tpl-preview')
  if (!el) { ElMessage.warning('预览内容未找到'); return }
  const win = window.open('', '_blank')
  if (!win) { ElMessage.warning('请允许弹窗以使用打印功能'); return }
  const styles = `
    body { font-family: 'Microsoft YaHei', sans-serif; padding: 24px; color: #1F2937; }
    .prev-company { text-align:center; font-size:12px; color:#6B7280; margin-bottom:4px; }
    .prev-title { text-align:center; font-size:22px; font-weight:600; margin:0 0 4px 0; }
    .prev-subtitle { text-align:center; font-size:11px; color:#9CA3AF; margin-bottom:18px; }
    .prev-meta, .prev-detail, .prev-summary { width:100%; border-collapse:collapse; margin-bottom:12px; }
    .prev-meta td, .prev-summary td { padding:6px 8px; border:1px solid #E5E7EB; font-size:12.5px; }
    .prev-meta .lbl, .prev-summary .lbl { background:#F3F4F6; color:#4B5563; width:90px; }
    .prev-summary .amt { color:#4F6BFF; font-weight:600; }
    .prev-summary .amt-num { color:#10B981; font-weight:600; }
    .prev-detail th, .prev-detail td { padding:6px 8px; border:1px solid #E5E7EB; font-size:12.5px; }
    .prev-detail th { background:#F9FAFB; font-weight:600; }
    .prev-section { font-size:13px; font-weight:600; margin:16px 0 6px 0; color:#374151; }
    .prev-sigs { display:flex; gap:24px; margin-top:30px; }
    .prev-sig-col { flex:1; }
    .prev-sig-label { font-size:11px; color:#6B7280; margin-bottom:6px; }
    .prev-sig-line { border-bottom:1px solid #1F2937; height:28px; }
    .prev-note { text-align:center; font-size:10px; color:#9CA3AF; margin-top:18px; }
    @page { size: A4; margin: 18mm; }
  `
  win.document.write(`<!DOCTYPE html><html><head><title>${previewTpl.value?.name || '模板预览'}</title><style>${styles}
</style></head><body>${el.innerHTML}</body></html>`)
  win.document.close()
  setTimeout(() => { win.print(); win.close() }, 300)
}

function openPreview(t: any) {
  previewTpl.value = t
  previewVisible.value = true
}

// 工具：金额格式（按 schema 中 type=money 的列右对齐）

// 过滤 table.rows 中的"占位空行"（这些是 openpyxl 输出但 HTML 中无意义）
function _tableRowsVisible(rows: any[]) {
  if (!rows) return []
  return rows
    .map((r, i) => ({ _idx: i, cells: r }))
    .filter(r => r.cells && r.cells.length > 0)
    .map((r, ri) => {
      // 跳过"无任何 cell"行
      return { _idx: ri, cells: r.cells.filter((c: any) => c && (c.text || '').trim() !== '' || (c.colspan > 1 || c.rowspan > 1)) }
    })
    .filter(r => r.cells.length > 0)
}
function _tableRowsVisible2(rows: any[]) {
  // 1:1 还原：合并"行内空 cell"到非空 cell 的 colspan，让 1 个 cell 占整行
  if (!rows) return rows
  return rows.map((r) => {
    if (!r || r.length === 0) return r
    // 检查是否所有 cell 都在同一行（无 rowspan 跨行）
    const allNoRowspan = r.every((c: any) => !c || (c.rowspan || 1) === 1)
    if (!allNoRowspan) return r
    // 找非空 cell
    const nonEmpty = r.filter((c: any) => c && (c.text || '').trim() !== '')
    if (nonEmpty.length === 0) return r  // 全部空，保持原样
    if (nonEmpty.length === 1) {
      // 只有 1 个非空 cell → 合并所有 colspan + rowspan 到这个 cell
      const totalCs = r.reduce((s: number, c: any) => s + (c?.colspan || 1), 0)
      const maxRs = r.reduce((m: number, c: any) => Math.max(m, c?.rowspan || 1), 1)
      return [{ ...nonEmpty[0], colspan: totalCs, rowspan: Math.max(maxRs, nonEmpty[0].rowspan || 1) }]
    }
    // 多个非空 cell：保留全部 cell（含空 cell 占位），让 col 位置不变
    return r
  })
}
function _isLabelCell(cell: any) {
  // 含特定关键词或为长 label → label
  return /摘要|大写|小写|备注|张数|项目|客户|部门|报销人|日期|金额|费用|凭证/.test(cell?.text || "")
}
function _isValueCell(cell: any) {
  return !_isLabelCell(cell) && (cell?.text || "").trim() !== ""
}
function _chunkPairs(arr: any[], n: number) {
  const out: any[][] = []
  for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n))
  return out
}
function _lastRowIdx(arr: any[], n: number) {
  return Math.max(0, Math.ceil(arr.length / n) - 1)
}
function _fmtMoney(v: any) {
  const n = Number(v || 0)
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function _toChineseAmount(num: number | string): string {
  // 数字金额转中文大写（人民币）
  const n = Number(num || 0)
  if (!isFinite(n) || n === 0) return '零元整'
  const upper = ['零','壹','贰','叁','肆','伍','陆','柒','捌','玖']
  const unit  = ['', '拾', '佰', '仟']
  const big   = ['', '万', '亿', '兆']
  const s = Math.abs(n).toFixed(2)
  const [intPart, decPart] = s.split('.')
  let intStr = ''
  if (intPart === '0') {
    intStr = ''
  } else {
    // 拆 4 位 group（高位在前）
    const groups: string[] = []
    let p = intPart
    while (p.length > 0) {
      const g = p.slice(-4)
      p = p.slice(0, -4)
      groups.unshift(g)
    }
    const groupStrs = groups.map((chunk) => {
      if (/^0+$/.test(chunk)) return ''
      let s = ''
      for (let i = 0; i < chunk.length; i++) {
        const d = Number(chunk[i])
        if (d !== 0) {
          if (i > 0 && s.length > 0 && s[s.length-1] !== '零' && Number(chunk[i-1]) === 0) s += '零'
          s += upper[d] + unit[chunk.length - 1 - i]
        }
      }
      return s
    })
    for (let gi = 0; gi < groupStrs.length; gi++) {
      const gs = groupStrs[gi]
      if (gs === '') {
        if (gi < groupStrs.length - 1 && groupStrs.slice(gi+1).some(g => g !== '')) intStr += '零'
        continue
      }
      // 前 group 末尾是 big unit 且 当前 group 最高位 = 0 → 补"零"
      if (gi > 0 && intStr.length > 0 && ['万','亿','兆'].includes(intStr[intStr.length-1]) && !intStr.endsWith('零')) {
        const curChunk = groups[gi]
        if (curChunk[0] === '0') intStr += '零'
      }
      intStr += gs + big[groupStrs.length - 1 - gi]
    }
    intStr = intStr.replace(/零+/g, '零').replace(/零+$/g, '')
  }
  const jiao = Number(decPart[0])
  const fen  = Number(decPart[1])
  let decStr = ''
  if (jiao === 0 && fen === 0) {
    decStr = '整'
    if (intStr === '') intStr = '零'
  } else {
    if (jiao !== 0) decStr += upper[jiao] + '角'
    else decStr += '零'
    if (fen !== 0) decStr += upper[fen] + '分'
    if (intStr === '') intStr = '零'
  }
  return (n < 0 ? '负' : '') + intStr + '元' + decStr
}

// 从 schema.applicant.fields 找显示名
function _applicantField(schema: any, key: string) {
  return (schema?.applicant?.fields || []).find((f: any) => f.key === key)?.label || key
}

// 模拟 1 行明细数据（用于预览）
const PREVIEW_SAMPLE = {
  seq: 1,
  expenseDate: '2026-06-19',
  expenseType: '差旅',
  title: '示例：客户拜访出差打车费',
  clientName: '示例客户公司',
  projectName: '示例项目',
  amount: 123456,        // 1,234.56 元 = 123456 分
}
async function deleteCustom(t: any) {
  try {
    await ElMessageBox.confirm(`确认删除模板「${t.name}」？删除后无法恢复`, '提示', { type: 'warning' })
  } catch { return }
  try {
    await reimburseApi.deleteTemplate(t.id)
    ElMessage.success('已删除')
    load()
  } catch (e: any) {
    ElMessage.error('删除失败：' + (e?.response?.data?.message || e?.message))
  }
}

// ============ 上传识别 ============
const recogVisible = ref(false)
const recogBusy = ref(false)
const recogPreview = ref<any>(null)
const recogText = ref('')
const recogFileInput = ref<HTMLInputElement | null>(null)

function openRecog() {
  recogVisible.value = true
  recogPreview.value = null
  recogText.value = ''
  setTimeout(() => recogFileInput.value?.click(), 50)
}

async function onFileChosen(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  if (f.size > 5 * 1024 * 1024) { ElMessage.warning('文件超过 5MB'); return }
  recogBusy.value = true
  try {
    // 文本文件直接读；其他（如 .pdf/.doc）走后端识别
    if (f.name.match(/\.(txt|md|csv|json)$/i)) {
      const txt = await f.text()
      recogText.value = txt
      const r: any = await reimburseApi.recognizeFromText(txt)
      recogPreview.value = r
    } else {
      const r: any = await reimburseApi.recognizeFromFile(f)
      recogText.value = r?.textPreview || ''
      recogPreview.value = r
    }
  } catch (e: any) {
    ElMessage.error('识别失败：' + (e?.response?.data?.message || e?.message))
  } finally {
    recogBusy.value = false
    if (recogFileInput.value) recogFileInput.value.value = ''
  }
}

async function recognizeText() {
  if (!recogText.value.trim()) { ElMessage.warning('请先粘贴或上传文本'); return }
  recogBusy.value = true
  try {
    const r: any = await reimburseApi.recognizeFromText(recogText.value)
    recogPreview.value = r
  } catch (e: any) {
    ElMessage.error('识别失败：' + (e?.response?.data?.message || e?.message))
  } finally {
    recogBusy.value = false
  }
}

function useRecognized() {
  const p = recogPreview.value
  if (!p?.suggestedSchema) { ElMessage.warning('请先识别'); return }
  editMode.value = 'create'
  editForm.templateId = null
  editForm.name = p.suggestedSchema?.header?.title || '识别出的模板'
  editForm.type = 'custom'
  editForm.icon = '📑'
  editForm.color = '#10B981'
  editForm.description = `基于上传文件识别（置信度 ${Math.round((p.confidence || 0) * 100)}%）`
  editForm.schemaRaw = JSON.stringify(p.suggestedSchema, null, 2)
  editErr.value = ''
  editVisible.value = true
  recogVisible.value = false
}

function _defaultSchema(title: string) {
  return {
    header: { company: '上海数智信息技术有限公司', title, subtitle: 'Reimbursement Form' },
    applicant: { fields: [
      { key: 'applicant', label: '报销人' },
      { key: 'department', label: '部门' },
      { key: 'expenseDate', label: '费用日期' },
      { key: 'formNo', label: '单据编号' },
    ]},
    summary: { fields: [
      { key: 'totalAmount', label: '申请金额', type: 'money' },
      { key: 'actualAmount', label: '实报金额', type: 'money' },
      { key: 'voucherNo', label: '凭证号' },
    ]},
    details: { columns: [
      { key: 'seq', label: '#', width: 32, align: 'center' },
      { key: 'expenseDate', label: '费用日期', width: 90, align: 'center' },
      { key: 'expenseType', label: '费用类型', width: 80, align: 'center' },
      { key: 'title', label: '摘要', width: 200, align: 'left' },
      { key: 'amount', label: '金额(元)', width: 100, align: 'right', type: 'money' },
    ]},
    footer: { signatures: [
      { label: '报销人签字', key: 'applicant' },
      { label: '部门负责人', key: 'dept_lead' },
      { label: '财务审核', key: 'finance' },
    ], note: '' },
  }
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>🧩 报销模板管理</h1>
        <p class="page-desc">内置 4 套通用模板，可复制后改造；或上传样张 AI 识别 / 空白新建</p>
      </div>
      <div style="display:flex;gap:8px">
        <el-button @click="openRecog">📤 上传样张 / 粘贴识别</el-button>
        <el-button type="primary" @click="openCreate">+ 新建模板</el-button>
      </div>
    </div>

    <!-- 内置 -->
    <h3 class="section-title">系统内置 <el-tag size="small" type="info">{{ builtinList.length }}</el-tag></h3>
    <div v-loading="loading" class="tpl-grid">
      <div v-for="t in builtinList" :key="t.code" class="tpl-card" :style="{ borderTop: '4px solid ' + t.color }">
        <div class="tpl-head">
          <span class="tpl-icon">{{ t.icon }}</span>
          <div>
            <div class="tpl-name">{{ t.name }}</div>
            <div class="tpl-code">{{ t.code }} · 系统内置</div>
          </div>
        </div>
        <div class="tpl-desc">{{ t.description }}</div>
        <div class="tpl-foot">
          <el-button size="small" link @click="openPreview(t)">👁 预览</el-button>
          <el-button size="small" link @click="cloneBuiltin(t)">📋 复制为自定义</el-button>
        </div>
      </div>
    </div>

    <!-- 自定义 -->
    <h3 class="section-title" style="margin-top:24px">自定义模板 <el-tag size="small">{{ customList.length }}</el-tag></h3>
    <div v-if="customList.length === 0" class="empty-tip">
      <p>暂无自定义模板</p>
      <p>点击右上角「新建模板」从零编辑，或「上传样张 / 粘贴识别」由 AI 自动生成。</p>
    </div>
    <div v-else class="tpl-grid">
      <div v-for="t in customList" :key="t.id" class="tpl-card" :style="{ borderTop: '4px solid ' + t.color }">
        <div class="tpl-head">
          <span class="tpl-icon">{{ t.icon }}</span>
          <div>
            <div class="tpl-name">{{ t.name }}</div>
            <div class="tpl-code">{{ t.code }} · 自定义</div>
          </div>
        </div>
        <div class="tpl-desc">{{ t.description || '—' }}</div>
        <div class="tpl-foot">
          <el-button size="small" link @click="openPreview(t)">👁 预览</el-button>
          <el-button size="small" link @click="openEdit(t)">✎ 编辑</el-button>
          <el-button size="small" link type="danger" @click="deleteCustom(t)">🗑 删除</el-button>
        </div>
      </div>
    </div>

    <!-- 编辑/新建弹窗 -->
    <el-dialog v-model="editVisible" :title="editMode === 'create' ? '+ 新建模板' : '✎ 编辑模板'" width="780px" :close-on-click-modal="false" append-to-body>
      <el-form :model="editForm" label-width="92px">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="名称"><el-input v-model="editForm.name" placeholder="如：研发费用报销单" /></el-form-item></el-col>
          <el-col :span="4"><el-form-item label="图标"><el-input v-model="editForm.icon" maxlength="2" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="颜色"><el-input v-model="editForm.color" type="color" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="类型"><el-input v-model="editForm.type" placeholder="custom" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="描述"><el-input v-model="editForm.description" /></el-form-item>
        <el-form-item label="Schema (JSON)">
          <el-input v-model="editForm.schemaRaw" type="textarea" :rows="14" spellcheck="false" style="font-family:'SF Mono',Menlo,monospace;font-size:12.5px" />
        </el-form-item>
        <div v-if="editErr" class="err-tip">{{ editErr }}</div>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editBusy" @click="saveEdit">✓ 保存</el-button>
      </template>
    </el-dialog>

    
    <!-- 预览弹窗（A4 风格渲染 schema） -->
    <el-dialog v-model="previewVisible" :title="(previewTpl?.icon || '📄') + ' 预览 · ' + (previewTpl?.name || '')" width="900px" :close-on-click-modal="false" append-to-body>
      <div class="preview-actions">
        <span class="preview-hint">A4 纸打印样式预览；预览仅供参考，实际以浏览器打印为准</span>
        <el-button @click="onPreviewPrint" type="primary" size="small">🖨 浏览器打印</el-button>
      </div>
      <div v-if="previewTpl" id="tpl-preview" class="tpl-preview-a4">
        <div class="prev-company">{{ previewTpl.schema?.header?.company || '上海数智信息技术有限公司' }}</div>
        <div v-if="previewTpl.schema?.header?.subtitle" class="prev-subtitle">{{ previewTpl.schema.header.subtitle }}</div>

        <table class="prev-meta">
          <tr>
            <td class="lbl">报销人</td><td>张 明</td>
            <td class="lbl">部门</td><td>财务部</td>
          </tr>
          <tr>
            <td class="lbl">单据编号</td><td>RB-20260619-XXXX</td>
            <td class="lbl">报销日期</td><td>2026-06-19</td>
          </tr>
        </table>

        <!-- detail 模式：多笔明细表 -->
        <template v-if="(previewTpl.schema?.layout || 'detail') === 'detail'">
          <h3 class="prev-section">费用明细</h3>
          <table class="prev-detail">
            <thead>
              <tr>
                <th v-for="c in (previewTpl.schema?.details?.columns || [])" :key="c.key" :style="{ width: (c.width || 80) + 'px', textAlign: c.align || 'left' }">
                  {{ c.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td v-for="c in (previewTpl.schema?.details?.columns || [])" :key="c.key" :style="{ textAlign: c.align || 'left' }">
                  <template v-if="c.type === 'money'">¥ {{ _fmtMoney(PREVIEW_SAMPLE[c.key]) }}</template>
                  <template v-else>{{ PREVIEW_SAMPLE[c.key] || '—' }}</template>
                </td>
              </tr>
              <tr class="prev-empty">
                <td :colspan="(previewTpl.schema?.details?.columns || []).length" style="text-align:center;color:#9CA3AF">… 实际使用时会从所选费用中自动填充</td>
              </tr>
            </tbody>
          </table>

          <table class="prev-cap" v-if="(previewTpl.schema?.summary?.fields || []).length">
            <tr>
              <td class="lbl cap-lbl">金额大写</td>
              <td class="cap-val">{{ _toChineseAmount((PREVIEW_SAMPLE.amount || 0) / 100) }}</td>
            </tr>
          </table>
          <table class="prev-summary" v-if="(previewTpl.schema?.summary?.fields || []).length">
            <tr v-for="(row, ri) in _chunkPairs(previewTpl.schema.summary.fields, 2)" :key="ri">
              <template v-for="(f, ci) in row" :key="f.key">
                <td class="lbl">{{ f.label }}</td>
                <td :colspan="(ri === _lastRowIdx(previewTpl.schema.summary.fields, 2) && row.length === 1) ? 3 : 1" :class="ci === 0 ? 'amt' : 'amt-num'">—</td>
              </template>
            </tr>
          </table>
        </template>

        <!-- single 模式：优先用 schema.table 真实表格，否则用 fields 网格 -->
        <template v-else>
          <template v-if="(previewTpl.schema?.table?.rows || []).length">
            <h3 class="prev-section">费用信息</h3>
            <table class="prev-table">
              <tr v-for="row in _tableRowsVisible2(previewTpl.schema?.table?.rows || [])" :key="row._idx">
                <td v-for="(cell, ci) in row" :key="ci"
                    :colspan="cell.colspan"
                    :rowspan="cell.rowspan"
                    :class="{ 'cell-header': cell.isHeader, 'cell-label': _isLabelCell(cell), 'cell-value': _isValueCell(cell) }">
                  {{ cell.text }}
                </td>
              </tr>
            </table>
          </template>
          <template v-else>
            <h3 class="prev-section">费用信息</h3>
            <table class="prev-fields">
              <tr v-for="(f, idx) in (previewTpl.schema?.summary?.fields || [])" :key="f.key">
                <td class="lbl">{{ f.label }}</td>
                <td :colspan="(idx % 2 === 0) ? 1 : 3">
                  <template v-if="f.type === 'money'">¥ {{ _fmtMoney(PREVIEW_SAMPLE[f.key] || 0) }}</template>
                  <template v-else-if="f.type === 'date'">{{ PREVIEW_SAMPLE[f.key] || '2026-06-19' }}</template>
                  <template v-else>{{ PREVIEW_SAMPLE[f.key] || '—' }}</template>
                </td>
                <td v-if="idx % 2 === 1"></td>
              </tr>
            </table>
          </template>
        </template>

        <div class="prev-sigs" :class="{ 'label-only': previewTpl.schema?.footer?.labelOnly }">
          <div v-for="s in (previewTpl.schema?.footer?.signatures || [])" :key="s.key" class="prev-sig-col">
            <span class="prev-sig-label">{{ s.label }}：</span>
            <span v-if="!previewTpl.schema?.footer?.labelOnly" class="prev-sig-line"></span>
          </div>
        </div>

        <div v-if="previewTpl.schema?.footer?.note" class="prev-note">{{ previewTpl.schema.footer.note }}</div>
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 上传识别 弹窗 -->
    <el-dialog v-model="recogVisible" title="📤 上传样张 / 粘贴识别" width="720px" :close-on-click-modal="false" append-to-body>
      <el-tabs>
        <el-tab-pane label="📁 上传文件">
          <p class="hint">
            支持 <b>.xlsx</b>（推荐：报销单 Excel 模板）、.txt / .md / .csv / .json，或任意文件（智能解析文本）。
          </p>
          <input ref="recogFileInput" type="file" accept=".xlsx,.txt,.md,.csv,.json,.docx,.pdf,*" style="display:none" @change="onFileChosen" />
          <el-button @click="recogFileInput?.click()" :loading="recogBusy">📁 选择文件并识别</el-button>
        </el-tab-pane>
        <el-tab-pane label="📋 粘贴文本">
          <p class="hint">把样张文字粘到下面（可空行、分隔符无要求），点击识别。</p>
          <el-input v-model="recogText" type="textarea" :rows="10" placeholder="例如：&#10;差旅费报销单&#10;报销人：&#10;部门：&#10;出差起止：&#10;单据编号：&#10;差旅费合计：&#10;实报金额：&#10;凭证号：&#10;报销人签字  部门负责人  财务审核  总经理审批" />
          <el-button style="margin-top:10px" @click="recognizeText" :loading="recogBusy">🔍 识别</el-button>
        </el-tab-pane>
      </el-tabs>

      <el-divider v-if="recogPreview" content-position="left">识别结果</el-divider>
      <div v-if="recogPreview" class="recog-result">
        <p>✅ 识别到 <b>{{ recogPreview.detectedFields?.length || 0 }}</b> 个字段，置信度 <b>{{ Math.round((recogPreview.confidence || 0) * 100) }}%</b></p>
        <p>推荐标题：<b>{{ recogPreview.suggestedSchema?.header?.title }}</b></p>
        <p>字段：
          <el-tag v-for="f in recogPreview.detectedFields" :key="f.key" size="small" style="margin:2px">
            {{ f.label }}（{{ f.key }}）
          </el-tag>
        </p>
        <p>签字栏：
          <el-tag v-for="s in recogPreview.suggestedSchema?.footer?.signatures" :key="s.key" size="small" type="warning" style="margin:2px">
            {{ s.label }}
          </el-tag>
        </p>
        <el-button type="primary" @click="useRecognized">📝 用此结果创建模板</el-button>
      </div>
    </el-dialog>
  </div>
</template>

<style>
/* 预览弹窗（el-dialog append-to-body 不受 scoped 影响，必须非 scoped）*/

.tpl-preview-a4 .prev-table { width:100%; border-collapse:collapse; table-layout: fixed; }
.tpl-preview-a4 .prev-table td { padding: 8px 12px; border: 1px solid #4B5563; font-size: 12.5px; vertical-align: middle; min-height: 32px; }
.tpl-preview-a4 .prev-table .cell-header { font-size: 18px; font-weight: 700; text-align: center; border: 0; padding: 12px; }
.tpl-preview-a4 .prev-table .cell-label { background: #fff; font-weight: 500; text-align: center; color: #1F2937; }
.tpl-preview-a4 .prev-table .cell-value { background: #fff; text-align: center; color: #4B5563; }


.tpl-preview-a4 .prev-sigs.label-only { gap: 28px; padding: 0 12px; }
.tpl-preview-a4 .prev-sigs.label-only .prev-sig-col { display: flex; align-items: baseline; gap: 6px; }
.tpl-preview-a4 .prev-sigs.label-only .prev-sig-label { font-size: 12.5px; color: #4B5563; font-weight: 500; margin: 0; }


.tpl-preview-a4 .prev-fields { width:100%; border-collapse:collapse; }
.tpl-preview-a4 .prev-fields td { padding:8px 12px; border:1px solid #D1D5DB; font-size:13px; }
.tpl-preview-a4 .prev-fields .lbl { background:#F9FAFB; color:#4B5563; width:100px; font-weight:500; }
.tpl-preview-a4 .prev-fields tr td:nth-child(3) { border-left:0; }

.tpl-preview-a4 {
  background: #fff;
  padding: 32px 40px;
  border: 1px solid #E5E7EB;
  border-radius: 4px;
  font-family: 'Microsoft YaHei', -apple-system, sans-serif;
  color: #1F2937;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  max-height: 70vh;
  overflow-y: auto;
}
.tpl-preview-a4 .prev-company { text-align:center; font-size:12px; color:#6B7280; margin-bottom:4px; }
.tpl-preview-a4 .prev-title { text-align:center; font-size:22px; font-weight:600; margin:0 0 4px 0; }
.tpl-preview-a4 .prev-subtitle { text-align:center; font-size:11px; color:#9CA3AF; margin-bottom:18px; }
.tpl-preview-a4 .prev-meta,
.tpl-preview-a4 .prev-detail,
.tpl-preview-a4 .prev-summary { width:100%; border-collapse:collapse; margin-bottom:12px; table-layout: auto; }
.tpl-preview-a4 .prev-meta td,
.tpl-preview-a4 .prev-summary td { padding:6px 10px; border:1px solid #E5E7EB; font-size:12.5px; vertical-align: middle; }
.tpl-preview-a4 .prev-meta .lbl,
.tpl-preview-a4 .prev-summary .lbl { background:#F3F4F6; color:#4B5563; white-space: nowrap; }
.tpl-preview-a4 .prev-summary .amt { color:#4F6BFF; font-weight:600; min-width: 120px; }
.tpl-preview-a4 .prev-summary .amt-num { color:#10B981; font-weight:600; min-width: 120px; }
.tpl-preview-a4 .prev-cap { width:100%; border-collapse:collapse; margin-bottom:8px; }
.tpl-preview-a4 .prev-cap td { padding:6px 10px; border:1px solid #E5E7EB; font-size:12.5px; }
.tpl-preview-a4 .prev-cap .cap-lbl { background:#F3F4F6; color:#4B5563; width:90px; white-space:nowrap; font-weight:500; }
.tpl-preview-a4 .prev-cap .cap-val { color:#1F2937; font-weight:600; letter-spacing: 0.5px; }
.tpl-preview-a4 .prev-detail th,
.tpl-preview-a4 .prev-detail td { padding:6px 8px; border:1px solid #D1D5DB; font-size:12.5px; }
.tpl-preview-a4 .prev-detail th { background:#F9FAFB; font-weight:600; border-bottom:2px solid #9CA3AF; }
.tpl-preview-a4 .prev-section { font-size:13px; font-weight:600; margin:18px 0 6px 0; color:#374151; }
.tpl-preview-a4 .prev-sigs { display:flex; gap:24px; margin-top:32px; padding:0 20px; }
.tpl-preview-a4 .prev-sig-col { flex:1; min-width:0; }
.tpl-preview-a4 .prev-sig-label { font-size:11px; color:#6B7280; margin-bottom:8px; }
.tpl-preview-a4 .prev-sig-line { border-bottom:1px solid #1F2937; height:32px; }
.tpl-preview-a4 .prev-note { text-align:center; font-size:10px; color:#9CA3AF; margin-top:18px; }
.tpl-preview-a4 .prev-empty td { color:#9CA3AF !important; }
.preview-actions { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
.preview-hint { color:#6B7280; font-size:12px; }
</style>

<style scoped>
.page-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.page-header h1 { font-size: 20px; font-weight: 600; margin: 0; }
.page-desc { color:#6B7280; font-size:13px; margin:4px 0 0 0; }
.section-title { font-size:14px; font-weight:600; color:#374151; margin:8px 0 12px 0; display:flex; align-items:center; gap:8px; }
.tpl-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap:12px; }
.tpl-card { background:#fff; border:1px solid #E5E7EB; border-radius:8px; padding:14px; transition: all 0.15s; }
.tpl-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.06); transform: translateY(-1px); }
.tpl-head { display:flex; gap:10px; align-items:center; margin-bottom:8px; }
.tpl-icon { font-size:24px; }
.tpl-name { font-size:15px; font-weight:600; color:#111827; }
.tpl-code { font-size:11px; color:#9CA3AF; font-family:'SF Mono',Menlo,monospace; }
.tpl-desc { font-size:12.5px; color:#4B5563; min-height:36px; line-height:1.5; }
.tpl-foot { display:flex; gap:8px; margin-top:8px; }
.empty-tip { text-align:center; color:#9CA3AF; padding:32px 0; background:#F9FAFB; border:1px dashed #E5E7EB; border-radius:8px; }
.empty-tip p { margin:4px 0; }
.err-tip { color:#EF4444; font-size:12px; padding:6px 0; }
.hint { color:#6B7280; font-size:12px; margin:0 0 8px 0; }
.recog-result p { font-size:13px; margin:6px 0; }
</style>
