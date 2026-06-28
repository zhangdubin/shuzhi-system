<!--
  BatchPrintProgressDialog · 批量打印进度对话框 (M4 阶段 1)
  - 监听 SSE 事件获取实时进度
  - 显示进度条 + 统计
  - 完成后提供下载按钮
-->
<template>
  <el-dialog
    :model-value="modelValue"
    title="📦 批量打印"
    width="480px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="status === 'done' || status === 'failed' || status === 'idle'"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="batch-content">
      <!-- 等待中 -->
      <div v-if="status === 'pending'" class="batch-status">
        <el-icon class="spin" :size="32"><Loading /></el-icon>
        <p>正在准备批量打印任务...</p>
      </div>

      <!-- 进行中 -->
      <div v-else-if="status === 'running'" class="batch-status">
        <el-progress
          :percentage="percentage"
          :stroke-width="12"
          :format="() => `${current}/${total}`"
          style="width: 100%;"
        />
        <div class="batch-stats">
          <span class="stat-ok">✓ {{ done }} 成功</span>
          <span v-if="failed > 0" class="stat-fail">✗ {{ failed }} 失败</span>
        </div>
      </div>

      <!-- 完成 -->
      <div v-else-if="status === 'done'" class="batch-status">
        <el-icon :size="32" color="#10B981"><CircleCheckFilled /></el-icon>
        <p class="done-title">批量打印完成</p>
        <div class="batch-stats">
          <span class="stat-ok">✓ {{ done }} 成功</span>
          <span v-if="failed > 0" class="stat-fail">✗ {{ failed }} 失败</span>
          <span class="stat-time">耗时 {{ (elapsedMs / 1000).toFixed(1) }}s</span>
        </div>
        <div v-if="errors.length > 0" class="batch-errors">
          <p class="err-title">失败详情：</p>
          <div v-for="e in errors" :key="e.id" class="err-item">
            ID {{ e.id }}: {{ e.error }}
          </div>
        </div>
      </div>

      <!-- 失败 -->
      <div v-else-if="status === 'failed'" class="batch-status">
        <el-icon :size="32" color="#DC2626"><CircleCloseFilled /></el-icon>
        <p class="fail-title">批量打印失败</p>
        <p class="fail-hint">所有项目均渲染失败，请检查模板和数据。</p>
      </div>
    </div>

    <template #footer>
      <el-button v-if="status === 'done'" type="primary" @click="download">
        📥 下载 PDF
      </el-button>
      <el-button @click="close">{{ status === 'running' ? '后台继续' : '关闭' }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { printApi } from '@/api/print'

const props = defineProps<{
  modelValue: boolean
  jobId: string | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
}>()

const status = ref<'idle' | 'pending' | 'running' | 'done' | 'failed'>('idle')
const total = ref(0)
const current = ref(0)
const done = ref(0)
const failed = ref(0)
const elapsedMs = ref(0)
const errors = ref<Array<{ id: string; error: string }>>([])
let eventSource: EventSource | null = null

const percentage = ref(0)

watch(() => props.modelValue, (v) => {
  if (v && props.jobId) {
    startListening()
  } else {
    stopListening()
  }
})

function startListening() {
  if (!props.jobId) return
  status.value = 'pending'
  total.value = 0
  current.value = 0
  done.value = 0
  failed.value = 0
  elapsedMs.value = 0
  errors.value = []
  percentage.value = 0

  const token = localStorage.getItem('token') || ''
  const url = `/sse/batch/${props.jobId}?token=${encodeURIComponent(token)}`
  eventSource = new EventSource(url)

  eventSource.addEventListener('batch_start', (e) => {
    const data = JSON.parse(e.data)
    status.value = 'running'
    total.value = data.total || 0
  })

  eventSource.addEventListener('batch_progress', (e) => {
    const data = JSON.parse(e.data)
    current.value = data.current || 0
    done.value = data.done || 0
    failed.value = data.failed || 0
    percentage.value = total.value > 0 ? Math.round((current.value / total.value) * 100) : 0
  })

  eventSource.addEventListener('batch_done', (e) => {
    const data = JSON.parse(e.data)
    status.value = data.status === 'done' ? 'done' : 'failed'
    done.value = data.done || 0
    failed.value = data.failed || 0
    elapsedMs.value = data.elapsedMs || 0
    stopListening()
    // 拉取完整状态（含 errors）
    fetchStatus()
  })

  eventSource.onerror = () => {
    // SSE 断开时轮询 fallback
    if (status.value === 'running' || status.value === 'pending') {
      pollStatus()
    }
  }
}

async function fetchStatus() {
  if (!props.jobId) return
  try {
    const r = await printApi.batchJobStatus(props.jobId)
    status.value = r.status as any
    total.value = r.total
    done.value = r.done
    failed.value = r.failed
    elapsedMs.value = r.elapsedMs
    errors.value = r.errors || []
  } catch { /* ignore */ }
}

async function pollStatus() {
  if (!props.jobId) return
  await fetchStatus()
  if (status.value === 'running' || status.value === 'pending') {
    setTimeout(pollStatus, 1000)
  }
}

function stopListening() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

async function download() {
  if (!props.jobId) return
  try {
    const blob = await printApi.batchJobDownload(props.jobId)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `batch_${props.jobId}.pdf`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('PDF 已下载')
  } catch (e: any) {
    ElMessage.error('下载失败: ' + (e?.message || ''))
  }
}

function close() {
  stopListening()
  emit('update:modelValue', false)
}

onUnmounted(stopListening)
</script>

<style scoped>
.batch-content {
  padding: 16px 0;
}
.batch-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}
.batch-status p {
  margin: 0;
  font-size: 14px;
  color: #374151;
}
.batch-stats {
  display: flex;
  gap: 16px;
  font-size: 13px;
  margin-top: 8px;
}
.stat-ok { color: #10B981; }
.stat-fail { color: #DC2626; }
.stat-time { color: #6B7280; }
.done-title { font-weight: 600; color: #10B981; font-size: 16px; }
.fail-title { font-weight: 600; color: #DC2626; font-size: 16px; }
.fail-hint { color: #6B7280; font-size: 13px; }
.batch-errors {
  width: 100%;
  margin-top: 12px;
  padding: 8px 12px;
  background: #FEF2F2;
  border-radius: 6px;
  max-height: 120px;
  overflow-y: auto;
}
.err-title { font-size: 12px; color: #DC2626; margin: 0 0 6px; font-weight: 600; }
.err-item { font-size: 11px; color: #991B1B; margin: 2px 0; font-family: 'SF Mono', monospace; }
.spin { animation: spin 1s linear infinite; color: #4F6BFF; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
