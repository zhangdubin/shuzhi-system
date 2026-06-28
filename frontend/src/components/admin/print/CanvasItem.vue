<!--
  CanvasItem · 画布上的单个组件表示 (M3 阶段 3 设计器 V1)
  - 显示该组件的简略预览
  - 点选 → 选中态 (蓝色边框)
  - 工具栏: ↑上移 / ↓下移 / ✕删除
-->
<template>
  <div
    class="canvas-item"
    :class="{ 'is-selected': selected, 'drag-over-top': dropPosition === 'top', 'drag-over-bottom': dropPosition === 'bottom' }"
    :draggable="true"
    @click.stop="$emit('select', index)"
    @dragstart.stop="onDragStart"
    @dragend="onDragEnd"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- 左侧类型 tag -->
    <div class="canvas-item-type">
      <span class="type-icon">{{ meta?.icon || '?' }}</span>
      <span class="type-label">{{ meta?.label || component.type }}</span>
    </div>
    <!-- 中间预览 -->
    <div class="canvas-item-body">
      <slot>
        <div v-if="component.type === 'title'" class="preview-title" :style="titleStyle">
          {{ component.text || '(空标题)' }}
        </div>
        <div v-else-if="component.type === 'text'" class="preview-text" :style="textStyle">
          {{ component.text || '(空文本)' }}
        </div>
        <div v-else-if="component.type === 'spacer'" class="preview-spacer">
          ↕ 间距 {{ component.height || 6 }} mm
        </div>
        <div v-else-if="component.type === 'line'" class="preview-line">
          <hr :style="{ borderColor: component.color || '#E5E7EB' }" />
        </div>
        <div v-else-if="component.type === 'grid'" class="preview-grid">
          <div class="grid-label">⊞ 网格 {{ component.colCount || 4 }} 列 · {{ (component.rows || []).length }} 行</div>
          <div v-if="nestedCount > 0" class="grid-nested">📦 {{ nestedCount }} 个单元格含嵌套组件</div>
        </div>
        <div v-else-if="component.type === 'table'" class="preview-table">
          ⊟ 数据表: bind="{{ component.bind || '?' }}", {{ (component.columns || []).length }} 列
        </div>
        <div v-else-if="component.type === 'pagebreak'" class="preview-pagebreak">
          ⤓ 强制分页
        </div>
        <div v-else-if="component.type === 'qrcode'" class="preview-qrcode">
          <span class="qr-icon">⊞</span> 二维码: {{ component.data || '(未绑定)' }}
        </div>
        <div v-else-if="component.type === 'barcode'" class="preview-barcode">
          <span class="qr-icon">║║</span> 条码: {{ component.data || '(未绑定)' }}
        </div>
      </slot>
    </div>
    <!-- 右侧工具栏 (仅选中时显示) -->
    <div v-if="selected" class="canvas-item-tools">
      <el-button link size="small" :disabled="index === 0" @click.stop="$emit('move', index, -1)">↑</el-button>
      <el-button link size="small" :disabled="index === total - 1" @click.stop="$emit('move', index, 1)">↓</el-button>
      <el-button link size="small" type="danger" @click.stop="$emit('remove', index)">✕</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { findMeta } from './compTemplates'

const props = defineProps<{
  component: Record<string, any>
  index: number
  selected: boolean
  total: number
}>()

defineEmits<{
  (e: 'select', index: number): void
  (e: 'remove', index: number): void
  (e: 'move', index: number, dir: number): void
  (e: 'dragStart', index: number): void
  (e: 'dragEnd'): void
  (e: 'drop', index: number): void
}>()

const dropPosition = ref<string | null>(null)

function onDragStart(e: DragEvent) {
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('application/x-udpe-reorder', String(props.index))
  }
}

function onDragEnd() {
  dropPosition.value = null
}

function onDragOver(e: DragEvent) {
  if (!e.dataTransfer?.types.includes('application/x-udpe-reorder')) return
  e.dataTransfer.dropEffect = 'move'
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const midY = rect.top + rect.height / 2
  dropPosition.value = e.clientY < midY ? 'top' : 'bottom'
}

