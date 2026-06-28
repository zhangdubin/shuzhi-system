<!--
  VersionHistoryDialog · 模板版本历史 (M4 阶段 4)
  - 显示版本时间线
  - 查看任意版本的 schemaJson
  - 回滚到指定版本
-->
<template>
  <el-dialog
    :model-value="modelValue"
    :title="`📋 版本历史 · ${templateName}`"
    width="700px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div v-if="loading" class="vh-loading">
      <el-icon class="is-loading"><Loading /></el-icon> 加载中...
    </div>

    <div v-else-if="versions.length === 0" class="vh-empty">
      <p>暂无历史版本</p>
      <p class="muted">保存模板后会自动记录版本</p>
    </div>

    <div v-else class="vh-list">
      <div
        v-for="v in versions"
        :key="v.id"
        class="vh-item"
        :class="{ 'is-current': v.version === currentVersion }"
      >
        <div class="vh-dot" />
        <div class="vh-content">
          <div class="vh-header">
            <span class="vh-ver">v{{ v.version }}</span>
            <el-tag v-if="v.version === currentVersion" size="small" type="success">当前</el-tag>
            <span class="vh-time">{{ formatTime(v.snapshotAt) }}</span>
          </div>
          <div v-if="v.note" class="vh-note">{{ v.note }}</div>
          <div class="vh-actions">
            <el-button size="small" link @click="previewVersion(v)">👁 预览</el-button>
            <el-button
              v-if="v.version !== currentVersion"
              size="small"
              link
              type="warning"
              @click="restoreVersion(v)"
            >↩ 回滚到此版本</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 预览弹窗 -->
    <el-dialog
      v-model="previewVisible"
      title="版本预览"
      width="600px"
      append-to-body
    >
      <div v-if="previewData" class="vh-preview">
        <div class="vh-preview-meta">
          <span>版本: v{{ previewData.version }}</span>
          <span>{{ formatTime(previewData.snapshotAt) }}</span>
        </div>
        <pre class="vh-json">{{ JSON.stringify(previewData.schemaJson, null, 2) }}</pre>
      </div>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { printApi } from '@/api/print'

const props = defineProps<{
  modelValue: boolean
  templateId: number | null
  templateName: string
  currentVersion: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'restored'): void
}>()

const loading = ref(false)
const versions = ref<Array<{ id: number; version: number; note: string; snapshotBy: number; snapshotAt: string }>>([])
const previewVisible = ref(false)
const previewData = ref<any>(null)

watch(() => props.modelValue, (v) => {
  if (v && props.templateId) loadVersions()
})

async function loadVersions() {
  if (!props.templateId) return
  loading.value = true
  try {
    versions.value = await printApi.listVersions(props.templateId)
  } catch (e: any) {
    ElMessage.error('加载版本历史失败: ' + (e?.message || ''))
  } finally {
    loading.value = false
  }
}

async function previewVersion(v: { id: number; version: number; snapshotAt: string }) {
  if (!props.templateId) return
  try {
    const detail = await printApi.getVersion(props.templateId, v.version)
    previewData.value = detail
    previewVisible.value = true
  } catch (e: any) {
    ElMessage.error('加载版本详情失败')
  }
}

async function restoreVersion(v: { version: number }) {
  if (!props.templateId) return
  await ElMessageBox.confirm(
    `确认回滚到 v${v.version}？当前版本会被保存为快照。`,
    '回滚确认',
    { type: 'warning' },
  ).catch(() => null)
  try {
    await printApi.restoreVersion(props.templateId, v.version)
    ElMessage.success(`已回滚到 v${v.version}`)
    previewVisible.value = false
    emit('restored')
    await loadVersions()
  } catch (e: any) {
    ElMessage.error('回滚失败: ' + (e?.message || ''))
  }
}

function formatTime(ts: string | null): string {
  if (!ts) return '—'
  try {
    const d = new Date(ts)
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch { return ts }
}
</script>

<style scoped>
.vh-loading { text-align: center; padding: 32px; color: #6B7280; }
.vh-empty { text-align: center; padding: 32px; color: #9CA3AF; }
.vh-empty .muted { font-size: 12px; }
.vh-list { max-height: 400px; overflow-y: auto; }
.vh-item {
  display: flex; gap: 12px; padding: 12px 0;
  border-bottom: 1px solid #F1F5F9;
  position: relative;
}
.vh-item:last-child { border-bottom: none; }
.vh-dot {
  width: 10px; height: 10px; border-radius: 50%;
  background: #CBD5E1; flex-shrink: 0; margin-top: 5px;
}
.vh-item.is-current .vh-dot { background: #10B981; }
.vh-content { flex: 1; min-width: 0; }
.vh-header { display: flex; align-items: center; gap: 8px; }
.vh-ver { font-weight: 600; color: #0F172A; font-size: 14px; }
.vh-time { font-size: 12px; color: #9CA3AF; }
.vh-note { font-size: 12px; color: #4B5563; margin-top: 4px; }
.vh-actions { margin-top: 6px; }
.vh-preview-meta {
  display: flex; justify-content: space-between;
  font-size: 13px; color: #475569; margin-bottom: 12px;
}
.vh-json {
  background: #1E293B; color: #E2E8F0; padding: 16px;
  border-radius: 6px; font-size: 12px; font-family: 'SF Mono', monospace;
  max-height: 400px; overflow: auto; white-space: pre-wrap;
}
</style>
