<script setup lang="ts">
/**
 * AdminPrintTemplate · 打印模板管理（M2 阶段 7：补前端模块）
 * - 列表：所有模板（按 docType 分组）
 * - 状态切换：发布（draft→active）/ 归档（→archived）
 * - 查看 JSON：仅看，不可改（V1 没设计器）
 * - 创建：JSON 导入 / 字段填写
 *
 * 设计文档：plans/udpe-design/design.md §三
 * 评审决策 ADR-11 #3：M1 预置 4 套（合同/报销/发票/费用），不允许编辑
 * 后端端点：/api/v1/admin/print-templates*
 */
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { printApi } from '@/api/print'
import { PrintPreviewDialog } from '@/components/common/print'
import { contractApi, invoiceOcrApi, expenseApi, reimburseApi } from '@/api/modules'

const templates = ref<any[]>([])
const loading = ref(false)

// 状态过滤
const filter = reactive<{ docType: string; status: string }>({
  docType: '',
  status: '',
})

const kpis = computed(() => {
  const all = templates.value
  return [
    { label: '模板总数', num: all.length, color: 'primary', icon: '📋' },
    { label: '已发布', num: all.filter(t => t.status === 'active').length, color: 'success', icon: '✓' },
    { label: '草稿', num: all.filter(t => t.status === 'draft').length, color: 'warning', icon: '✎' },
    { label: '已归档', num: all.filter(t => t.status === 'archived').length, color: 'info', icon: '📦' },
    { label: '业务类型', num: new Set(all.map(t => t.docType)).size, color: 'primary', icon: '🏷' },
  ]
})

// 详情弹窗
const detailVisible = ref(false)
const detailTpl = ref<any>(null)

// 浏览器预览弹窗
const previewVisible = ref(false)
const previewTemplate = ref<any>(null)
const previewBusinessOptions = ref<any[]>([])
const previewBusinessId = ref<number | null>(null)
const previewLoading = ref(false)

// 创建弹窗
const createVisible = ref(false)
const createForm = reactive({
  code: '',
  name: '',
  docType: 'invoice',
  paper: 'A4',
  widthMm: 210,
  heightMm: 297,
  orientation: 'portrait',
  description: '',
  schemaJson: { body: [] } as any,
})
const createJsonMode = ref(false)
const createJsonRaw = ref('{\n  "body": []\n}')

const DOC_TYPE_LABEL: Record<string, string> = {
  contract: '合同',
  invoice: '发票',
  reimbursement: '报销单',
  expense: '费用',
}

const STATUS_TAG: Record<string, { label: string; type: string }> = {
  active:   { label: '已发布', type: 'success' },
  draft:    { label: '草稿',   type: 'warning' },
  archived: { label: '已归档', type: 'info' },
}

async function loadList() {
  loading.value = true
  try {
    const r = await printApi.listTemplates({
      docType: filter.docType || undefined,
      status: filter.status || undefined,
    }).catch(() => ({ list: [], total: 0 }))
    templates.value = r.list || []
  } catch (e: any) {
    ElMessage.error('加载失败：' + (e?.message || ''))
  } finally {
    loading.value = false
  }
}

async function publish(t: any) {
  await ElMessageBox.confirm(`确认发布模板「${t.name}」？发布后可被业务方调用。`, '发布确认', {
    type: 'success',
  }).catch(() => null)
  if (!t.id) return
  try {
    await printApi.publishTemplate(t.id)
    ElMessage.success('已发布')
    await loadList()
  } catch (e: any) {
    ElMessage.error('发布失败：' + (e?.message || ''))
  }
}

async function archive(t: any) {
  await ElMessageBox.confirm(`确认归档「${t.name}」？归档后不可被业务调用。`, '归档确认', {
    type: 'warning',
  }).catch(() => null)
  if (!t.id) return
  try {
    await printApi.archiveTemplate(t.id)
    ElMessage.success('已归档')
    await loadList()
  } catch (e: any) {
    ElMessage.error('归档失败：' + (e?.message || ''))
  }
}