function onDragLeave() {
  dropPosition.value = null
}

function onDrop(e: DragEvent) {
  dropPosition.value = null
  if (!e.dataTransfer) return
  const fromIndex = parseInt(e.dataTransfer.getData('application/x-udpe-reorder'), 10)
  if (isNaN(fromIndex)) return
  // 计算目标位置: 如果从上面拖到下面, 需要 +1
  const toIndex = props.index
  if (fromIndex === toIndex) return
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const midY = rect.top + rect.height / 2
  const insertBefore = e.clientY < midY
  // 发给父组件处理
  const event = new CustomEvent('udpe-reorder', { detail: { from: fromIndex, to: toIndex, insertBefore } })
  document.dispatchEvent(event)
}

const nestedCount = computed(() => {
  if (props.component.type !== 'grid') return 0
  let count = 0
  for (const row of (props.component.rows || [])) {
    for (const cell of (row.cells || [])) {
      if (cell.children && cell.children.length > 0) count++
    }
  }
  return count
})

const meta = computed(() => findMeta(props.component.type))

const titleStyle = computed(() => ({
  fontSize: (props.component.fontSize || 20) + 'px',
  textAlign: (props.component.align || 'center') as any,
  color: props.component.color || '#0F172A',
  fontWeight: 'bold',
}))

const textStyle = computed(() => ({
  fontSize: (props.component.fontSize || 12) + 'px',
  textAlign: (props.component.align || 'left') as any,
  color: props.component.color || '#1F2937',
  fontWeight: props.component.bold ? 'bold' : 'normal',
}))
</script>

<style scoped>
.canvas-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px;
  border: 1px solid #E5E7EB;
  border-radius: 6px;
  background: #FFFFFF;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
}
.canvas-item:hover {
  border-color: #4F6BFF;
  background: #FAFBFF;
}
.canvas-item.is-selected {
  border-color: #4F6BFF;
  background: #EEF2FF;
  box-shadow: 0 0 0 2px rgba(79,107,255,0.15);
}
.canvas-item-type {
  display: flex; flex-direction: column; align-items: center;
  width: 56px; flex-shrink: 0;
  padding: 4px;
  background: #F1F5F9;
  border-radius: 4px;
}
.type-icon { font-size: 16px; color: #4F6BFF; }
.type-label { font-size: 11px; color: #475569; margin-top: 2px; }
.canvas-item-body {
  flex: 1; min-width: 0;
  padding: 4px 0;
  overflow: hidden;
}
.preview-title {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.preview-text {
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.preview-spacer { color: #94A3B8; font-size: 12px; font-style: italic; }
.preview-line hr { border: none; border-top: 1px solid #E5E7EB; margin: 4px 0; }
.preview-grid .grid-label { font-size: 12px; color: #4F6BFF; }
.preview-grid .grid-nested { font-size: 11px; color: #16A34A; margin-top: 2px; }
.preview-table { font-size: 12px; color: #4F6BFF; font-family: 'SF Mono', monospace; }
.preview-pagebreak { color: #DC2626; font-size: 12px; font-weight: 600; }
.canvas-item-tools {
  display: flex; gap: 4px; flex-shrink: 0;
}
.drag-over-top {
  border-top: 2px solid #4F6BFF !important;
  margin-top: -1px;
}
.drag-over-bottom {
  border-bottom: 2px solid #4F6BFF !important;
  margin-bottom: -1px;
}
.canvas-item[draggable="true"] {
  cursor: grab;
}
.canvas-item[draggable="true"]:active {
  cursor: grabbing;
  opacity: 0.5;
}
.preview-qrcode { font-size: 12px; color: #4F6BFF; display: flex; align-items: center; gap: 6px; }
.preview-barcode { font-size: 12px; color: #4F6BFF; display: flex; align-items: center; gap: 6px; }
.qr-icon { font-size: 16px; }
</style>
