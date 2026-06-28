<!--
  VisualCanvas · 中央画布 (M3 阶段 3 设计器 V1)
  - 接收 body: Component[] 列表
  - 渲染每个 CanvasItem
  - 接受拖拽放入 (从 ComponentPalette)
  - emit: add / select / remove / move / reorder
-->
<template>
  <div
    class="visual-canvas"
    :class="{ 'is-drag-over': isDragOver }"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <div class="canvas-header">
      <span class="canvas-title">🎨 画布 ({{ body.length }} 个组件)</span>
      <div class="canvas-tip">点击组件选中 → 右侧改属性</div>
    </div>
    <div class="canvas-body">
      <div v-if="body.length === 0" class="canvas-empty">
        <div class="empty-icon">📄</div>
        <div class="empty-title">空模板</div>
        <div class="empty-hint">从左侧组件库点击 / 拖入组件</div>
      </div>
      <CanvasItem
        v-for="(c, i) in body"
        :key="c.id || i"
        :component="c"
        :index="i"
        :selected="i === selectedIndex"
        :total="body.length"
        @select="$emit('select', $event)"
        @remove="$emit('remove', $event)"
        @move="(idx, dir) => $emit('move', idx, dir)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import CanvasItem from './CanvasItem.vue'
import { findMeta, cloneComp, type CompMeta } from './compTemplates'

function handleReorder(e: Event) {
  const detail = (e as CustomEvent).detail
  if (detail) {
    emit('reorder', detail.from, detail.to, detail.insertBefore)
  }
}

onMounted(() => {
  document.addEventListener('udpe-reorder', handleReorder)
})
onUnmounted(() => {
  document.removeEventListener('udpe-reorder', handleReorder)
})

defineProps<{
  body: Record<string, any>[]
  selectedIndex: number
}>()

const emit = defineEmits<{
  (e: 'select', index: number): void
  (e: 'remove', index: number): void
  (e: 'move', index: number, dir: number): void
  (e: 'add', component: Record<string, any>): void
  (e: 'reorder', from: number, to: number, insertBefore: boolean): void
}>()

const isDragOver = ref(false)

function onDragOver(e: DragEvent) {
  if (e.dataTransfer?.types.includes('application/x-udpe-comp')) {
    e.dataTransfer.dropEffect = 'copy'
    isDragOver.value = true
  }
}
function onDragLeave() { isDragOver.value = false }
function onDrop(e: DragEvent) {
  isDragOver.value = false
  const type = e.dataTransfer?.getData('application/x-udpe-comp')
  if (!type) return
  const meta = findMeta(type)
  if (!meta) return
  emit('add', cloneComp(meta))
}

function onAddFromPalette(meta: CompMeta) {
  emit('add', cloneComp(meta))
}

// 暴露给父组件
defineExpose({ onAddFromPalette })
</script>

<style scoped>
.visual-canvas {
  flex: 7 1 auto; display: flex; flex-direction: column;
  min-height: 0;
  background: #F8FAFC;
  border-radius: 8px;
  border: 2px dashed transparent;
  transition: border-color 0.2s;
  overflow: hidden;
}
.visual-canvas.is-drag-over {
  border-color: #4F6BFF;
  background: #EEF2FF;
}
.canvas-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 16px;
  background: #FFFFFF;
  border-bottom: 1px solid #E5E7EB;
  flex-shrink: 0;
}
.canvas-title { font-size: 13px; font-weight: 600; color: #0F172A; }
.canvas-tip { font-size: 11px; color: #9CA3AF; }
.canvas-body {
  flex: 1; overflow: auto;
  padding: 16px;
  min-height: 200px;
}
.canvas-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; min-height: 200px;
  color: #9CA3AF;
  gap: 8px;
}
.empty-icon { font-size: 48px; opacity: 0.5; }
.empty-title { font-size: 14px; color: #475569; font-weight: 500; }
.empty-hint { font-size: 12px; }
</style>