async function deleteTemplate(t: any) {
  await ElMessageBox.confirm(
    `确认删除模板「${t.name}」？删除后不可恢复。`,
    '删除确认',
    { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' },
  ).catch(() => null)
  if (!t.id) return
  try {
    await printApi.deleteTemplate(t.id)
    ElMessage.success('已删除')
    await loadList()
  } catch (e: any) {
    ElMessage.error('删除失败：' + (e?.message || ''))
  }
}

function gotoEditor(t: any) {
  // 跳到 M3 阶段 1 编辑器 (独立路由)
  window.location.href = `/admin/print-template/editor/${t.id}`
}

function openDetail(t: any) {
  detailTpl.value = t
  detailVisible.value = true
}

async function openPreview(t: any) {
  previewTemplate.value = t
  previewVisible.value = true
  previewBusinessId.value = null
  previewLoading.value = true
  try {
    // 拉该 doc_type 的业务记录列表
    const list = await fetchBusinessList(t.docType)
    previewBusinessOptions.value = list
    // 默认选第一条
    if (list.length > 0) previewBusinessId.value = list[0].value
  } catch (e: any) {
    ElMessage.error('加载业务记录失败：' + (e?.message || ''))
  } finally {
    previewLoading.value = false
  }
}

async function fetchBusinessList(docType: string): Promise<Array<{ label: string; value: number }>> {
  const out: Array<{ label: string; value: number }> = []
  try {
    if (docType === 'contract') {
      const r: any = await contractApi.list({ page: 1, pageSize: 30 }).catch(() => null)
      const rows = r?.list || r?.data?.list || []
      for (const r of rows) out.push({ label: `${r.code || ''} ${r.name || ''}`.trim() || `#${r.contractId || r.id}`, value: r.contractId || r.id })
    } else if (docType === 'invoice') {
      const r: any = await invoiceOcrApi.records({ page: 1, pageSize: 30 }).catch(() => null)
      const rows = r?.list || r?.data?.list || []
      for (const r of rows) out.push({ label: r.invoiceNo || r.sellerName || `#${r.invoiceId || r.id}`, value: r.invoiceId || r.id })
    } else if (docType === 'expense') {
      const r: any = await expenseApi.list({ page: 1, pageSize: 30 }).catch(() => null)
      const rows = r?.list || r?.data?.list || []
      for (const r of rows) out.push({ label: r.code || r.title || `#${r.expenseId || r.id}`, value: r.expenseId || r.id })
    } else if (docType === 'reimbursement') {
      const r: any = await reimburseApi.list({ page: 1, pageSize: 30 }).catch(() => null)
      const rows = r?.list || r?.data?.list || []
      for (const r of rows) out.push({ label: r.formNo || r.title || `#${r.formId || r.id}`, value: r.formId || r.id })
    }
  } catch (e) {
    console.error('fetchBusinessList error', e)
  }
  return out
}

function openCreate() {
  createForm.code = ''
  createForm.name = ''
  createForm.docType = 'invoice'
  createForm.paper = 'A4'
  createForm.widthMm = 210
  createForm.heightMm = 297
  createForm.orientation = 'portrait'
  createForm.description = ''
  createForm.schemaJson = { body: [] }
  createJsonRaw.value = '{\n  "body": []\n}'
  createJsonMode.value = false
  createVisible.value = true
}

function toggleJsonMode() {
  if (!createJsonMode.value) {
    // 切到 JSON：序列化当前 schemaJson
    createJsonRaw.value = JSON.stringify(createForm.schemaJson || { body: [] }, null, 2)
  } else {
    // 切回表单：解析 JSON
    try {
      createForm.schemaJson = JSON.parse(createJsonRaw.value)
    } catch (e: any) {
      ElMessage.error('JSON 解析失败：' + (e?.message || ''))
    }
  }
  createJsonMode.value = !createJsonMode.value
}

async function submitCreate() {
  if (!createForm.code || !createForm.name) {
    ElMessage.warning('请填写 code 和 name')
    return
  }
  // 如果在 JSON 模式，先同步
  if (createJsonMode.value) {
    try {
      createForm.schemaJson = JSON.parse(createJsonRaw.value)
    } catch (e: any) {
      ElMessage.error('JSON 解析失败：' + (e?.message || ''))
      return
    }
  }
  try {
    await printApi.createTemplate({
      code: createForm.code,
      name: createForm.name,
      docType: createForm.docType,
      paper: createForm.paper,
      widthMm: createForm.widthMm,
      heightMm: createForm.heightMm,
      orientation: createForm.orientation,
      description: createForm.description,
      schemaJson: createForm.schemaJson,
    })
    ElMessage.success('已创建（draft 状态）')
    createVisible.value = false
    await loadList()
  } catch (e: any) {
    ElMessage.error('创建失败：' + (e?.message || ''))
  }
}

onMounted(loadList)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1>🧾 打印模板</h1>
        <p class="page-desc">UDPE 统一单据打印引擎的模板中心 · M1 阶段 3</p>
      </div>
      <div class="page-actions">
        <el-button @click="loadList">🔄 刷新</el-button>
        <el-button type="primary" @click="openCreate">+ 新建模板</el-button>
      </div>
    </div>

    <!-- KPI -->
    <div class="kpi-grid">
      <div v-for="k in kpis" :key="k.label" :class="['kpi-card', `kpi-${k.color}`]">
        <div class="kpi-icon">{{ k.icon }}</div>
        <div class="kpi-body">
          <div class="kpi-num">{{ k.num }}</div>
          <div class="kpi-label">{{ k.label }}</div>
        </div>
      </div>
    </div>

    <!-- 过滤 -->
    <div class="filter-bar">
      <span class="filter-label">业务类型：</span>
      <el-select v-model="filter.docType" placeholder="全部" clearable size="small" style="width: 140px;" @change="loadList">
        <el-option label="合同" value="contract" />
        <el-option label="发票" value="invoice" />
        <el-option label="报销单" value="reimbursement" />
        <el-option label="费用" value="expense" />
      </el-select>
      <span class="filter-label" style="margin-left: 12px;">状态：</span>
      <el-select v-model="filter.status" placeholder="全部" clearable size="small" style="width: 140px;" @change="loadList">
        <el-option label="已发布" value="active" />
        <el-option label="草稿" value="draft" />
        <el-option label="已归档" value="archived" />
      </el-select>
    </div>

    <!-- 列表 -->
    <div class="detail-section">
      <div class="detail-section-body">
        <el-table v-loading="loading" :data="templates" stripe>
          <el-table-column label="模板标识" min-width="200">
            <template #default="{ row }">
              <div class="tpl-id">
                <span class="tpl-code">{{ row.code }}</span>
                <span class="tpl-ver">v{{ row.version }}</span>
              </div>
              <div class="tpl-name">{{ row.name }}</div>
            </template>
          </el-table-column>
          <el-table-column label="业务类型" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ DOC_TYPE_LABEL[row.docType] || row.docType }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="纸型" width="90">
            <template #default="{ row }">{{ row.paper }} / {{ row.orientation === 'portrait' ? '纵' : '横' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="(STATUS_TAG[row.status] || {}).type as any" size="small">
                {{ (STATUS_TAG[row.status] || {}).label || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="默认" width="80">
            <template #default="{ row }">
              <span v-if="row.isDefault" style="color:#F59E0B;">⭐ 是</span>
              <span v-else style="color:#9CA3AF;">—</span>
            </template>
          </el-table-column>
          <el-table-column label="描述" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.description || '—' }}</template>
          </el-table-column>
          <el-table-column label="更新时间" width="180">
            <template #default="{ row }">{{ row.updatedAt || '—' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="openPreview(row)">👁 预览</el-button>
              <el-button size="small" link @click="gotoEditor(row)">✏️ 编辑</el-button>
              <el-button size="small" link @click="openDetail(row)">查看 JSON</el-button>
              <el-button v-if="row.status === 'draft'" size="small" type="success" link @click="publish(row)">发布</el-button>
              <el-button v-if="row.status === 'active'" size="small" type="warning" link @click="archive(row)">归档</el-button>
              <el-button v-if="row.status !== 'active'" size="small" type="danger" link @click="deleteTemplate(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="📄 模板 JSON" width="760px" destroy-on-close>
      <div v-if="detailTpl" class="json-detail">
        <div class="json-meta">
          <span><b>code:</b> {{ detailTpl.code }}</span>
          <span><b>name:</b> {{ detailTpl.name }}</span>
          <span><b>docType:</b> {{ detailTpl.docType }}</span>
          <span><b>version:</b> v{{ detailTpl.version }}</span>
        </div>
        <pre class="json-content">{{ JSON.stringify(detailTpl.schemaJson, null, 2) }}</pre>
      </div>
    </el-dialog>

    <!-- 创建弹窗 -->
    <el-dialog v-model="createVisible" title="+ 新建打印模板" width="720px" destroy-on-close>
      <el-form label-width="100px" size="default">
        <el-form-item label="code" required>
          <el-input v-model="createForm.code" placeholder="例：custom_contract_v1" />
        </el-form-item>
        <el-form-item label="name" required>
          <el-input v-model="createForm.name" placeholder="例：合同模板 V1" />
        </el-form-item>
        <el-form-item label="业务类型" required>
          <el-select v-model="createForm.docType" style="width: 100%;">
            <el-option label="合同" value="contract" />
            <el-option label="发票" value="invoice" />
            <el-option label="报销单" value="reimbursement" />
            <el-option label="费用" value="expense" />
          </el-select>
        </el-form-item>
        <el-form-item label="纸型">
          <el-select v-model="createForm.paper" style="width: 120px;">
            <el-option label="A4" value="A4" />
            <el-option label="A3" value="A3" />
            <el-option label="A5" value="A5" />
          </el-select>
          <el-select v-model="createForm.orientation" style="width: 120px; margin-left: 8px;">
            <el-option label="纵向" value="portrait" />
            <el-option label="横向" value="landscape" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="schemaJson">
          <div style="width: 100%;">
            <el-button size="small" @click="toggleJsonMode">
              {{ createJsonMode ? '📋 切到表单' : '📝 切到 JSON 编辑' }}
            </el-button>
            <div v-if="!createJsonMode" class="schema-hint">
              V1 简化：表单仅初始化空 body，复杂模板请用 JSON 编辑模式。
            </div>
            <el-input
              v-else
              v-model="createJsonRaw"
              type="textarea"
              :rows="14"
              spellcheck="false"
              style="margin-top: 8px; font-family: 'SF Mono', Menlo, monospace;"
            />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate">创建（draft 状态）</el-button>
      </template>
    </el-dialog>
  </div>


    <!-- 浏览器预览弹窗（M2 阶段 8 重构版） -->
    <!-- 业务选择器（小提示条，放模板中心页面顶部） -->
    <div v-if="previewVisible && previewTemplate" class="preview-picker">
      <div class="preview-picker-inner">
        <span class="picker-label">选一条 <b>{{ previewTemplate.docType }}</b> 记录预览：</span>
        <el-select v-model="previewBusinessId" :loading="previewLoading" size="small" style="width: 360px;" placeholder="请选择">
          <el-option
            v-for="opt in previewBusinessOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <span v-if="!previewLoading && previewBusinessOptions.length === 0" style="color: #DC2626; font-size: 12px;">
          该业务类型暂无数据，请先创建
        </span>
        <el-button size="small" link @click="previewVisible = false">关闭</el-button>
      </div>
    </div>

    <PrintPreviewDialog
      v-if="previewVisible && previewTemplate && previewBusinessId !== null"
      v-model="previewVisible"
      :template-code="previewTemplate.code"
      :data="{ _resolver: String(previewBusinessId) }"
      :source-module="previewTemplate.docType"
      :source-id="String(previewBusinessId)"
      :title="`${previewTemplate.name} 预览`"
    />
