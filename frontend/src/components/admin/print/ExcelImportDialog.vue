<!--
  ExcelImportDialog · Excel 模板导入弹窗 (M3 阶段 4)
  - 上传 .xlsx → 解析每个 sheet 为 schemaJson + HTML 预览
  - 选择 sheet → 命名 + docType → 保存为新模板
-->
<template>
  <el-dialog
    :model-value="modelValue"
    title="📥 导入 Excel 模板"
    width="900px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <!-- Step 1: 上传文件 -->
    <div v-if="step === 1" class="step">
      <p class="step-desc">选择 .xlsx 文件, 系统会自动解析所有 sheet 并生成 grid 模板。</p>
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        :on-change="onFileSelected"
        :on-exceed="onExceed"
        accept=".xlsx"
        drag
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖动文件到此处或<em>点击选择</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">仅支持 .xlsx 格式, 大小不超过 10MB</div>
        </template>
      </el-upload>
      <div v-if="selectedFile" class="file-info">
        <span>📄 {{ selectedFile.name }} ({{ (selectedFile.size / 1024).toFixed(1) }} KB)</span>
      </div>
      <div v-if="errorMsg" class="err-msg">⚠ {{ errorMsg }}</div>
    </div>

    <!-- Step 2: 解析结果 + 预览 -->
    <div v-else-if="step === 2" class="step">
      <div class="result-summary">
        <span>📄 {{ preview?.filename }}</span>
        <span>共 {{ preview?.totalSheets }} 个 sheet</span>
      </div>
      <!-- Sheet 切换 -->
      <el-tabs v-model="activeSheet" class="sheet-tabs">
        <el-tab-pane
          v-for="s in preview?.sheets || []"
          :key="s.name"
          :name="s.name"
          :label="`${s.name} (${s.rowCount}行 × ${s.colCount}列 · ${s.mergedCount}合并)`"
        />
      </el-tabs>
      <!-- 当前 sheet 的预览 + 信息 -->
      <div v-if="currentSheet" class="sheet-content">
        <div class="sheet-stats">
          <el-tag size="small">行: {{ currentSheet.rowCount }}</el-tag>
          <el-tag size="small">列: {{ currentSheet.colCount }}</el-tag>
          <el-tag size="small">合并: {{ currentSheet.mergedCount }}</el-tag>
          <el-tag size="small" type="info">grid rows: {{ currentSheet.schemaJson.body[0]?.rows?.length || 0 }}</el-tag>
          <el-tag v-if="currentSheet.placeholders.length" size="small" type="success">
            占位符: {{ currentSheet.placeholders.length }}
          </el-tag>
        </div>
        <!-- 占位符提示 -->
        <el-alert
          v-if="currentSheet.placeholders.length"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 8px;"
        >
          检测到占位符: <code v-for="p in currentSheet.placeholders" :key="p" class="ph-code">{{ p }}</code>
        </el-alert>
        <!-- HTML 预览 -->
        <iframe
          v-if="currentSheet.html"
          :srcdoc="currentSheet.html"
          class="preview-iframe"
          sandbox="allow-same-origin"
        />
      </div>
    </div>

    <!-- Step 3: 命名 + 保存 -->
    <div v-else-if="step === 3" class="step">
      <el-form :model="form" label-width="100px" size="default">
        <el-form-item label="模板 code" required>
          <el-input v-model="form.code" placeholder="例：reimbursement_excel_v1" />
        </el-form-item>
        <el-form-item label="模板名称" required>
          <el-input v-model="form.name" placeholder="例：费用报销单（Excel 导入）" />
        </el-form-item>
        <el-form-item label="业务类型" required>
          <el-select v-model="form.docType" style="width:100%">
            <el-option label="合同" value="contract" />
            <el-option label="发票" value="invoice" />
            <el-option label="报销单" value="reimbursement" />
            <el-option label="费用" value="expense" />
            <el-option label="通用" value="general" />
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
      </el-form>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="cancel">取消</el-button>
        <el-button v-if="step === 1" type="primary" :loading="parsing" :disabled="!selectedFile" @click="parseFile">
          解析
        </el-button>
        <el-button v-if="step === 2" @click="step = 1">← 上一步</el-button>
        <el-button v-if="step === 2" type="primary" @click="goSave">下一步: 命名 →</el-button>
        <el-button v-if="step === 3" @click="step = 2">← 上一步</el-button>
        <el-button v-if="step === 3" type="primary" :loading="saving" @click="save">确认导入</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage, type UploadFile, type UploadInstance, type UploadRawFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { excelImportApi, type ExcelImportPreview, type ExcelImportSheet } from '@/api/print'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'success', templateId: number): void
}>()

