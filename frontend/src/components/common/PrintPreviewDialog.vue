<!--
  PrintPreviewDialog · UDPE 通用预览弹窗
  ======================================================================
  设计文档：plans/udpe-design/design.md §十
  阶段：M2 阶段 6（消除 4 处样板代码）

  用法：
    <PrintPreviewDialog
      v-model="printDialogVisible"
      :template-code="'invoice_v1'"
      :data="{ _resolver: invoiceId }"
      :source-module="'invoice'"
      :source-id="invoiceId"
      title="发票打印预览"
    />

  行为：
    - visible=true 时自动调 /print/preview 拉 HTML
    - 内嵌 iframe srcdoc 渲染 HTML（不依赖第三方 CDN / 字体）
    - 头部按钮：下载 PDF / 浏览器打印 / 关闭
    - 重新生成按钮（弹 loading → 重新拉）
-->
<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="(v) => $emit('update:modelValue', v)"
    :title="title || '打印预览'"
    width="920px"
    :close-on-click-modal="false"
    align-center
    destroy-on-close
    class="udpe-preview-dialog"
  >
    <div v-if="loading" class="udpe-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span style="margin-left: 8px;">正在生成预览…</span>
    </div>

    <div v-else-if="errorMsg" class="udpe-error">
      <el-alert :title="errorMsg" type="error" :closable="false" show-icon />
      <div style="margin-top: 12px;">
        <el-button size="small" @click="loadPreview">重新生成</el-button>
      </div>
    </div>

    <div v-else class="udpe-preview-wrap">
      <div class="udpe-toolbar no-print">
        <el-button size="small" :loading="pdfLoading" @click="downloadPdf">
          📥 下载 PDF
        </el-button>
        <el-button size="small" type="primary" :disabled="!html" @click="browserPrint">
          🖨 浏览器打印
        </el-button>
        <span class="udpe-hint">
          A4 纸打印 · 建议关闭页眉页脚 · {{ elapsedMs ? `${elapsedMs}ms` : '' }}
        </span>
        <el-button size="small" link @click="loadPreview">🔄 重新生成</el-button>
      </div>
      <iframe
        v-if="html"
        ref="iframeRef"
        class="udpe-iframe"
        :srcdoc="html"
        sandbox="allow-same-origin allow-scripts"
      />
    </div>

    <template #footer>
      <el-button @click="close">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { printApi } from '@/api/print'

const props = defineProps<{
  modelValue: boolean
  templateCode: string
  data?: Record<string, any>
  options?: Record<string, any>
  title?: string
  sourceModule?: string
  sourceId?: string | number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'success', payload: { logId: number; elapsedMs: number; pdfSize?: number }): void
  (e: 'error', err: Error): void
}>()

const loading = ref(false)
const pdfLoading = ref(false)
const errorMsg = ref<string | null>(null)
const html = ref<string>('')
const elapsedMs = ref(0)
const logId = ref(0)
const iframeRef = ref<HTMLIFrameElement | null>(null)

const fullOptions = () => {
  // 后端 Pydantic schema 要求 sourceId 为 string。
  // 兼容业务方传 number / string 两种情况（详情页用了 Number(...) 强转,管理后台用 String(...)）。
  const sid = props.sourceId ?? props.options?.sourceId
  return {
    ...(props.options || {}),
    sourceModule: props.sourceModule || props.options?.sourceModule,
    sourceId: sid !== undefined && sid !== null ? String(sid) : sid,
  }
}

async function loadPreview() {
  if (!props.templateCode) {
    errorMsg.value = '缺少 templateCode'
    return
  }
  loading.value = true
  errorMsg.value = null
  try {
    const r = await printApi.preview({
      templateCode: props.templateCode,
      data: props.data || {},
      options: fullOptions(),
    })
    html.value = r.html
    elapsedMs.value = r.elapsedMs
    logId.value = r.logId
    emit('success', { logId: r.logId, elapsedMs: r.elapsedMs })
  } catch (e: any) {
    // 兼容 Pydantic 422 (detail 数组) / 自定义 message / 通用 message
    const detail = e?.response?.data?.detail
    let msg = e?.response?.data?.message || e?.message || '预览生成失败'
    if (Array.isArray(detail) && detail.length > 0) {
      const d = detail[0]
      msg = `${d.loc?.join('.') || ''}: ${d.msg || ''}`.replace(/^: /, '')
    } else if (typeof detail === 'string') {
      msg = detail
    }
    errorMsg.value = msg
    emit('error', e)
  } finally {
    loading.value = false
  }
}

async function downloadPdf() {
  pdfLoading.value = true
  try {
    const blob = await printApi.pdfBlob({
      templateCode: props.templateCode,
      data: props.data || {},
      options: fullOptions(),
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${props.templateCode}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
    ElMessage.success('PDF 已下载')
  } catch (e: any) {
    const msg = e?.response?.data?.message || e?.message || '下载失败'
    ElMessage.error(msg)
  } finally {
    pdfLoading.value = false
  }
}

function browserPrint() {
  // 内嵌 iframe 走 window.print（沙箱允许 same-origin 即可）
  const w = iframeRef.value?.contentWindow
  if (!w) { ElMessage.warning('预览未就绪'); return }
  try {
    w.focus()
    w.print()
  } catch (e) {
    ElMessage.warning('请在预览内点击"浏览器打印"')
  }
}

function close() {
  emit('update:modelValue', false)
}

// 打开时自动加载；关闭时清状态
// 修复 M2 阶段 8 bug: 组件挂载时 modelValue 已经为 true, 普通 watch 不会触发
watch(() => props.modelValue, (v) => {
  if (v) {
    html.value = ''
    errorMsg.value = null
    nextTick(loadPreview)
  }
}, { immediate: true })
</script>

<style scoped>
.udpe-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #6B7280;
  font-size: 13px;
}
.udpe-error { padding: 24px 0; }

.udpe-preview-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 70vh;
  min-height: 500px;
}
.udpe-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #F9FAFB;
  border-radius: 8px;
}
.udpe-hint {
  margin-left: auto;
  font-size: 11px;
  color: #9CA3AF;
}
.udpe-iframe {
  flex: 1;
  width: 100%;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  background: #FFFFFF;
}

/* 打印时只输出 iframe 内容 */
@media print {
  :deep(.udpe-preview-dialog),
  :deep(.el-dialog__header),
  :deep(.el-dialog__body) > *:not(.udpe-preview-wrap) { display: none !important; }
  .udpe-toolbar { display: none !important; }
  .udpe-iframe { border: none; }
}
</style>