</template>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #0F172A; margin: 0 0 4px 0; }
.page-desc { font-size: 13px; color: #6B7280; margin: 0; }
.page-actions { display: flex; gap: 8px; }

.kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; padding: 0 24px 16px; }
.kpi-card { background: #FFFFFF; border-radius: 10px; padding: 16px; display: flex; align-items: center; gap: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.kpi-icon { font-size: 24px; }
.kpi-num { font-size: 22px; font-weight: 600; line-height: 1.2; color: #0F172A; }
.kpi-label { font-size: 12px; color: #6B7280; }
.kpi-primary { border-left: 3px solid #4F6BFF; }
.kpi-success { border-left: 3px solid #10B981; }
.kpi-warning { border-left: 3px solid #F59E0B; }
.kpi-info { border-left: 3px solid #6B7280; }

.filter-bar { display: flex; align-items: center; padding: 0 24px 12px; }
.filter-label { font-size: 13px; color: #6B7280; }

.detail-section { background: #FFFFFF; border-radius: 12px; margin: 0 24px 24px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.detail-section-body { padding: 12px 16px; }

.tpl-id { display: flex; align-items: baseline; gap: 6px; }
.tpl-code { font-family: 'SF Mono', Menlo, monospace; font-size: 13px; color: #4F6BFF; font-weight: 500; }
.tpl-ver { font-size: 11px; color: #9CA3AF; }
.tpl-name { font-size: 13px; color: #1F2937; margin-top: 2px; }

.json-meta { display: flex; flex-wrap: wrap; gap: 16px; font-size: 12px; color: #4B5563; margin-bottom: 12px; }
.json-meta b { color: #0F172A; margin-right: 4px; }
.json-content { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 8px; padding: 12px; font-size: 12px; line-height: 1.5; max-height: 60vh; overflow: auto; font-family: 'SF Mono', Menlo, monospace; }

.schema-hint { font-size: 12px; color: #6B7280; margin-top: 8px; line-height: 1.6; }

/* 业务选择器浮条（M2 阶段 8） */
.preview-picker {
  position: fixed;
  top: 80px;
  right: 24px;
  z-index: 2000;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.10);
  padding: 12px 16px;
}
.preview-picker-inner {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.picker-label {
  font-size: 13px;
  color: #4B5563;
}
</style>
