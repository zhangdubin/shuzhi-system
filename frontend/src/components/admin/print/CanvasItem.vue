<!--
  CanvasItem · 画布上的单个组件表示 (M3 阶段 3 设计器 V1)
  - 显示该组件的简略预览
  - 点选 → 选中态 (蓝色边框)
  - 工具栏: ↑上移 / ↓下移 / ✕删除
-->
<template>
  <div
    class="canvas-item"
    :class="{ 'is-selected': selected }"
    @click.stop="$emit('select', index)"
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
        </div>
        <div v-else-if="component.type === 'table'" class="preview-table">
          ⊟ 数据表: bind="{{ component.bind || '?' }}", {{ (component.columns || []).length }} 列
        </div>
        <div v-else-if="component.type === 'pagebreak'" class="preview-pagebreak">
          ⤓ 强制分页
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
import { computed } from 'vue'
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
}>()

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
.preview-table { font-size: 12px; color: #4F6BFF; font-family: 'SF Mono', monospace; }
.preview-pagebreak { color: #DC2626; font-size: 12px; font-weight: 600; }
.canvas-item-tools {
  display: flex; gap: 4px; flex-shrink: 0;
}
</style>