const step = ref(1)
const selectedFile = ref<UploadFile | null>(null)
const parsing = ref(false)
const saving = ref(false)
const errorMsg = ref<string | null>(null)
const preview = ref<ExcelImportPreview | null>(null)
const activeSheet = ref<string>('')
const uploadRef = ref<UploadInstance>()

const currentSheet = computed<ExcelImportSheet | null>(() => {
  if (!preview.value || !activeSheet.value) return null
  return preview.value.sheets.find(s => s.name === activeSheet.value) || null
})

const form = reactive({
  code: '',
  name: '',
  docType: 'reimbursement',
  paper: 'A4',
  orientation: 'portrait',
})

function cancel() {
  emit('update:modelValue', false)
}

function reset() {
  step.value = 1
  selectedFile.value = null
  parsing.value = false
  saving.value = false
  errorMsg.value = null
  preview.value = null
  activeSheet.value = ''
  form.code = ''
  form.name = ''
  form.docType = 'reimbursement'
  form.paper = 'A4'
  form.orientation = 'portrait'
}

watch(() => props.modelValue, (v) => {
  if (v) reset()
})

function onFileSelected(file: UploadFile) {
  selectedFile.value = file
  errorMsg.value = null
}
function onExceed() {
  ElMessage.warning('只能上传一个文件')
}

async function parseFile() {
  if (!selectedFile.value?.raw) {
    ElMessage.warning('请先选择文件')
    return
  }
  parsing.value = true
  errorMsg.value = null
  try {
    const r = await excelImportApi.preview(selectedFile.value.raw as File)
    preview.value = r
    if (r.sheets.length > 0) {
      activeSheet.value = r.sheets[0].name
    }
    step.value = 2
  } catch (e: any) {
    const detail = e?.response?.data?.message || e?.response?.data?.detail
    errorMsg.value = detail || e.message || '解析失败'
  } finally {
    parsing.value = false
  }
}

function goSave() {
  if (!currentSheet.value) return
  // 自动建议 code / name
  if (!form.code) {
    const ts = Date.now().toString(36).slice(-4)
    form.code = `${currentSheet.value.name.toLowerCase()}_excel_${ts}`
  }
  if (!form.name) {
    form.name = `${currentSheet.value.name} (Excel 导入)`
  }
  step.value = 3
}

async function save() {
  if (!form.code || !form.name || !form.docType) {
    ElMessage.warning('请填写必填字段')
    return
  }
  if (!currentSheet.value) return
  saving.value = true
  try {
    const t = await excelImportApi.confirm({
      code: form.code,
      name: form.name,
      docType: form.docType,
      paper: form.paper,
      orientation: form.orientation,
      schemaJson: currentSheet.value.schemaJson,
      sourceFile: preview.value?.filename,
      sourceSheet: currentSheet.value.name,
    })
    ElMessage.success(`已创建模板: ${t.name} (id=${t.id})`)
    emit('success', t.id)
    emit('update:modelValue', false)
  } catch (e: any) {
    const detail = e?.response?.data?.message || e?.response?.data?.detail
    ElMessage.error('保存失败: ' + (detail || e.message))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.step { padding: 0 12px; }
.step-desc { color: #6B7280; font-size: 13px; margin-bottom: 16px; }
.file-info {
  margin-top: 12px; padding: 8px 12px;
  background: #F0F9FF; border: 1px solid #BAE6FD;
  border-radius: 6px; color: #0369A1; font-size: 13px;
}
.err-msg {
  margin-top: 8px; padding: 6px 12px;
  background: #FEF2F2; color: #DC2626; font-size: 12px;
  border-radius: 4px;
}
.result-summary {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; background: #F8FAFC; border-radius: 6px;
  margin-bottom: 12px; font-size: 13px; color: #475569;
}
.sheet-tabs { margin-bottom: 8px; }
.sheet-content { border: 1px solid #E5E7EB; border-radius: 6px; overflow: hidden; }
.sheet-stats {
  display: flex; gap: 8px; padding: 8px 12px;
  background: #FAFBFC; border-bottom: 1px solid #E5E7EB;
}
.ph-code {
  display: inline-block; margin: 0 4px;
  padding: 1px 6px; background: #EEF2FF; color: #4F6BFF;
  border-radius: 3px; font-size: 11px; font-family: 'SF Mono', monospace;
}
.preview-iframe {
  width: 100%; height: 500px; border: none; background: #FFFFFF;
}
.dialog-footer { display: flex; justify-content: flex-end; gap: 8px; }
</style>
